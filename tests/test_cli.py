"""测试 nexus_vpn.cli 模块"""
import os
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock


class TestCheckFunctions:
    """测试 CLI 辅助函数"""
    
    def test_allowed_services_constant(self):
        """测试 ALLOWED_SERVICES 常量"""
        from nexus_vpn.cli import ALLOWED_SERVICES
        assert "nexus-xray" in ALLOWED_SERVICES
        assert "strongswan" in ALLOWED_SERVICES
        assert "strongswan-starter" in ALLOWED_SERVICES
        assert "ipsec" in ALLOWED_SERVICES
    
    def test_check_service_valid_active(self, mocker):
        """测试 check_service 对活跃服务"""
        from nexus_vpn.cli import check_service
        
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(stdout="active\n", returncode=0)
        
        result = check_service("nexus-xray")
        
        assert "[green]active[/green]" == result
    
    def test_check_service_valid_inactive(self, mocker):
        """测试 check_service 对非活跃服务"""
        from nexus_vpn.cli import check_service
        
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(stdout="inactive\n", returncode=0)
        
        result = check_service("nexus-xray")
        
        assert "[red]inactive[/red]" == result
    
    def test_check_service_invalid_name(self):
        """测试 check_service 对无效服务名"""
        from nexus_vpn.cli import check_service
        
        result = check_service("malicious-service")
        
        assert result == "[red]invalid[/red]"
    
    def test_check_service_injection_attempt(self):
        """测试 check_service 防止命令注入"""
        from nexus_vpn.cli import check_service
        
        result = check_service("nexus-xray; rm -rf /")
        assert result == "[red]invalid[/red]"
        
        result = check_service("nexus-xray && cat /etc/passwd")
        assert result == "[red]invalid[/red]"
    
    def test_check_service_subprocess_error(self, mocker):
        """测试 check_service 处理 subprocess 错误"""
        from nexus_vpn.cli import check_service
        import subprocess
        
        mocker.patch('subprocess.run', side_effect=subprocess.SubprocessError)
        
        result = check_service("nexus-xray")
        
        assert result == "[red]error[/red]"
    
    def test_check_port_valid_tcp_open(self, mocker):
        """测试 check_port 对开放的 TCP 端口"""
        from nexus_vpn.cli import check_port
        
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(stdout="LISTEN 0 128 0.0.0.0:443 0.0.0.0:*")
        
        result = check_port(443, "tcp")
        
        assert result == "[green]OPEN[/green]"
    
    def test_check_port_valid_tcp_closed(self, mocker):
        """测试 check_port 对关闭的 TCP 端口"""
        from nexus_vpn.cli import check_port
        
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(stdout="")
        
        result = check_port(443, "tcp")
        
        assert result == "[red]CLOSED[/red]"
    
    def test_check_port_valid_udp(self, mocker):
        """测试 check_port 对 UDP 端口"""
        from nexus_vpn.cli import check_port
        
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(stdout="UNCONN 0 0 0.0.0.0:500 0.0.0.0:*")
        
        result = check_port(500, "udp")
        
        assert result == "[green]OPEN[/green]"
    
    def test_check_port_invalid_port(self):
        """测试 check_port 对无效端口"""
        from nexus_vpn.cli import check_port
        
        assert check_port(0, "tcp") == "[red]INVALID[/red]"
        assert check_port(-1, "tcp") == "[red]INVALID[/red]"
        assert check_port(65536, "tcp") == "[red]INVALID[/red]"
        assert check_port("443", "tcp") == "[red]INVALID[/red]"
    
    def test_check_port_subprocess_error(self, mocker):
        """测试 check_port 处理 subprocess 错误"""
        from nexus_vpn.cli import check_port
        import subprocess
        
        mocker.patch('subprocess.run', side_effect=subprocess.SubprocessError)
        
        result = check_port(443, "tcp")
        
        assert result == "[red]CLOSED[/red]"
    
    def test_check_bbr_enabled(self, mocker):
        """测试 check_bbr 当 BBR 启用时"""
        from nexus_vpn.cli import check_bbr
        
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(stdout="bbr\n")
        
        result = check_bbr()
        
        assert "BBR" in result
        assert "[green]" in result
    
    def test_check_bbr_disabled(self, mocker):
        """测试 check_bbr 当 BBR 未启用时"""
        from nexus_vpn.cli import check_bbr
        
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(stdout="cubic\n")
        
        result = check_bbr()
        
        assert "cubic" in result
        assert "[yellow]" in result
    
    def test_check_bbr_error(self, mocker):
        """测试 check_bbr 处理错误"""
        from nexus_vpn.cli import check_bbr
        import subprocess
        
        mocker.patch('subprocess.run', side_effect=subprocess.SubprocessError)
        
        result = check_bbr()
        
        assert result == "[red]Unknown[/red]"


