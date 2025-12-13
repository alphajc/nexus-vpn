"""测试 nexus_vpn.protocols.ikev2 模块"""
import os
import base64
import pytest
from unittest.mock import patch, MagicMock


class TestIKEv2Manager:
    """IKEv2Manager 类测试"""
    
    def test_ikev2_manager_import(self):
        """测试 IKEv2Manager 可以正常导入"""
        from nexus_vpn.protocols.ikev2 import IKEv2Manager
        assert IKEv2Manager is not None
    
    def test_secrets_file_constant(self):
        """测试 SECRETS_FILE 常量"""
        from nexus_vpn.protocols.ikev2 import IKEv2Manager
        assert IKEv2Manager.SECRETS_FILE == "/etc/ipsec.secrets"
    
    def test_ipsec_conf_file_constant(self):
        """测试 IPSEC_CONF_FILE 常量"""
        from nexus_vpn.protocols.ikev2 import IKEv2Manager
        assert IKEv2Manager.IPSEC_CONF_FILE == "/etc/ipsec.conf"
    
    def test_init_pki_calls_cert_manager(self, mocker):
        """测试 init_pki 调用 CertManager.setup_ca"""
        from nexus_vpn.protocols.ikev2 import IKEv2Manager
        mock_setup_ca = mocker.patch('nexus_vpn.core.cert_mgr.CertManager.setup_ca')
        
        IKEv2Manager.init_pki("example.com")
        
        mock_setup_ca.assert_called_once_with("example.com")
    
    def test_generate_config_creates_file(self, mocker, temp_dir):
        """测试 generate_config 创建配置文件"""
        from nexus_vpn.protocols.ikev2 import IKEv2Manager
        
        conf_path = os.path.join(temp_dir, "ipsec.conf")
        mocker.patch.object(IKEv2Manager, 'IPSEC_CONF_FILE', conf_path)
        mocker.patch('subprocess.run')
        
        IKEv2Manager.generate_config("example.com")
        
        assert os.path.exists(conf_path)
        with open(conf_path, 'r') as f:
            content = f.read()
        
        assert "leftid=@example.com" in content
        assert "conn IKEv2-Cert" in content
        assert "conn IKEv2-EAP" in content
        assert "keyexchange=ikev2" in content
    
    def test_generate_config_sanitizes_domain(self, mocker, temp_dir):
        """测试 generate_config 清理域名中的额外内容"""
        from nexus_vpn.protocols.ikev2 import IKEv2Manager
        
        conf_path = os.path.join(temp_dir, "ipsec.conf")
        mocker.patch.object(IKEv2Manager, 'IPSEC_CONF_FILE', conf_path)
        mocker.patch('subprocess.run')
        
        # 域名带有额外空格
        IKEv2Manager.generate_config("example.com   extra stuff")
        
        with open(conf_path, 'r') as f:
            content = f.read()
        
        assert "leftid=@example.com" in content
        assert "extra" not in content
    
    def test_generate_config_calls_ipsec_reload(self, mocker, temp_dir):
        """测试 generate_config 调用 ipsec reload"""
        from nexus_vpn.protocols.ikev2 import IKEv2Manager
        
        conf_path = os.path.join(temp_dir, "ipsec.conf")
        mocker.patch.object(IKEv2Manager, 'IPSEC_CONF_FILE', conf_path)
        mock_run = mocker.patch('subprocess.run')
        
        IKEv2Manager.generate_config("example.com")
        
        mock_run.assert_called_with(["ipsec", "reload"])
    
    def test_remove_user_from_secrets_file_not_exists(self, mocker, temp_dir):
        """测试 _remove_user_from_secrets 当文件不存在时"""
        from nexus_vpn.protocols.ikev2 import IKEv2Manager
        
        secrets_path = os.path.join(temp_dir, "ipsec.secrets")
        mocker.patch.object(IKEv2Manager, 'SECRETS_FILE', secrets_path)
        
        # 不应该抛出异常
        IKEv2Manager._remove_user_from_secrets("testuser")
    
    def test_remove_user_from_secrets_removes_user(self, mocker, temp_dir):
        """测试 _remove_user_from_secrets 移除用户"""
        from nexus_vpn.protocols.ikev2 import IKEv2Manager
        
        secrets_path = os.path.join(temp_dir, "ipsec.secrets")
        mocker.patch.object(IKEv2Manager, 'SECRETS_FILE', secrets_path)
        
        # 创建 secrets 文件
        content = """: RSA server.key
testuser1 : EAP "password1"
testuser2 : EAP "password2"
"testuser3" : EAP "password3"
"""
        with open(secrets_path, 'w') as f:
            f.write(content)
        
        IKEv2Manager._remove_user_from_secrets("testuser1")
        
        with open(secrets_path, 'r') as f:
            result = f.read()
        
        assert "testuser1" not in result
        assert "testuser2 : EAP" in result
        assert '"testuser3" : EAP' in result
        assert ": RSA server.key" in result
    
    def test_remove_user_from_secrets_removes_quoted_user(self, mocker, temp_dir):
        """测试 _remove_user_from_secrets 移除带引号的用户"""
        from nexus_vpn.protocols.ikev2 import IKEv2Manager
        
        secrets_path = os.path.join(temp_dir, "ipsec.secrets")
        mocker.patch.object(IKEv2Manager, 'SECRETS_FILE', secrets_path)
        
        content = """: RSA server.key
"quoteduser" : EAP "password"
normaluser : EAP "password"
"""
        with open(secrets_path, 'w') as f:
            f.write(content)
        
        IKEv2Manager._remove_user_from_secrets("quoteduser")
        
        with open(secrets_path, 'r') as f:
            result = f.read()
        
        assert "quoteduser" not in result
        assert "normaluser : EAP" in result
    
    def test_add_eap_user(self, mocker, temp_dir):
        """测试 add_eap_user 添加用户"""
        from nexus_vpn.protocols.ikev2 import IKEv2Manager
        
        secrets_path = os.path.join(temp_dir, "ipsec.secrets")
        mocker.patch.object(IKEv2Manager, 'SECRETS_FILE', secrets_path)
        mock_run = mocker.patch('subprocess.run')
        
        # 创建空 secrets 文件
        with open(secrets_path, 'w') as f:
            f.write(": RSA server.key\n")
        
        IKEv2Manager.add_eap_user("newuser", "newpassword")
        
        with open(secrets_path, 'r') as f:
            result = f.read()
        
        assert 'newuser : EAP "newpassword"' in result
        mock_run.assert_called_with(["ipsec", "rereadsecrets"])
    
    def test_add_eap_user_replaces_existing(self, mocker, temp_dir):
        """测试 add_eap_user 替换现有用户"""
        from nexus_vpn.protocols.ikev2 import IKEv2Manager
        
        secrets_path = os.path.join(temp_dir, "ipsec.secrets")
        mocker.patch.object(IKEv2Manager, 'SECRETS_FILE', secrets_path)
        mocker.patch('subprocess.run')
        
        # 创建包含用户的 secrets 文件
        with open(secrets_path, 'w') as f:
            f.write(': RSA server.key\nexistinguser : EAP "oldpassword"\n')
        
        IKEv2Manager.add_eap_user("existinguser", "newpassword")
        
        with open(secrets_path, 'r') as f:
            result = f.read()
        
        assert 'existinguser : EAP "newpassword"' in result
        assert "oldpassword" not in result
    
    def test_remove_eap_user(self, mocker, temp_dir):
        """测试 remove_eap_user 删除用户"""
        from nexus_vpn.protocols.ikev2 import IKEv2Manager
        
        secrets_path = os.path.join(temp_dir, "ipsec.secrets")
        mocker.patch.object(IKEv2Manager, 'SECRETS_FILE', secrets_path)
        mock_run = mocker.patch('subprocess.run')
        
        with open(secrets_path, 'w') as f:
            f.write(': RSA server.key\ndeleteuser : EAP "password"\n')
        
        IKEv2Manager.remove_eap_user("deleteuser")
        
        with open(secrets_path, 'r') as f:
            result = f.read()
        
        assert "deleteuser" not in result
        mock_run.assert_called_with(["ipsec", "rereadsecrets"])
    
    def test_create_mobileconfig_structure(self, mocker, temp_dir):
        """测试 create_mobileconfig 生成正确的 XML 结构"""
        from nexus_vpn.protocols.ikev2 import IKEv2Manager
        from nexus_vpn.core.cert_mgr import CertManager
        
        # 创建模拟的 CA 和 P12 文件
        pki_dir = os.path.join(temp_dir, "pki")
        os.makedirs(pki_dir, exist_ok=True)
        mocker.patch.object(CertManager, 'PKI_DIR', pki_dir)
        
        ca_content = b"FAKE CA CONTENT"
        with open(os.path.join(pki_dir, "ca.crt"), 'wb') as f:
            f.write(ca_content)
        
        p12_path = os.path.join(temp_dir, "user.p12")
        p12_content = b"FAKE P12 CONTENT"
        with open(p12_path, 'wb') as f:
            f.write(p12_content)
        
        result = IKEv2Manager.create_mobileconfig("testuser", "example.com", p12_path)
        
        # 验证 XML 结构
        assert '<?xml version="1.0" encoding="UTF-8"?>' in result
        assert "<!DOCTYPE plist" in result
        assert "<plist version=" in result
        assert "PayloadContent" in result
        assert "com.apple.security.root" in result
        assert "com.apple.security.pkcs12" in result
        assert "com.apple.vpn.managed" in result
        assert "IKEv2" in result
        assert "example.com" in result
        assert "testuser" in result
        
        # 验证 Base64 编码的证书
        ca_b64 = base64.b64encode(ca_content).decode()
        p12_b64 = base64.b64encode(p12_content).decode()
        assert ca_b64 in result
        assert p12_b64 in result
    
    def test_create_mobileconfig_sanitizes_domain(self, mocker, temp_dir):
        """测试 create_mobileconfig 清理域名"""
        from nexus_vpn.protocols.ikev2 import IKEv2Manager
        from nexus_vpn.core.cert_mgr import CertManager
        
        pki_dir = os.path.join(temp_dir, "pki")
        os.makedirs(pki_dir, exist_ok=True)
        mocker.patch.object(CertManager, 'PKI_DIR', pki_dir)
        
        with open(os.path.join(pki_dir, "ca.crt"), 'wb') as f:
            f.write(b"CA")
        
        p12_path = os.path.join(temp_dir, "user.p12")
        with open(p12_path, 'wb') as f:
            f.write(b"P12")
        
        result = IKEv2Manager.create_mobileconfig("user", "example.com extra", p12_path)
        
        assert "example.com" in result
        assert "extra" not in result
