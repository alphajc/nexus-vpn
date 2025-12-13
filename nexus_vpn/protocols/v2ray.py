import json
import subprocess
import uuid
import os
import qrcode
from nexus_vpn.utils.logger import log
from nexus_vpn.utils.sudo import sudo_run, sudo_write_file, sudo_read_file, sudo_makedirs

class V2RayManager:
    CONFIG_PATH = "/usr/local/etc/xray/config.json"
    
    @staticmethod
    def create_config(domain, reality_dests, preserve_users=True):
        """生成 VLESS-Reality 配置
        
        Args:
            domain: 服务器域名/IP
            reality_dests: Reality 目标，可以是单个字符串或字符串列表
            preserve_users: 是否保留现有用户（默认 True）
        """
        log.info("生成 VLESS-Reality 配置...")
        
        # 兼容单个字符串和列表
        if isinstance(reality_dests, str):
            reality_dests = [reality_dests]
        
        # 第一个作为主 dest，所有域名作为 serverNames
        primary_dest = reality_dests[0]
        server_names = [dest.split(':')[0] for dest in reality_dests]
        
        # 尝试保留现有配置中的用户和密钥
        existing_clients = None
        existing_keys = None
        if preserve_users and os.path.exists(V2RayManager.CONFIG_PATH):
            try:
                old_cfg_content = sudo_read_file(V2RayManager.CONFIG_PATH)
                old_cfg = json.loads(old_cfg_content)
                existing_clients = old_cfg.get('inbounds', [{}])[0].get('settings', {}).get('clients', [])
                reality_settings = old_cfg.get('inbounds', [{}])[0].get('streamSettings', {}).get('realitySettings', {})
                if reality_settings.get('privateKey'):
                    existing_keys = {
                        'privateKey': reality_settings['privateKey'],
                        'shortIds': reality_settings.get('shortIds', [])
                    }
                if existing_clients:
                    log.info(f"保留 {len(existing_clients)} 个现有用户")
            except Exception:
                pass
        
        # 生成新密钥或使用现有密钥
        if existing_keys:
            priv_key = existing_keys['privateKey']
            short_id = existing_keys['shortIds'][0] if existing_keys['shortIds'] else subprocess.check_output(["openssl", "rand", "-hex", "4"]).decode().strip()
            # 从私钥推导公钥
            out = subprocess.check_output(["/usr/local/bin/xray", "x25519", "-i", priv_key]).decode()
            pub_key = out.split('Public key:')[1].split('\n')[0].strip()
        else:
            out = subprocess.check_output(["/usr/local/bin/xray", "x25519"]).decode()
            priv_key = out.split('Private key:')[1].split('\n')[0].strip()
            pub_key = out.split('Public key:')[1].split('\n')[0].strip()
            short_id = subprocess.check_output(["openssl", "rand", "-hex", "4"]).decode().strip()
        
        # 使用现有用户或创建默认 admin 用户
        if existing_clients:
            clients = existing_clients
            uid = clients[0]['id']  # 返回第一个用户的 UUID
        else:
            uid = str(uuid.uuid4())
            clients = [{"id": uid, "flow": "xtls-rprx-vision", "email": "admin"}]
        
        config = {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "port": 443,
                "protocol": "vless",
                "settings": {
                    "clients": clients,
                    "decryption": "none"
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "dest": primary_dest,
                        "serverNames": server_names,
                        "privateKey": priv_key,
                        "shortIds": [short_id]
                    }
                },
                "sniffing": {"enabled": True, "destOverride": ["http", "tls"]}
            }],
            "outbounds": [{"protocol": "freedom"}]
        }
        
        sudo_makedirs(os.path.dirname(V2RayManager.CONFIG_PATH))
        sudo_write_file(V2RayManager.CONFIG_PATH, json.dumps(config, indent=4))
        sudo_run(["systemctl", "restart", "nexus-xray"], check=True)
        return {"uuid": uid, "public_key": pub_key, "short_id": short_id, "sni": server_names[0], "port": 443}

    @staticmethod
    def print_connection_info(domain, info):
        link = (f"vless://{info['uuid']}@{domain}:{info['port']}"
                f"?security=reality&sni={info['sni']}&fp=chrome"
                f"&pbk={info['public_key']}&sid={info['short_id']}"
                f"&type=tcp&flow=xtls-rprx-vision#NexusVPN")
        log.success("V2Ray 部署成功!")
        print(f"\nURL: {link}\n")
        try:
            qr = qrcode.QRCode(border=1)
            qr.add_data(link)
            qr.print_ascii(invert=True)
        except Exception:
            pass

    @staticmethod
    def add_user(username):
        cfg_content = sudo_read_file(V2RayManager.CONFIG_PATH)
        cfg = json.loads(cfg_content)
        new_uid = str(uuid.uuid4())
        cfg['inbounds'][0]['settings']['clients'].append(
            {"id": new_uid, "flow": "xtls-rprx-vision", "email": username}
        )
        sudo_write_file(V2RayManager.CONFIG_PATH, json.dumps(cfg, indent=4))
        sudo_run(["systemctl", "restart", "nexus-xray"], check=True)
        log.success(f"V2Ray 用户 {username} 已添加。")

    @staticmethod
    def remove_user(username):
        cfg_content = sudo_read_file(V2RayManager.CONFIG_PATH)
        cfg = json.loads(cfg_content)
        clients = cfg['inbounds'][0]['settings']['clients']
        new_clients = [c for c in clients if c.get('email') != username]
        if len(clients) == len(new_clients):
            return
        cfg['inbounds'][0]['settings']['clients'] = new_clients
        sudo_write_file(V2RayManager.CONFIG_PATH, json.dumps(cfg, indent=4))
        sudo_run(["systemctl", "restart", "nexus-xray"], check=True)
        log.success(f"V2Ray 用户 {username} 已删除。")
