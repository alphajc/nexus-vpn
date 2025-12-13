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
        
        result = V2RayManager.create_config("example.com", "www.microsoft.com:443", preserve_users=False)
        
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
        """测试 create_config 调用 sudo_run 重启服务"""
        from nexus_vpn.protocols.v2ray import V2RayManager
        
        config_path = os.path.join(temp_dir, "xray", "config.json")
        mocker.patch.object(V2RayManager, 'CONFIG_PATH', config_path)
        
        mock_check_output = mocker.patch('subprocess.check_output')
        mock_check_output.side_effect = [
            b"Private key: priv\nPublic key: pub\n",
            b"1234\n"
        ]
        
        # 直接 mock sudo_run 并验证调用
        mock_sudo_run = mocker.patch('nexus_vpn.protocols.v2ray.sudo_run')
        
        V2RayManager.create_config("example.com", "www.example.com:443", preserve_users=False)
        
        # 验证 sudo_run 被调用来重启服务
        mock_sudo_run.assert_called_with(["systemctl", "restart", "nexus-xray"], check=True)
    
    def test_add_user(self, mocker, mock_xray_config):
        """测试 add_user 添加用户"""
        from nexus_vpn.protocols.v2ray import V2RayManager
        
        mocker.patch.object(V2RayManager, 'CONFIG_PATH', mock_xray_config)
        mock_sudo_run = mocker.patch('nexus_vpn.protocols.v2ray.sudo_run')
        mocker.patch('uuid.uuid4', return_value=MagicMock(__str__=lambda x: "new-user-uuid"))
        
        V2RayManager.add_user("newuser")
        
        with open(mock_xray_config, 'r') as f:
            config = json.load(f)
        
        clients = config['inbounds'][0]['settings']['clients']
        emails = [c.get('email') for c in clients]
        
        assert "newuser" in emails
        mock_sudo_run.assert_called_with(["systemctl", "restart", "nexus-xray"], check=True)
    
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
        mock_sudo_run = mocker.patch('nexus_vpn.protocols.v2ray.sudo_run')
        
        V2RayManager.remove_user("testuser")
        
        with open(mock_xray_config, 'r') as f:
            config = json.load(f)
        
        clients = config['inbounds'][0]['settings']['clients']
        emails = [c.get('email') for c in clients]
        
        assert "testuser" not in emails
        assert "admin" in emails  # 其他用户应保留
        mock_sudo_run.assert_called_with(["systemctl", "restart", "nexus-xray"], check=True)
    
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

    def test_create_config_multiple_reality_dests(self, mocker, temp_dir):
        """测试 create_config 支持多个 reality_dests"""
        from nexus_vpn.protocols.v2ray import V2RayManager
        
        config_path = os.path.join(temp_dir, "xray", "config.json")
        mocker.patch.object(V2RayManager, 'CONFIG_PATH', config_path)
        
        mock_check_output = mocker.patch('subprocess.check_output')
        mock_check_output.side_effect = [
            b"Private key: priv_key\nPublic key: pub_key\n",
            b"1234\n"
        ]
        
        mocker.patch('subprocess.run')
        mocker.patch('uuid.uuid4', return_value=MagicMock(__str__=lambda x: "test-uuid"))
        
        dests = ["www.microsoft.com:443", "www.apple.com:443", "www.google.com:443"]
        result = V2RayManager.create_config("example.com", dests, preserve_users=False)
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        reality_settings = config['inbounds'][0]['streamSettings']['realitySettings']
        
        # 验证 dest 是第一个目标
        assert reality_settings['dest'] == "www.microsoft.com:443"
        
        # 验证 serverNames 包含所有域名
        assert reality_settings['serverNames'] == ["www.microsoft.com", "www.apple.com", "www.google.com"]
        
        # 验证返回值
        assert result['sni'] == "www.microsoft.com"

    def test_create_config_preserves_users(self, mocker, mock_xray_config):
        """测试 create_config 保留现有用户"""
        from nexus_vpn.protocols.v2ray import V2RayManager
        
        mocker.patch.object(V2RayManager, 'CONFIG_PATH', mock_xray_config)
        
        # 读取原始用户
        with open(mock_xray_config, 'r') as f:
            original_config = json.load(f)
        original_clients = original_config['inbounds'][0]['settings']['clients']
        original_private_key = original_config['inbounds'][0]['streamSettings']['realitySettings']['privateKey']
        
        mock_check_output = mocker.patch('subprocess.check_output')
        # 模拟从私钥推导公钥
        mock_check_output.return_value = b"Public key: derived_pub_key\n"
        
        mocker.patch('subprocess.run')
        
        # 使用新的 reality_dests 重新生成配置
        result = V2RayManager.create_config("example.com", "www.apple.com:443", preserve_users=True)
        
        with open(mock_xray_config, 'r') as f:
            new_config = json.load(f)
        
        new_clients = new_config['inbounds'][0]['settings']['clients']
        new_private_key = new_config['inbounds'][0]['streamSettings']['realitySettings']['privateKey']
        
        # 验证用户被保留
        assert len(new_clients) == len(original_clients)
        for orig in original_clients:
            assert any(c['email'] == orig['email'] for c in new_clients)
        
        # 验证私钥被保留
        assert new_private_key == original_private_key
        
        # 验证 reality_dests 已更新
        assert new_config['inbounds'][0]['streamSettings']['realitySettings']['dest'] == "www.apple.com:443"

    def test_create_config_no_preserve_users(self, mocker, mock_xray_config):
        """测试 create_config 不保留用户时重新生成"""
        from nexus_vpn.protocols.v2ray import V2RayManager
        
        mocker.patch.object(V2RayManager, 'CONFIG_PATH', mock_xray_config)
        
        mock_check_output = mocker.patch('subprocess.check_output')
        mock_check_output.side_effect = [
            b"Private key: new_priv_key\nPublic key: new_pub_key\n",
            b"5678\n"
        ]
        
        mocker.patch('subprocess.run')
        mocker.patch('uuid.uuid4', return_value=MagicMock(__str__=lambda x: "new-admin-uuid"))
        
        result = V2RayManager.create_config("example.com", "www.apple.com:443", preserve_users=False)
        
        with open(mock_xray_config, 'r') as f:
            new_config = json.load(f)
        
        new_clients = new_config['inbounds'][0]['settings']['clients']
        
        # 验证只有一个 admin 用户
        assert len(new_clients) == 1
        assert new_clients[0]['email'] == 'admin'
        
        # 验证使用新的密钥
        assert new_config['inbounds'][0]['streamSettings']['realitySettings']['privateKey'] == 'new_priv_key'

    def test_create_config_single_dest_string(self, mocker, temp_dir):
        """测试 create_config 接受单个字符串 reality_dest"""
        from nexus_vpn.protocols.v2ray import V2RayManager
        
        config_path = os.path.join(temp_dir, "xray", "config.json")
        mocker.patch.object(V2RayManager, 'CONFIG_PATH', config_path)
        
        mock_check_output = mocker.patch('subprocess.check_output')
        mock_check_output.side_effect = [
            b"Private key: priv\nPublic key: pub\n",
            b"1234\n"
        ]
        
        mocker.patch('subprocess.run')
        mocker.patch('uuid.uuid4', return_value=MagicMock(__str__=lambda x: "uuid"))
        
        # 传入单个字符串而非列表
        result = V2RayManager.create_config("example.com", "www.example.com:443", preserve_users=False)
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        assert config['inbounds'][0]['streamSettings']['realitySettings']['dest'] == "www.example.com:443"
        assert config['inbounds'][0]['streamSettings']['realitySettings']['serverNames'] == ["www.example.com"]
