"""Pytest 配置和共享 fixtures"""
import os
import sys
import pytest
import tempfile
import json

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_dir():
    """创建临时目录用于测试"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_pki_dir(temp_dir, monkeypatch):
    """模拟 PKI 目录"""
    pki_dir = os.path.join(temp_dir, "pki")
    os.makedirs(os.path.join(pki_dir, "private"), exist_ok=True)
    os.makedirs(os.path.join(pki_dir, "certs"), exist_ok=True)
    monkeypatch.setattr("nexus_vpn.core.cert_mgr.CertManager.PKI_DIR", pki_dir)
    return pki_dir


@pytest.fixture
def mock_xray_config(temp_dir):
    """模拟 Xray 配置文件"""
    config_path = os.path.join(temp_dir, "xray", "config.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "port": 443,
            "protocol": "vless",
            "settings": {
                "clients": [
                    {"id": "test-uuid-1", "flow": "xtls-rprx-vision", "email": "admin"},
                    {"id": "test-uuid-2", "flow": "xtls-rprx-vision", "email": "testuser"}
                ],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "dest": "www.microsoft.com:443",
                    "serverNames": ["www.microsoft.com"],
                    "privateKey": "test-private-key",
                    "shortIds": ["abcd1234"]
                }
            }
        }],
        "outbounds": [{"protocol": "freedom"}]
    }
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    
    return config_path


@pytest.fixture
def mock_ipsec_secrets(temp_dir):
    """模拟 ipsec.secrets 文件"""
    secrets_path = os.path.join(temp_dir, "ipsec.secrets")
    content = """: RSA server.key
testuser1 : EAP "password1"
testuser2 : EAP "password2"
"""
    with open(secrets_path, 'w') as f:
        f.write(content)
    return secrets_path


@pytest.fixture
def mock_ipsec_conf(temp_dir):
    """模拟 ipsec.conf 文件"""
    conf_path = os.path.join(temp_dir, "ipsec.conf")
    content = """config setup
    charondebug="ike 1, knl 1, cfg 0"

conn IKEv2-Cert
    leftid=@test.example.com
    auto=add
"""
    with open(conf_path, 'w') as f:
        f.write(content)
    return conf_path


@pytest.fixture
def mock_subprocess_run(mocker):
    """Mock subprocess.run 用于避免实际执行系统命令"""
    mock = mocker.patch('subprocess.run')
    mock.return_value.returncode = 0
    mock.return_value.stdout = ""
    mock.return_value.stderr = ""
    return mock


@pytest.fixture
def mock_subprocess_check_output(mocker):
    """Mock subprocess.check_output"""
    return mocker.patch('subprocess.check_output')


@pytest.fixture(autouse=True)
def mock_sudo_helpers(mocker, temp_dir):
    """自动 mock sudo helpers，使其直接操作本地文件（不执行系统命令）"""
    from unittest.mock import MagicMock
    
    # Mock need_sudo 返回 False（不需要 sudo）
    mocker.patch('nexus_vpn.utils.sudo.need_sudo', return_value=False)
    
    # 让 sudo_run 返回一个 mock 对象（不执行实际命令）
    mock_run_result = MagicMock()
    mock_run_result.returncode = 0
    mock_run_result.stdout = ""
    mock_run_result.stderr = ""
    mocker.patch('nexus_vpn.utils.sudo.sudo_run', return_value=mock_run_result)
    
    # sudo_write_file 直接写入文件
    def mock_sudo_write_file(path, content, mode='w'):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, mode) as f:
            f.write(content)
    
    mocker.patch('nexus_vpn.utils.sudo.sudo_write_file', side_effect=mock_sudo_write_file)
    
    # sudo_read_file 直接读取文件
    def mock_sudo_read_file(path):
        with open(path, 'r') as f:
            return f.read()
    
    mocker.patch('nexus_vpn.utils.sudo.sudo_read_file', side_effect=mock_sudo_read_file)
    
    # sudo_makedirs 直接创建目录
    def mock_sudo_makedirs(path, mode=0o755):
        os.makedirs(path, exist_ok=True)
    
    mocker.patch('nexus_vpn.utils.sudo.sudo_makedirs', side_effect=mock_sudo_makedirs)
    
    # sudo_chmod 直接修改权限
    def mock_sudo_chmod(path, mode):
        os.chmod(path, mode)
    
    mocker.patch('nexus_vpn.utils.sudo.sudo_chmod', side_effect=mock_sudo_chmod)
    
    # sudo_move 直接移动文件
    import shutil
    def mock_sudo_move(src, dst):
        shutil.move(src, dst)
    
    mocker.patch('nexus_vpn.utils.sudo.sudo_move', side_effect=mock_sudo_move)
    
    # sudo_remove 直接删除
    def mock_sudo_remove(path):
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.exists(path):
            os.remove(path)
    
    mocker.patch('nexus_vpn.utils.sudo.sudo_remove', side_effect=mock_sudo_remove)
