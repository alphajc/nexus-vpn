import os
import subprocess
import shutil
import urllib.request
import zipfile
import tempfile
from nexus_vpn.utils.logger import log
from nexus_vpn.protocols.ikev2 import IKEv2Manager

class Installer:
    XRAY_VERSION = "1.8.4"
    XRAY_URL = f"https://github.com/XTLS/Xray-core/releases/download/v{XRAY_VERSION}/Xray-linux-64.zip"
    
    def __init__(self, domain, proto, reality_dest):
        self.domain = domain
        self.proto = proto
        self.reality_dest = reality_dest

    def run(self):
        log.info(">>> 阶段 1: 安装系统依赖...")
        self.install_dependencies()
        
        log.info(">>> 阶段 2: 部署 Xray Core...")
        self.install_xray()
        
        log.info(">>> 阶段 3: 配置网络与 NAT...")
        self.setup_network()

        log.info(">>> 阶段 4: 初始化 PKI 环境...")
        IKEv2Manager.init_pki(self.domain)
        
        log.success("基础环境安装完毕。")

    def install_dependencies(self):
        pkgs = ["curl", "wget", "openssl", "unzip", "strongswan", "strongswan-pki",
                "libcharon-extra-plugins", "iptables", "iptables-persistent"]
        
        env = os.environ.copy()
        env["DEBIAN_FRONTEND"] = "noninteractive"
        
        try:
            if shutil.which("apt-get"):
                subprocess.run(["apt-get", "update", "-y"], env=env, 
                             stdout=subprocess.DEVNULL, check=True)
                subprocess.run(["apt-get", "install", "-y"] + pkgs, env=env,
                             stdout=subprocess.DEVNULL, check=True)
            elif shutil.which("yum"):
                subprocess.run(["yum", "install", "-y", "epel-release"],
                             stdout=subprocess.DEVNULL, check=True)
                subprocess.run(["yum", "install", "-y"] + pkgs,
                             stdout=subprocess.DEVNULL, check=True)
        except subprocess.CalledProcessError as e:
            log.warning(f"依赖安装可能有警告: {e}")

    def install_xray(self):
        bin_path = "/usr/local/bin/xray"
        if not os.path.exists(bin_path):
            with tempfile.TemporaryDirectory() as tmp:
                urllib.request.urlretrieve(self.XRAY_URL, os.path.join(tmp, "xray.zip"))
                with zipfile.ZipFile(os.path.join(tmp, "xray.zip"), 'r') as z:
                    z.extractall(tmp)
                shutil.move(os.path.join(tmp, "xray"), bin_path)
                os.chmod(bin_path, 0o755)
        
        svc = """[Unit]
Description=Xray Service
After=network.target
[Service]
User=root
ExecStart=/usr/local/bin/xray run -config /usr/local/etc/xray/config.json
Restart=on-failure
[Install]
WantedBy=multi-user.target
"""
        with open("/etc/systemd/system/nexus-xray.service", "w") as f:
            f.write(svc)
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", "nexus-xray"], check=True)

    def setup_network(self):
        # 1. Sysctl - 幂等写入
        sysctl_settings = {
            "net.ipv4.ip_forward": "1",
            "net.ipv6.conf.all.forwarding": "1",
            "net.core.default_qdisc": "fq",
            "net.ipv4.tcp_congestion_control": "bbr"
        }
        sysctl_path = "/etc/sysctl.conf"
        
        # 读取现有配置
        existing_lines = []
        if os.path.exists(sysctl_path):
            with open(sysctl_path, "r") as f:
                existing_lines = f.readlines()
        
        # 过滤掉我们要设置的项（避免重复）
        filtered_lines = []
        for line in existing_lines:
            key = line.split("=")[0].strip()
            if key not in sysctl_settings:
                filtered_lines.append(line)
        
        # 追加新配置
        with open(sysctl_path, "w") as f:
            f.writelines(filtered_lines)
            f.write("\n# NexusVPN settings\n")
            for key, value in sysctl_settings.items():
                f.write(f"{key}={value}\n")
        
        subprocess.run(["sysctl", "-p"], stdout=subprocess.DEVNULL, check=True)

        # 2. IPTables NAT
        try:
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True, text=True, check=True
            )
            # 解析默认网卡
            parts = result.stdout.split()
            iface = None
            for i, p in enumerate(parts):
                if p == "dev" and i + 1 < len(parts):
                    iface = parts[i + 1]
                    break
            
            if iface:
                # 清理旧规则（忽略错误）
                subprocess.run(
                    ["iptables", "-t", "nat", "-D", "POSTROUTING",
                     "-s", "10.10.10.0/24", "-o", iface, "-j", "MASQUERADE"],
                    stderr=subprocess.DEVNULL
                )
                # 添加新规则
                subprocess.run(
                    ["iptables", "-t", "nat", "-A", "POSTROUTING",
                     "-s", "10.10.10.0/24", "-o", iface, "-j", "MASQUERADE"],
                    check=True
                )
                # 保存规则
                if shutil.which("netfilter-persistent"):
                    subprocess.run(["netfilter-persistent", "save"],
                                 stderr=subprocess.DEVNULL)
                log.info(f"NAT 转发规则已添加至网卡: {iface}")
        except subprocess.CalledProcessError as e:
            log.warning(f"NAT 规则配置失败: {e}")

        # 3. AppArmor
        if shutil.which("aa-complain"):
            subprocess.run(["aa-complain", "/usr/lib/ipsec/charon"],
                         stderr=subprocess.DEVNULL)
            subprocess.run(["aa-complain", "/usr/lib/ipsec/stroke"],
                         stderr=subprocess.DEVNULL)

    @staticmethod
    def cleanup():
        subprocess.run(["systemctl", "stop", "nexus-xray", "strongswan-starter", "strongswan"],
                      stderr=subprocess.DEVNULL)
        
        paths_to_remove = [
            "/usr/local/bin/xray",
            "/usr/local/etc/xray",
            "/etc/nexus-vpn",
            "/etc/ipsec.conf",
            "/etc/ipsec.secrets",
            "/etc/systemd/system/nexus-xray.service"
        ]
        for path in paths_to_remove:
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            elif os.path.exists(path):
                os.remove(path)
        
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        log.success("清理完成。")