class TestCLICommands:
    """测试 CLI 命令"""
    
    def test_cli_help(self, mocker):
        """测试 CLI 帮助信息"""
        from nexus_vpn.cli import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert "nexus-vpn" in result.output
    
    def test_cli_install_success(self, mocker):
        """测试 install 命令成功执行"""
        from nexus_vpn.cli import cli
        
        mocker.patch('nexus_vpn.cli.SystemChecker.check_os')
        # mock cli 模块中导入的 Installer
        mock_installer_class = mocker.patch('nexus_vpn.cli.Installer')
        mock_installer_instance = MagicMock()
        mock_installer_class.return_value = mock_installer_instance
        
        mock_v2ray = mocker.patch('nexus_vpn.cli.V2RayManager.create_config')
        mock_v2ray.return_value = {"uuid": "test", "public_key": "pk", "short_id": "id", "sni": "sni", "port": 443}
        mocker.patch('nexus_vpn.cli.V2RayManager.print_connection_info')
        mocker.patch('nexus_vpn.protocols.ikev2.IKEv2Manager.generate_config')
        
        runner = CliRunner()
        result = runner.invoke(cli, ['install', '--domain', 'example.com'])
        
        assert result.exit_code == 0
        mock_installer_class.assert_called_once()
        mock_installer_instance.run.assert_called_once()
    
    def test_cli_uninstall_confirmed(self, mocker):
        """测试 uninstall 命令确认后执行"""
        from nexus_vpn.cli import cli
        
        mock_cleanup = mocker.patch('nexus_vpn.core.installer.Installer.cleanup')
        
        runner = CliRunner()
        result = runner.invoke(cli, ['uninstall'], input='y\n')
        
        assert result.exit_code == 0
        mock_cleanup.assert_called_once()
    
    def test_cli_uninstall_cancelled(self, mocker):
        """测试 uninstall 命令取消"""
        from nexus_vpn.cli import cli
        
        mock_cleanup = mocker.patch('nexus_vpn.core.installer.Installer.cleanup')
        
        runner = CliRunner()
        result = runner.invoke(cli, ['uninstall'], input='n\n')
        
        # 用户取消时 click.confirm 返回 False，不执行 cleanup，但不会抛异常
        mock_cleanup.assert_not_called()
    
    def test_cli_user_group(self, mocker):
        """测试 user 命令组"""
        from nexus_vpn.cli import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['user', '--help'])
        
        assert result.exit_code == 0
        assert "add" in result.output
        assert "del" in result.output
        assert "list" in result.output
    
    def test_cli_user_add_v2ray(self, mocker):
        """测试添加 V2Ray 用户"""
        from nexus_vpn.cli import cli
        
        mock_add = mocker.patch('nexus_vpn.core.user_mgr.UserManager.add')
        
        runner = CliRunner()
        result = runner.invoke(cli, ['user', 'add', '--type', 'v2ray', '--username', 'testuser'])
        
        assert result.exit_code == 0
        mock_add.assert_called_once_with('v2ray', 'testuser')
    
    def test_cli_user_del(self, mocker):
        """测试删除用户"""
        from nexus_vpn.cli import cli
        
        mock_remove = mocker.patch('nexus_vpn.core.user_mgr.UserManager.remove')
        
        runner = CliRunner()
        result = runner.invoke(cli, ['user', 'del', '--type', 'v2ray', '--username', 'testuser'])
        
        assert result.exit_code == 0
        mock_remove.assert_called_once_with('v2ray', 'testuser')
    
    def test_cli_user_list(self, mocker):
        """测试列出用户"""
        from nexus_vpn.cli import cli
        
        mock_list = mocker.patch('nexus_vpn.core.user_mgr.UserManager.list_users')
        
        runner = CliRunner()
        result = runner.invoke(cli, ['user', 'list'])
        
        assert result.exit_code == 0
        mock_list.assert_called_once()
    
    def test_cli_status(self, mocker):
        """测试 status 命令"""
        from nexus_vpn.cli import cli
        
        mocker.patch('subprocess.run', return_value=MagicMock(stdout="active\n"))
        mocker.patch('builtins.open', mocker.mock_open(read_data="1"))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['status'])
        
        assert result.exit_code == 0
        assert "Nexus-VPN" in result.output or "状态" in result.output
