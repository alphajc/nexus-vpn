import os
import json
import subprocess
import shutil
import urllib.request
import zipfile
import tempfile
from nexus_vpn.utils.logger import log
from nexus_vpn.utils.sudo import sudo_run, sudo_write_file, sudo_read_file, sudo_makedirs, sudo_chmod, sudo_move, sudo_remove
from nexus_vpn.protocols.ikev2 import IKEv2Manager

class Installer:
    XRAY_VERSION = "1.8.4"
    XRAY_RELEASE_API = "https://api.github.com/repos/XTLS/Xray-core/releases/latest"
    
    @staticmethod
    def get_xray_download_url(version):
        return f"https://github.com/XTLS/Xray-core/releases/download/v{version}/Xray-linux-64.zip"
    
    def __init__(self, domain, proto, reality_dests):
        self.domain = domain
        self.proto = proto
        # 兼容单个字符串和列表
        if isinstance(reality_dests, str):
            self.reality_dests = [reality_dests]
        else:
            self.reality_dests = list(reality_dests)

    def run(self):
        """运行安装流程（幂等，可重复执行）"""
        # 检测是否已安装
        xray_installed = os.path.exists("/usr/local/bin/xray")
        pki_exists = os.path.exists("/etc/nexus-vpn/pki/ca.crt")
        
        if xray_installed and pki_exists:
            log.info("检测到已有安装，执行增量更新...")
        
        log.info(">>> 阶段 1: 安装系统依赖...")
        self.install_dependencies()
        
        log.info(">>> 阶段 2: 部署 Xray Core...")
        self.install_xray()
        
        log.info(">>> 阶段 3: 配置网络与 NAT...")
        self.setup_network()

        log.info(">>> 阶段 4: 初始化 PKI 环境...")
        # setup_ca 内部已经是幂等的（检查 ca.crt 是否存在）
        IKEv2Manager.init_pki(self.domain)
        
        log.success("基础环境安装完毕。")

    def install_dependencies(self):
        pkgs = ["curl", "wget", "openssl", "unzip", "strongswan", "strongswan-pki",
                "libcharon-extra-plugins", "iptables", "iptables-persistent"]
        
        env = os.environ.copy()
        env["DEBIAN_FRONTEND"] = "noninteractive"
        
        try:
            if shutil.which("apt-get"):
                sudo_run(["apt-get", "update", "-y"], env=env, 
                         stdout=subprocess.DEVNULL, check=True)
                sudo_run(["apt-get", "install", "-y"] + pkgs, env=env,
                         stdout=subprocess.DEVNULL, check=True)
            elif shutil.which("yum"):
                sudo_run(["yum", "install", "-y", "epel-release"],
                         stdout=subprocess.DEVNULL, check=True)
                sudo_run(["yum", "install", "-y"] + pkgs,
                         stdout=subprocess.DEVNULL, check=True)
        except subprocess.CalledProcessError as e:
            log.warning(f"依赖安装可能有警告: {e}")

    def install_xray(self):
        bin_path = "/usr/local/bin/xray"
        if not os.path.exists(bin_path):
            Installer._download_and_install_xray(Installer.XRAY_VERSION)
        
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
        sudo_write_file("/etc/systemd/system/nexus-xray.service", svc)
        sudo_run(["systemctl", "daemon-reload"], check=True)
        sudo_run(["systemctl", "enable", "nexus-xray"], check=True)

    @staticmethod
    def _download_and_install_xray(version):
        """下载并安装指定版本的 Xray"""
        bin_path = "/usr/local/bin/xray"
        url = Installer.get_xray_download_url(version)
        
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = os.path.join(tmp, "xray.zip")
            log.info(f"下载 Xray v{version}...")
            urllib.request.urlretrieve(url, zip_path)
            
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(tmp)
            
            # 备份旧版本
            if os.path.exists(bin_path):
                sudo_move(bin_path, f"{bin_path}.bak")
            
            sudo_move(os.path.join(tmp, "xray"), bin_path)
            sudo_chmod(bin_path, 0o755)
        
        log.success(f"Xray v{version} 安装完成")

    @staticmethod
    def _get_current_xray_version():
        """获取当前安装的 Xray 版本"""
        bin_path = "/usr/local/bin/xray"
        if not os.path.exists(bin_path):
            return None
        try:
            result = subprocess.run(
                [bin_path, "version"],
                capture_output=True, text=True
            )
            # 输出格式: Xray 1.8.4 (Xray, Penetrates Everything.)
            for line in result.stdout.split('\n'):
                if line.startswith("Xray"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1]
        except subprocess.SubprocessError:
            pass
        return None

    @staticmethod
    def _get_latest_xray_version():
        """从 GitHub API 获取最新 Xray 版本"""
        try:
            req = urllib.request.Request(
                Installer.XRAY_RELEASE_API,
                headers={"User-Agent": "NexusVPN"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                # tag_name 格式: v1.8.6
                return data.get("tag_name", "").lstrip("v")
        except Exception as e:
            log.warning(f"获取最新版本失败: {e}")
            return None

    @staticmethod
    def update_xray(target_version=None):
        """更新 Xray Core"""
        current = Installer._get_current_xray_version()
        log.info(f"当前 Xray 版本: {current or '未安装'}")
        
        if target_version is None:
            target_version = Installer._get_latest_xray_version()
            if not target_version:
                log.error("无法获取最新版本信息")
                return
        
        log.info(f"目标版本: {target_version}")
        
        if current == target_version:
            log.info("已是最新版本，无需更新")
            return
        
        # 停止服务
        sudo_run(["systemctl", "stop", "nexus-xray"], stderr=subprocess.DEVNULL)
        
        try:
            Installer._download_and_install_xray(target_version)
            # 重启服务
            sudo_run(["systemctl", "start", "nexus-xray"], check=True)
            log.success(f"Xray 已从 {current} 更新到 {target_version}")
        except Exception as e:
            log.error(f"更新失败: {e}")
            # 恢复备份
            bin_path = "/usr/local/bin/xray"
            if os.path.exists(f"{bin_path}.bak"):
                sudo_move(f"{bin_path}.bak", bin_path)
                sudo_run(["systemctl", "start", "nexus-xray"], stderr=subprocess.DEVNULL)
                log.warning("已恢复到旧版本")

    @staticmethod
    def update_strongswan():
        """更新 StrongSwan 到最新版本"""
        env = os.environ.copy()
        env["DEBIAN_FRONTEND"] = "noninteractive"
        
        log.info("更新 StrongSwan...")
        
        try:
            if shutil.which("apt-get"):
                sudo_run(["apt-get", "update", "-y"], env=env,
                         stdout=subprocess.DEVNULL, check=True)
                sudo_run(
                    ["apt-get", "install", "-y", "--only-upgrade",
                     "strongswan", "strongswan-pki", "libcharon-extra-plugins"],
                    env=env, check=True
                )
            elif shutil.which("yum"):
                sudo_run(
                    ["yum", "update", "-y", "strongswan"],
                    check=True
                )
            
            # 重启服务
            sudo_run(["systemctl", "restart", "strongswan"], stderr=subprocess.DEVNULL)
            sudo_run(["systemctl", "restart", "strongswan-starter"], stderr=subprocess.DEVNULL)
            
            # 获取版本
            result = subprocess.run(["ipsec", "version"], capture_output=True, text=True)
            version_info = result.stdout.split('\n')[0] if result.stdout else "未知"
            
            log.success(f"StrongSwan 更新完成: {version_info}")
        except subprocess.CalledProcessError as e:
            log.error(f"更新失败: {e}")

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
            try:
                content = sudo_read_file(sysctl_path)
                existing_lines = content.splitlines(keepends=True)
            except Exception:
                pass
        
        # 过滤掉我们要设置的项（避免重复）
        filtered_lines = []
        for line in existing_lines:
            key = line.split("=")[0].strip()
            if key not in sysctl_settings:
                filtered_lines.append(line)
        
        # 追加新配置
        new_content = "".join(filtered_lines)
        new_content += "\n# NexusVPN settings\n"
        for key, value in sysctl_settings.items():
            new_content += f"{key}={value}\n"
        
        sudo_write_file(sysctl_path, new_content)
        sudo_run(["sysctl", "-p"], stdout=subprocess.DEVNULL, check=True)

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
                sudo_run(
                    ["iptables", "-t", "nat", "-D", "POSTROUTING",
                     "-s", "10.10.10.0/24", "-o", iface, "-j", "MASQUERADE"],
                    stderr=subprocess.DEVNULL
                )
                # 添加新规则
                sudo_run(
                    ["iptables", "-t", "nat", "-A", "POSTROUTING",
                     "-s", "10.10.10.0/24", "-o", iface, "-j", "MASQUERADE"],
                    check=True
                )
                # 保存规则
                if shutil.which("netfilter-persistent"):
                    sudo_run(["netfilter-persistent", "save"],
                             stderr=subprocess.DEVNULL)
                log.info(f"NAT 转发规则已添加至网卡: {iface}")
        except subprocess.CalledProcessError as e:
            log.warning(f"NAT 规则配置失败: {e}")

        # 3. AppArmor
        if shutil.which("aa-complain"):
            sudo_run(["aa-complain", "/usr/lib/ipsec/charon"],
                     stderr=subprocess.DEVNULL)
            sudo_run(["aa-complain", "/usr/lib/ipsec/stroke"],
                     stderr=subprocess.DEVNULL)

    @staticmethod
    def cleanup():
        sudo_run(["systemctl", "stop", "nexus-xray", "strongswan-starter", "strongswan"],
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
            sudo_remove(path)
        
        sudo_run(["systemctl", "daemon-reload"], check=True)
        log.success("清理完成。")
