"""测试 nexus_vpn.protocols.v2ray 模块"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock


class TestV2RayManager:
    """V2RayManager 类测试"""
    
    def test_v2ray_manager_import(self):
        """测试 V2RayManager 可以正常导入"""
        from nexus_vpn.protocols.v2ray import V2RayManager
        assert V2RayManager is not None
    
    def test_config_path_constant(self):
        """测试 CONFIG_PATH 常量"""
        from nexus_vpn.protocols.v2ray import V2RayManager
        assert V2RayManager.CONFIG_PATH == "/usr/local/etc/xray/config.json"
    
    def test_create_config_generates_valid_json(self, mocker, temp_dir):
        """测试 create_config 生成有效的 JSON 配置"""
        from nexus_vpn.protocols.v2ray import V2RayManager
        
        config_path = os.path.join(temp_dir, "xray", "config.json")
        mocker.patch.object(V2RayManager, 'CONFIG_PATH', config_path)
        
        # Mock xray x25519 命令
        mock_check_output = mocker.patch('subprocess.check_output')
        mock_check_output.side_effect = [
            b"Private key: test_private_key_123\nPublic key: test_public_key_456\n",
            b"abcd1234\n"  # short_id
        ]
        
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(returncode=0)
        
        # Mock uuid
        mocker.patch('uuid.uuid4', return_value=MagicMock(__str__=lambda x: "test-uuid-12345"))
        
        result = V2RayManager.create_config("example.com", "www.microsoft.com:443")
        
        # 验证返回值
        assert "uuid" in result
        assert "public_key" in result
        assert "short_id" in result
        assert "sni" in result
        assert "port" in result
        assert result["port"] == 443
        assert result["sni"] == "www.microsoft.com"
        
        # 验证配置文件
        assert os.path.exists(config_path)
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        assert "inbounds" in config
        assert "outbounds" in config
        assert config["inbounds"][0]["port"] == 443
        assert config["inbounds"][0]["protocol"] == "vless"
    
    def test_create_config_restarts_service(self, mocker, temp_dir):
        """测试 create_config 重启服务"""
        from nexus_vpn.protocols.v2ray import V2RayManager
        
        config_path = os.path.join(temp_dir, "xray", "config.json")
        mocker.patch.object(V2RayManager, 'CONFIG_PATH', config_path)
        
        mock_check_output = mocker.patch('subprocess.check_output')
        mock_check_output.side_effect = [
            b"Private key: priv\nPublic key: pub\n",
            b"1234\n"
        ]
        
        mock_run = mocker.patch('subprocess.run')
        
        V2RayManager.create_config("example.com", "www.example.com:443")
        
        # 验证 systemctl restart 被调用
        mock_run.assert_called_with(["systemctl", "restart", "nexus-xray"], check=True)
    
    def test_add_user(self, mocker, mock_xray_config):
        """测试 add_user 添加用户"""
        from nexus_vpn.protocols.v2ray import V2RayManager
        
        mocker.patch.object(V2RayManager, 'CONFIG_PATH', mock_xray_config)
        mock_run = mocker.patch('subprocess.run')
        mocker.patch('uuid.uuid4', return_value=MagicMock(__str__=lambda x: "new-user-uuid"))
        
        V2RayManager.add_user("newuser")
        
        with open(mock_xray_config, 'r') as f:
            config = json.load(f)
        
        clients = config['inbounds'][0]['settings']['clients']
        emails = [c.get('email') for c in clients]
        
        assert "newuser" in emails
        mock_run.assert_called_with(["systemctl", "restart", "nexus-xray"], check=True)
    
    def test_add_user_preserves_existing(self, mocker, mock_xray_config):
        """测试 add_user 保留现有用户"""
        from nexus_vpn.protocols.v2ray import V2RayManager
        
        mocker.patch.object(V2RayManager, 'CONFIG_PATH', mock_xray_config)
        mocker.patch('subprocess.run')
        mocker.patch('uuid.uuid4', return_value=MagicMock(__str__=lambda x: "new-uuid"))
        
        # 读取原始用户
        with open(mock_xray_config, 'r') as f:
            original_clients = json.load(f)['inbounds'][0]['settings']['clients']
        
        V2RayManager.add_user("brandnewuser")
        
        with open(mock_xray_config, 'r') as f:
            new_clients = json.load(f)['inbounds'][0]['settings']['clients']
        
        # 验证原始用户仍存在
        for orig in original_clients:
            assert any(c.get('email') == orig.get('email') for c in new_clients)
        
        # 验证新用户已添加
        assert any(c.get('email') == 'brandnewuser' for c in new_clients)
    
    def test_remove_user(self, mocker, mock_xray_config):
        """测试 remove_user 删除用户"""
        from nexus_vpn.protocols.v2ray import V2RayManager
        
        mocker.patch.object(V2RayManager, 'CONFIG_PATH', mock_xray_config)
        mock_run = mocker.patch('subprocess.run')
        
        V2RayManager.remove_user("testuser")
        
        with open(mock_xray_config, 'r') as f:
            config = json.load(f)
        
        clients = config['inbounds'][0]['settings']['clients']
        emails = [c.get('email') for c in clients]
        
        assert "testuser" not in emails
        assert "admin" in emails  # 其他用户应保留
        mock_run.assert_called_with(["systemctl", "restart", "nexus-xray"], check=True)
    
    def test_remove_user_not_found(self, mocker, mock_xray_config):
        """测试 remove_user 用户不存在时"""
        from nexus_vpn.protocols.v2ray import V2RayManager
        
        mocker.patch.object(V2RayManager, 'CONFIG_PATH', mock_xray_config)
        mock_run = mocker.patch('subprocess.run')
        
        # 读取原始配置
        with open(mock_xray_config, 'r') as f:
            original = f.read()
        
        V2RayManager.remove_user("nonexistentuser")
        
        # 配置应该保持不变（不调用 restart）
        mock_run.assert_not_called()
    
    def test_print_connection_info(self, mocker, capsys):
        """测试 print_connection_info 输出连接信息"""
        from nexus_vpn.protocols.v2ray import V2RayManager
        
        # Mock qrcode
        mock_qr = MagicMock()
        mocker.patch('qrcode.QRCode', return_value=mock_qr)
        
        info = {
            "uuid": "test-uuid",
            "public_key": "test-pubkey",
            "short_id": "1234",
            "sni": "www.example.com",
            "port": 443
        }
        
        V2RayManager.print_connection_info("example.com", info)
        
        captured = capsys.readouterr()
        assert "vless://" in captured.out
        assert "test-uuid" in captured.out
        assert "example.com" in captured.out
        assert "test-pubkey" in captured.out
    
    def test_print_connection_info_qrcode_error(self, mocker, capsys):
        """测试 print_connection_info 二维码生成失败时不抛异常"""
        from nexus_vpn.protocols.v2ray import V2RayManager
        
        # Mock qrcode 抛出异常
        mocker.patch('qrcode.QRCode', side_effect=Exception("QR Error"))
        
        info = {
            "uuid": "test-uuid",
            "public_key": "test-pubkey",
            "short_id": "1234",
            "sni": "www.example.com",
            "port": 443
        }
        
        # 不应该抛出异常
        V2RayManager.print_connection_info("example.com", info)
        
        captured = capsys.readouterr()
        assert "vless://" in captured.out
