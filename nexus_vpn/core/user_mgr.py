import os
import json
import glob
import click
import subprocess
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from nexus_vpn.utils.logger import log
from nexus_vpn.protocols.v2ray import V2RayManager
from nexus_vpn.protocols.ikev2 import IKEv2Manager
from nexus_vpn.core.cert_mgr import CertManager

console = Console()

class UserManager:
    @staticmethod
    def add(vpn_type, username):
        if vpn_type == 'v2ray':
            V2RayManager.add_user(username)
        
        elif vpn_type == 'ikev2-cert':
            p12 = CertManager.issue_user_cert(username)
            dom = UserManager._get_domain()
            xml = IKEv2Manager.create_mobileconfig(username, dom, p12)
            with open(f"{username}.mobileconfig", "w") as f: f.write(xml)
            log.success(f"IKEv2 证书用户已生成: {username}.mobileconfig")
        
        elif vpn_type == 'ikev2-eap':
            pw = click.prompt(f"设置 VPN 密码", hide_input=False)
            IKEv2Manager.add_eap_user(username, pw)
            dom = UserManager._get_domain()
            
            msg = f"""
[bold cyan]用户创建成功！[/bold cyan]

[bold]客户端连接设置 (Android/Windows/iOS):[/bold]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
服务器 (Server):     [green]{dom}[/green]
远程ID (Remote ID):  [green]{dom}[/green]  <-- 必填，否则连不上！
用户名 (Username):   [yellow]{username}[/yellow]
密码 (Password):     [yellow]{pw}[/yellow]
认证类型:            IKEv2 EAP (MSCHAPv2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[bold red]⚠️  重要提示 (Android 11+ / Windows):[/bold red]
您必须下载并安装 CA 根证书，否则连接会失败！

[bold]CA 证书路径:[/bold] {CertManager.PKI_DIR}/ca.crt

[bold]快速下载方式 (在本地终端运行):[/bold]
scp root@{dom}:{CertManager.PKI_DIR}/ca.crt ./nexus-ca.crt
            """
            console.print(Panel(msg.strip(), title="IKEv2 EAP 连接信息", border_style="green"))

    @staticmethod
    def remove(vpn_type, username):
        if vpn_type == 'v2ray': V2RayManager.remove_user(username)
        elif vpn_type == 'ikev2-cert':
            for ext in ['.crt', '.key', '.p12']:
                f = f"{CertManager.PKI_DIR}/certs/{username}{ext}"
                if os.path.exists(f): os.remove(f)
            if os.path.exists(f"{username}.mobileconfig"): os.remove(f"{username}.mobileconfig")
            log.success(f"IKEv2 证书 {username} 已清理")
        elif vpn_type == 'ikev2-eap':
            IKEv2Manager.remove_eap_user(username)

    @staticmethod
    def list_users():
        # V2Ray
        v_table = Table(title="🌐 V2Ray 用户", show_header=True, header_style="bold magenta")
        v_table.add_column("用户名", style="cyan")
        v_table.add_column("UUID", style="dim")
        try:
            if os.path.exists(V2RayManager.CONFIG_PATH):
                with open(V2RayManager.CONFIG_PATH) as f:
                    clients = json.load(f)['inbounds'][0]['settings']['clients']
                    for c in clients: v_table.add_row(c.get('email', 'N/A'), c.get('id', 'N/A'))
        except Exception as e:
            v_table.add_row("[red]Error[/red]", str(e))
        console.print(v_table); print("")
        
        # IKEv2 Cert Users
        cert_table = Table(title="🛡️ IKEv2 (证书认证) 用户", show_header=True, header_style="bold green")
        cert_table.add_column("用户名", style="cyan")
        cert_table.add_column("状态", style="dim")
        try:
            cert_dir = f"{CertManager.PKI_DIR}/certs"
            if os.path.exists(cert_dir):
                found_cert_users = False
                for f_path in glob.glob(os.path.join(cert_dir, "*.crt")):
                    fname = os.path.basename(f_path)
                    if fname == "server.crt": continue # 排除服务器证书
                    username = fname.replace(".crt", "")
                    cert_table.add_row(username, "已签发")
                    found_cert_users = True
                if not found_cert_users:
                    cert_table.add_row("无证书用户", "[dim]N/A[/dim]")
            else:
                cert_table.add_row("PKI目录未初始化", "[red]Error[/red]")
        except Exception as e:
            cert_table.add_row("[red]Error[/red]", str(e))
        console.print(cert_table); print("")

        # IKEv2 EAP Users
        eap_table = Table(title="🛡️ IKEv2 (账号密码) 用户", show_header=True, header_style="bold yellow")
        eap_table.add_column("用户名", style="cyan")
        eap_table.add_column("类型", style="dim")
        try:
            if os.path.exists(IKEv2Manager.SECRETS_FILE):
                found_eap_users = False
                with open(IKEv2Manager.SECRETS_FILE) as f:
                    for l in f:
                        if " : EAP " in l:
                            user = l.split(":")[0].strip().replace('"','')
                            eap_table.add_row(user, "MSCHAPv2")
                            found_eap_users = True
                if not found_eap_users:
                    eap_table.add_row("无账号密码用户", "[dim]N/A[/dim]")
            else:
                eap_table.add_row("Secrets文件不存在", "[red]Error[/red]")
        except Exception as e:
            eap_table.add_row("[red]Error[/red]", str(e))
        console.print(eap_table)
        
        # 底部提示
        print(f"\n[dim]CA 证书位置: {CertManager.PKI_DIR}/ca.crt[/dim]")

    @staticmethod
    def _get_domain():
        import re
        try:
            with open("/etc/ipsec.conf") as f:
                m = re.search(r"leftid=@(.*)", f.read())
                if m: return m.group(1).strip()
        except: pass
        # 尝试获取本机 IP 作为备选
        try:
             return subprocess.check_output("curl -s ifconfig.me", shell=True).decode().strip()
        except: return "your-server-ip"
