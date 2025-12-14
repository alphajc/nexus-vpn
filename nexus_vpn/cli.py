"""命令行入口模块"""
import click
import subprocess
from rich.table import Table
from rich.console import Console
from nexus_vpn.utils.logger import log
from nexus_vpn.core.system import SystemChecker
from nexus_vpn.core.installer import Installer
from nexus_vpn.core.user_mgr import UserManager
from nexus_vpn.protocols.v2ray import V2RayManager

console = Console()

# 允许检查的服务名白名单
ALLOWED_SERVICES = {"nexus-xray", "strongswan", "strongswan-starter", "ipsec"}


def check_service(name):
    if name not in ALLOWED_SERVICES:
        return "[red]invalid[/red]"
    try:
        res = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True, text=True
        )
        active = res.stdout.strip() if res.stdout else "unknown"
        color = "green" if active == "active" else "red"
        return f"[{color}]{active}[/{color}]"
    except subprocess.SubprocessError:
        return "[red]error[/red]"


def check_port(port, proto="tcp"):
    if not isinstance(port, int) or port < 1 or port > 65535:
        return "[red]INVALID[/red]"
    flag = "-u" if "udp" in proto.lower() else "-t"
    try:
        # 使用 ss 命令检查端口，不使用 shell
        result = subprocess.run(
            ["ss", flag + "ln"],
            capture_output=True, text=True
        )
        if f":{port} " in result.stdout or f":{port}\t" in result.stdout:
            return "[green]OPEN[/green]"
    except subprocess.SubprocessError:
        pass
    return "[red]CLOSED[/red]"


def check_bbr():
    try:
        res = subprocess.run(
            ["sysctl", "-n", "net.ipv4.tcp_congestion_control"],
            capture_output=True, text=True
        )
        if "bbr" in res.stdout:
            return "[green]已开启 (BBR)[/green]"
        return f"[yellow]未开启 ({res.stdout.strip()})[/yellow]"
    except subprocess.SubprocessError:
        return "[red]Unknown[/red]"


@click.group()
def cli():
    """🛡️ nexus-vpn: 综合代理与 VPN 部署工具"""
    pass


@cli.command()
@click.option('--domain', prompt='请输入服务器域名/IP', help='服务器公网IP或域名')
@click.option('--proto', default='vless', type=click.Choice(['vless']), help='协议类型')
@click.option('--reality-dest', 'reality_dests', multiple=True, default=['www.microsoft.com:443'], help='Reality 偷取的目标网站（可多次指定）')
def install(domain, proto, reality_dests):
    """[部署] 执行全自动安装与初始化"""
    log.info(f"开始部署 Nexus-VPN | 目标: {domain}")
    SystemChecker.check_os()
    installer = Installer(domain, proto, reality_dests)
    installer.run()

    if proto == 'vless':
        info = V2RayManager.create_config(domain, reality_dests)
        V2RayManager.print_connection_info(domain, info)

    from nexus_vpn.protocols.ikev2 import IKEv2Manager
    IKEv2Manager.generate_config(domain)
    log.info("IKEv2 VPN 已初始化完成 (Cert + EAP 模式)")


@cli.command()
def uninstall():
    """[卸载] 停止服务并清理文件"""
    if click.confirm('⚠️  警告: 此操作将删除所有配置、证书和服务，确定吗?'):
        Installer.cleanup()


@cli.group()
def update():
    """[更新] 更新组件版本"""
    pass


@update.command(name='xray')
@click.option('--version', 'target_version', default=None, help='指定版本号（如 1.8.6），留空则获取最新版')
def update_xray(target_version):
    """更新 Xray Core 到指定版本"""
    Installer.update_xray(target_version)


@update.command(name='strongswan')
def update_strongswan():
    """更新 StrongSwan 到最新版本"""
    Installer.update_strongswan()


@cli.group()
def user():
    """[用户] 管理 VPN/代理 用户"""
    pass


@user.command(name='add')
@click.option('--type', 'vpn_type', type=click.Choice(['v2ray', 'ikev2-cert', 'ikev2-eap']), required=True)
@click.option('--username', prompt='请输入用户名')
def user_add(vpn_type, username):
    """添加用户"""
    UserManager.add(vpn_type, username)


@user.command(name='del')
@click.option('--type', 'vpn_type', type=click.Choice(['v2ray', 'ikev2-cert', 'ikev2-eap']), required=True)
@click.option('--username', prompt='请输入用户名')
def user_del(vpn_type, username):
    """删除用户"""
    UserManager.remove(vpn_type, username)


@user.command(name='list')
def user_list():
    """列出所有用户"""
    UserManager.list_users()


@user.command(name='info')
@click.option('--type', 'vpn_type', type=click.Choice(['v2ray']), required=True)
@click.option('--username', prompt='请输入用户名')
def user_info(vpn_type, username):
    """显示用户连接信息（URL + 二维码）"""
    UserManager.info(vpn_type, username)


@cli.command()
def status():
    """[状态] 检查服务运行状态"""
    table = Table(title="🛡️ Nexus-VPN 系统状态", show_header=True, header_style="bold blue")
    table.add_column("组件", style="cyan")
    table.add_column("状态信息", style="bold")
    table.add_column("附加详情", style="dim")

    xray_status = check_service("nexus-xray")
    xray_port = f"TCP/443: {check_port(443, 'tcp')}"
    table.add_row("Xray (VLESS)", xray_status, xray_port)

    # 检测 strongswan 服务名
    ss_name = "strongswan"
    try:
        result = subprocess.run(
            ["systemctl", "list-unit-files", "--type=service"],
            capture_output=True, text=True
        )
        if "strongswan-starter" in result.stdout:
            ss_name = "strongswan-starter"
    except subprocess.SubprocessError:
        pass

    ike_status = check_service(ss_name)
    ike_ports = f"UDP/500:  {check_port(500, 'u')}\nUDP/4500: {check_port(4500, 'u')}"
    table.add_row("StrongSwan", ike_status, ike_ports)

    try:
        with open("/proc/sys/net/ipv4/ip_forward") as f:
            fw = "[green]Enabled[/green]" if f.read().strip() == "1" else "[red]Disabled[/red]"
    except OSError:
        fw = "[red]Unknown[/red]"

    table.add_row("Kernel", check_bbr(), f"IP Forward: {fw}")
    console.print(table)


if __name__ == '__main__':
    cli()
