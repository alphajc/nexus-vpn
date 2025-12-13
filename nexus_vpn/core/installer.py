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
        # 必须安装 stroke 插件 (libcharon-extra-plugins) 和 iptables
        pkgs = "curl wget openssl unzip strongswan strongswan-pki libcharon-extra-plugins iptables iptables-persistent"
        cmd = ""
        if shutil.which("apt-get"):
            # DEBIAN_FRONTEND=noninteractive 防止 iptables-persistent 弹窗
            cmd = f"DEBIAN_FRONTEND=noninteractive apt-get update -y && DEBIAN_FRONTEND=noninteractive apt-get install -y {pkgs}"
        elif shutil.which("yum"):
            cmd = f"yum install -y epel-release && yum install -y {pkgs}"
        
        try:
            subprocess.check_call(cmd, shell=True, stdout=subprocess.DEVNULL)
        except:
            log.warning("依赖安装可能有警告，尝试继续...")

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
        with open("/etc/systemd/system/nexus-xray.service", "w") as f: f.write(svc)
        subprocess.run("systemctl daemon-reload && systemctl enable nexus-xray", shell=True)

    def setup_network(self):
        # 1. Sysctl
        with open("/etc/sysctl.conf", "a") as f:
            f.write("\nnet.ipv4.ip_forward=1\nnet.ipv6.conf.all.forwarding=1\n")
            f.write("net.core.default_qdisc=fq\nnet.ipv4.tcp_congestion_control=bbr\n")
        subprocess.run("sysctl -p", shell=True, stdout=subprocess.DEVNULL)

        # 2. IPTables NAT (关键修复: 确保 VPN 流量能上网)
        try:
            # 获取默认网卡
            iface = subprocess.check_output("ip route show default | awk '/default/ {print $5}'", shell=True).decode().strip()
            if iface:
                # 清理旧规则
                subprocess.run(f"iptables -t nat -D POSTROUTING -s 10.10.10.0/24 -o {iface} -j MASQUERADE", shell=True, stderr=subprocess.DEVNULL)
                # 添加新规则
                subprocess.run(f"iptables -t nat -A POSTROUTING -s 10.10.10.0/24 -o {iface} -j MASQUERADE", shell=True)
                # 保存规则 (Ubuntu/Debian)
                subprocess.run("netfilter-persistent save", shell=True, stderr=subprocess.DEVNULL)
                log.info(f"NAT 转发规则已添加至网卡: {iface}")
        except Exception as e:
            log.warning(f"NAT 规则配置失败: {e}")

        # 3. AppArmor (防止拦截配置读取)
        if shutil.which("aa-complain"):
            subprocess.run("aa-complain /usr/lib/ipsec/charon", shell=True, stderr=subprocess.DEVNULL)
            subprocess.run("aa-complain /usr/lib/ipsec/stroke", shell=True, stderr=subprocess.DEVNULL)

    @staticmethod
    def cleanup():
        subprocess.run("systemctl stop nexus-xray strongswan-starter strongswan", shell=True)
        subprocess.run("rm -rf /usr/local/bin/xray /usr/local/etc/xray /etc/nexus-vpn /etc/ipsec.conf /etc/ipsec.secrets", shell=True)
        subprocess.run("rm /etc/systemd/system/nexus-xray.service", shell=True)
        subprocess.run("systemctl daemon-reload", shell=True)
        log.success("清理完成。")
