"""测试 nexus_vpn.core.user_mgr 模块"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock


class TestUserManager:
    """UserManager 类测试"""
    
    def test_user_manager_import(self):
        """测试 UserManager 可以正常导入"""
        from nexus_vpn.core.user_mgr import UserManager
        assert UserManager is not None
    
    def test_add_v2ray_user(self, mocker):
        """测试添加 V2Ray 用户"""
        from nexus_vpn.core.user_mgr import UserManager
        
        mock_add = mocker.patch('nexus_vpn.protocols.v2ray.V2RayManager.add_user')
        
        UserManager.add('v2ray', 'testuser')
        
        mock_add.assert_called_once_with('testuser')
    
    def test_add_ikev2_cert_user(self, mocker, temp_dir):
        """测试添加 IKEv2 证书用户"""
        from nexus_vpn.core.user_mgr import UserManager
        
        p12_path = os.path.join(temp_dir, "testuser.p12")
        with open(p12_path, 'wb') as f:
            f.write(b"FAKE P12")
        
        mock_issue = mocker.patch(
            'nexus_vpn.core.cert_mgr.CertManager.issue_user_cert',
            return_value=p12_path
        )
        mock_get_domain = mocker.patch.object(
            UserManager, '_get_domain', return_value='example.com'
        )
        mock_mobileconfig = mocker.patch(
            'nexus_vpn.protocols.ikev2.IKEv2Manager.create_mobileconfig',
            return_value='<?xml version="1.0"?><plist/>'
        )
        
        # 切换到临时目录以创建 mobileconfig 文件
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            UserManager.add('ikev2-cert', 'testuser')
        finally:
            os.chdir(original_cwd)
        
        mock_issue.assert_called_once_with('testuser')
        mock_get_domain.assert_called_once()
        mock_mobileconfig.assert_called_once_with('testuser', 'example.com', p12_path)
        
        # 验证 mobileconfig 文件被创建
        mobileconfig_path = os.path.join(temp_dir, "testuser.mobileconfig")
        assert os.path.exists(mobileconfig_path)
    
    def test_add_ikev2_eap_user(self, mocker):
        """测试添加 IKEv2 EAP 用户"""
        from nexus_vpn.core.user_mgr import UserManager
        
        mocker.patch('click.prompt', return_value='testpassword')
        mock_add_eap = mocker.patch(
            'nexus_vpn.protocols.ikev2.IKEv2Manager.add_eap_user'
        )
        mocker.patch.object(UserManager, '_get_domain', return_value='example.com')
        
        UserManager.add('ikev2-eap', 'testuser')
        
        mock_add_eap.assert_called_once_with('testuser', 'testpassword')
    
    def test_remove_v2ray_user(self, mocker):
        """测试删除 V2Ray 用户"""
        from nexus_vpn.core.user_mgr import UserManager
        
        mock_remove = mocker.patch('nexus_vpn.protocols.v2ray.V2RayManager.remove_user')
        
        UserManager.remove('v2ray', 'testuser')
        
        mock_remove.assert_called_once_with('testuser')
    
    def test_remove_ikev2_cert_user(self, mocker, temp_dir):
        """测试删除 IKEv2 证书用户"""
        from nexus_vpn.core.user_mgr import UserManager
        from nexus_vpn.core.cert_mgr import CertManager
        
        pki_dir = os.path.join(temp_dir, "pki")
        certs_dir = os.path.join(pki_dir, "certs")
        os.makedirs(certs_dir, exist_ok=True)
        mocker.patch.object(CertManager, 'PKI_DIR', pki_dir)
        
        # 创建测试文件
        for ext in ['.crt', '.key', '.p12']:
            with open(os.path.join(certs_dir, f"testuser{ext}"), 'w') as f:
                f.write("FAKE")
        
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        # 创建 mobileconfig 文件
        with open("testuser.mobileconfig", 'w') as f:
            f.write("FAKE")
        
        try:
            UserManager.remove('ikev2-cert', 'testuser')
        finally:
            os.chdir(original_cwd)
        
        # 验证文件被删除
        assert not os.path.exists(os.path.join(certs_dir, "testuser.crt"))
        assert not os.path.exists(os.path.join(temp_dir, "testuser.mobileconfig"))
    
    def test_remove_ikev2_eap_user(self, mocker):
        """测试删除 IKEv2 EAP 用户"""
        from nexus_vpn.core.user_mgr import UserManager
        
        mock_remove = mocker.patch(
            'nexus_vpn.protocols.ikev2.IKEv2Manager.remove_eap_user'
        )
        
        UserManager.remove('ikev2-eap', 'testuser')
        
        mock_remove.assert_called_once_with('testuser')
    
    def test_list_users_v2ray(self, mocker, mock_xray_config):
        """测试列出 V2Ray 用户"""
        from nexus_vpn.core.user_mgr import UserManager
        from nexus_vpn.protocols.v2ray import V2RayManager
        
        mocker.patch.object(V2RayManager, 'CONFIG_PATH', mock_xray_config)
        mocker.patch('nexus_vpn.protocols.ikev2.IKEv2Manager.SECRETS_FILE', '/nonexistent')
        
        # Mock CertManager.PKI_DIR 指向不存在的目录
        mocker.patch('nexus_vpn.core.cert_mgr.CertManager.PKI_DIR', '/nonexistent')
        
        # 不应该抛出异常
        UserManager.list_users()
    
    def test_list_users_ikev2_eap(self, mocker, mock_ipsec_secrets):
        """测试列出 IKEv2 EAP 用户"""
        from nexus_vpn.core.user_mgr import UserManager
        from nexus_vpn.protocols.ikev2 import IKEv2Manager
        from nexus_vpn.protocols.v2ray import V2RayManager
        
        mocker.patch.object(IKEv2Manager, 'SECRETS_FILE', mock_ipsec_secrets)
        mocker.patch.object(V2RayManager, 'CONFIG_PATH', '/nonexistent')
        mocker.patch('nexus_vpn.core.cert_mgr.CertManager.PKI_DIR', '/nonexistent')
        
        # 不应该抛出异常
        UserManager.list_users()
    
    def test_get_domain_from_ipsec_conf(self, mocker, mock_ipsec_conf):
        """测试从 ipsec.conf 获取域名"""
        from nexus_vpn.core.user_mgr import UserManager
        
        mocker.patch('builtins.open', mocker.mock_open(read_data="""
config setup
conn IKEv2-Cert
    leftid=@vpn.example.com
    auto=add
"""))
        
        result = UserManager._get_domain()
        assert result == "vpn.example.com"
    
    def test_get_domain_fallback_to_ip(self, mocker):
        """测试获取域名失败时回退到 IP"""
        from nexus_vpn.core.user_mgr import UserManager
        
        # 模拟文件不存在
        mocker.patch('builtins.open', side_effect=OSError)
        
        # 模拟 urllib 请求
        mock_response = MagicMock()
        mock_response.read.return_value = b"1.2.3.4"
        mock_response.__enter__ = lambda s: mock_response
        mock_response.__exit__ = MagicMock(return_value=False)
        
        mocker.patch('urllib.request.urlopen', return_value=mock_response)
        
        result = UserManager._get_domain()
        assert result == "1.2.3.4"
    
    def test_get_domain_all_fail(self, mocker):
        """测试所有获取域名方法都失败时返回默认值"""
        from nexus_vpn.core.user_mgr import UserManager
        
        mocker.patch('builtins.open', side_effect=OSError)
        mocker.patch('urllib.request.urlopen', side_effect=Exception("Network error"))
        
        result = UserManager._get_domain()
        assert result == "your-server-ip"
