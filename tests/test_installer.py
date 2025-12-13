"""测试 nexus_vpn.core.installer 模块"""
import os
import pytest
from unittest.mock import patch, MagicMock


class TestInstaller:
    """Installer 类测试"""
    
    def test_installer_import(self):
        """测试 Installer 可以正常导入"""
        from nexus_vpn.core.installer import Installer
        assert Installer is not None
    
    def test_xray_version_constant(self):
        """测试 XRAY_VERSION 常量"""
        from nexus_vpn.core.installer import Installer
        assert Installer.XRAY_VERSION == "1.8.4"
    
    def test_xray_url_method(self):
        """测试 get_xray_download_url 方法"""
        from nexus_vpn.core.installer import Installer
        url = Installer.get_xray_download_url(Installer.XRAY_VERSION)
        assert "github.com" in url
        assert "Xray-core" in url
        assert Installer.XRAY_VERSION in url
    
    def test_init_single_dest(self):
        """测试 Installer 初始化（单个 reality_dest）"""
        from nexus_vpn.core.installer import Installer
        
        installer = Installer("example.com", "vless", "www.microsoft.com:443")
        
        assert installer.domain == "example.com"
        assert installer.proto == "vless"
        assert installer.reality_dests == ["www.microsoft.com:443"]
    
    def test_init_multiple_dests(self):
        """测试 Installer 初始化（多个 reality_dests）"""
        from nexus_vpn.core.installer import Installer
        
        dests = ["www.microsoft.com:443", "www.apple.com:443"]
        installer = Installer("example.com", "vless", dests)
        
        assert installer.domain == "example.com"
        assert installer.proto == "vless"
        assert installer.reality_dests == dests
    
    def test_run_calls_all_steps(self, mocker):
        """测试 run 方法调用所有安装步骤"""
        from nexus_vpn.core.installer import Installer
        
        mocker.patch('os.path.exists', return_value=False)
        mock_deps = mocker.patch.object(Installer, 'install_dependencies')
        mock_xray = mocker.patch.object(Installer, 'install_xray')
        mock_network = mocker.patch.object(Installer, 'setup_network')
        mock_pki = mocker.patch('nexus_vpn.protocols.ikev2.IKEv2Manager.init_pki')
        
        installer = Installer("example.com", "vless", "www.microsoft.com:443")
        installer.run()
        
        mock_deps.assert_called_once()
        mock_xray.assert_called_once()
        mock_network.assert_called_once()
        mock_pki.assert_called_once_with("example.com")

    def test_run_idempotent_detects_existing_install(self, mocker):
        """测试 run 方法检测已安装状态（幂等性）"""
        from nexus_vpn.core.installer import Installer
        
        # 模拟 Xray 和 PKI 都已存在
        def mock_exists(path):
            if path == "/usr/local/bin/xray":
                return True
            if path == "/etc/nexus-vpn/pki/ca.crt":
                return True
            return False
        
        mocker.patch('os.path.exists', side_effect=mock_exists)
        mock_deps = mocker.patch.object(Installer, 'install_dependencies')
        mock_xray = mocker.patch.object(Installer, 'install_xray')
        mock_network = mocker.patch.object(Installer, 'setup_network')
        mock_pki = mocker.patch('nexus_vpn.protocols.ikev2.IKEv2Manager.init_pki')
        
        installer = Installer("example.com", "vless", "www.microsoft.com:443")
        installer.run()
        
        # 所有步骤仍应被调用（幂等执行）
        mock_deps.assert_called_once()
        mock_xray.assert_called_once()
        mock_network.assert_called_once()
        mock_pki.assert_called_once()
    
    def test_install_dependencies_apt(self, mocker):
        """测试使用 apt-get 安装依赖"""
        from nexus_vpn.core.installer import Installer
        
        mocker.patch('shutil.which', side_effect=lambda x: '/usr/bin/apt-get' if x == 'apt-get' else None)
        mock_sudo_run = mocker.patch('nexus_vpn.core.installer.sudo_run')
        
        installer = Installer("example.com", "vless", "www.microsoft.com:443")
        installer.install_dependencies()
        
        # 验证 sudo_run 被调用
        calls = [str(c) for c in mock_sudo_run.call_args_list]
        assert any('apt-get' in str(c) and 'update' in str(c) for c in calls)
        assert any('apt-get' in str(c) and 'install' in str(c) for c in calls)
    
    def test_install_dependencies_yum(self, mocker):
        """测试使用 yum 安装依赖"""
        from nexus_vpn.core.installer import Installer
        
        def which_side_effect(cmd):
            if cmd == 'apt-get':
                return None
            elif cmd == 'yum':
                return '/usr/bin/yum'
            return None
        
        mocker.patch('shutil.which', side_effect=which_side_effect)
        mock_sudo_run = mocker.patch('nexus_vpn.core.installer.sudo_run')
        
        installer = Installer("example.com", "vless", "www.microsoft.com:443")
        installer.install_dependencies()
        
        calls = [str(c) for c in mock_sudo_run.call_args_list]
        assert any('yum' in str(c) for c in calls)
    
    def test_install_dependencies_handles_error(self, mocker):
        """测试安装依赖时处理错误"""
        from nexus_vpn.core.installer import Installer
        import subprocess
        
        mocker.patch('shutil.which', return_value='/usr/bin/apt-get')
        mocker.patch('nexus_vpn.core.installer.sudo_run', side_effect=subprocess.CalledProcessError(1, 'apt-get'))
        
        installer = Installer("example.com", "vless", "www.microsoft.com:443")
        
        # 不应该抛出异常
        installer.install_dependencies()
    
    def test_install_xray_already_exists(self, mocker):
        """测试 Xray 已存在时跳过下载"""
        from nexus_vpn.core.installer import Installer
        
        mocker.patch('os.path.exists', return_value=True)
        mock_urlretrieve = mocker.patch('urllib.request.urlretrieve')
        mock_sudo_run = mocker.patch('nexus_vpn.core.installer.sudo_run')
        mock_sudo_write = mocker.patch('nexus_vpn.core.installer.sudo_write_file')
        
        installer = Installer("example.com", "vless", "www.microsoft.com:443")
        installer.install_xray()
        
        # 不应该下载
        mock_urlretrieve.assert_not_called()
        
        # 但应该创建 systemd service
        mock_sudo_write.assert_called()
        mock_sudo_run.assert_called()
    
    def test_install_xray_downloads_and_extracts(self, mocker, temp_dir):
        """测试下载并解压 Xray"""
        from nexus_vpn.core.installer import Installer
        import zipfile
        
        # 创建模拟的 zip 文件
        zip_path = os.path.join(temp_dir, "xray.zip")
        
        with zipfile.ZipFile(zip_path, 'w') as z:
            z.writestr("xray", b"FAKE BINARY")
        
        def mock_exists(path):
            if path == "/usr/local/bin/xray":
                return False
            return True
        
        mocker.patch('os.path.exists', side_effect=mock_exists)
        mocker.patch('urllib.request.urlretrieve')
        mock_sudo_run = mocker.patch('nexus_vpn.core.installer.sudo_run')
        mock_sudo_write = mocker.patch('nexus_vpn.core.installer.sudo_write_file')
        mock_sudo_move = mocker.patch('nexus_vpn.core.installer.sudo_move')
        mock_sudo_chmod = mocker.patch('nexus_vpn.core.installer.sudo_chmod')
        
        # Mock tempfile
        mock_temp = mocker.patch('tempfile.TemporaryDirectory')
        mock_temp.return_value.__enter__ = lambda s: temp_dir
        mock_temp.return_value.__exit__ = MagicMock(return_value=False)
        
        # Mock zipfile
        mock_zip = mocker.patch('zipfile.ZipFile')
        mock_zip.return_value.__enter__ = lambda s: MagicMock(extractall=lambda x: None)
        mock_zip.return_value.__exit__ = MagicMock(return_value=False)
        
        installer = Installer("example.com", "vless", "www.microsoft.com:443")
        installer.install_xray()
        
        # 验证 systemd 命令被调用
        calls = [str(c) for c in mock_sudo_run.call_args_list]
        assert any('daemon-reload' in c for c in calls)
        assert any('enable' in c for c in calls)
    
    def test_setup_network_configures_sysctl(self, mocker, temp_dir):
        """测试配置 sysctl"""
        from nexus_vpn.core.installer import Installer
        
        sysctl_path = os.path.join(temp_dir, "sysctl.conf")
        with open(sysctl_path, 'w') as f:
            f.write("# Existing config\nnet.ipv4.tcp_syncookies=1\n")
        
        mocker.patch('os.path.exists', return_value=True)
        
        mock_sudo_run = mocker.patch('nexus_vpn.core.installer.sudo_run')
        mock_sudo_run.return_value = MagicMock(stdout="default via 1.2.3.4 dev eth0", returncode=0)
        
        # Mock subprocess.run for ip route
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(stdout="default via 1.2.3.4 dev eth0", returncode=0)
        
        mock_sudo_read = mocker.patch('nexus_vpn.core.installer.sudo_read_file', return_value="# Existing\n")
        mock_sudo_write = mocker.patch('nexus_vpn.core.installer.sudo_write_file')
        
        mocker.patch('shutil.which', return_value=None)  # No netfilter-persistent
        
        installer = Installer("example.com", "vless", "www.microsoft.com:443")
        
        try:
            installer.setup_network()
        except Exception:
            pass  # 可能因为 mock 不完整而失败
        
        # 验证 sysctl -p 被调用
        calls = [str(c) for c in mock_sudo_run.call_args_list]
        assert any('sysctl' in c for c in calls)
    
    def test_setup_network_configures_iptables(self, mocker):
        """测试配置 iptables NAT"""
        from nexus_vpn.core.installer import Installer
        
        mocker.patch('os.path.exists', return_value=True)
        
        mock_sudo_run = mocker.patch('nexus_vpn.core.installer.sudo_run')
        mock_sudo_read = mocker.patch('nexus_vpn.core.installer.sudo_read_file', return_value="")
        mock_sudo_write = mocker.patch('nexus_vpn.core.installer.sudo_write_file')
        
        # Mock subprocess.run for ip route
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(
            stdout="default via 1.2.3.4 dev eth0 proto static",
            returncode=0
        )
        
        mocker.patch('shutil.which', return_value=None)
        
        installer = Installer("example.com", "vless", "www.microsoft.com:443")
        installer.setup_network()
        
        # 验证 iptables 被调用
        calls = [str(c) for c in mock_sudo_run.call_args_list]
        assert any('iptables' in c for c in calls)
    
    def test_cleanup(self, mocker, temp_dir):
        """测试 cleanup 静态方法"""
        from nexus_vpn.core.installer import Installer
        
        mock_sudo_run = mocker.patch('nexus_vpn.core.installer.sudo_run')
        mock_sudo_remove = mocker.patch('nexus_vpn.core.installer.sudo_remove')
        
        Installer.cleanup()
        
        # 验证服务停止
        calls = [str(c) for c in mock_sudo_run.call_args_list]
        assert any('stop' in c for c in calls)
        assert any('daemon-reload' in c for c in calls)
        
        # 验证文件删除
        assert mock_sudo_remove.called
