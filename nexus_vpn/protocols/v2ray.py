import json
import subprocess
import uuid
import os
import qrcode
from nexus_vpn.utils.logger import log

class V2RayManager:
    CONFIG_PATH = "/usr/local/etc/xray/config.json"
    
    @staticmethod
    def create_config(domain, reality_dest):
        log.info("生成 VLESS-Reality 配置...")
        out = subprocess.check_output(["/usr/local/bin/xray", "x25519"]).decode()
        priv_key = out.split('Private key:')[1].split('\n')[0].strip()
        pub_key = out.split('Public key:')[1].split('\n')[0].strip()
        uid = str(uuid.uuid4())
        short_id = subprocess.check_output(["openssl", "rand", "-hex", "4"]).decode().strip()
        
        config = {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "port": 443,
                "protocol": "vless",
                "settings": {
                    "clients": [{"id": uid, "flow": "xtls-rprx-vision", "email": "admin"}],
                    "decryption": "none"
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "dest": reality_dest,
                        "serverNames": [reality_dest.split(':')[0]],
                        "privateKey": priv_key,
                        "shortIds": [short_id]
                    }
                },
                "sniffing": {"enabled": True, "destOverride": ["http", "tls"]}
            }],
            "outbounds": [{"protocol": "freedom"}]
        }
        
        os.makedirs(os.path.dirname(V2RayManager.CONFIG_PATH), exist_ok=True)
        with open(V2RayManager.CONFIG_PATH, 'w') as f: json.dump(config, f, indent=4)
        subprocess.run("systemctl restart nexus-xray", shell=True)
        return {"uuid": uid, "public_key": pub_key, "short_id": short_id, "sni": reality_dest.split(':')[0], "port": 443}

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
        except: pass

    @staticmethod
    def add_user(username):
        with open(V2RayManager.CONFIG_PATH, 'r') as f: cfg = json.load(f)
        new_uid = str(uuid.uuid4())
        cfg['inbounds'][0]['settings']['clients'].append({"id": new_uid, "flow": "xtls-rprx-vision", "email": username})
        with open(V2RayManager.CONFIG_PATH, 'w') as f: json.dump(cfg, f, indent=4)
        subprocess.run("systemctl restart nexus-xray", shell=True)
        log.success(f"V2Ray 用户 {username} 已添加。")

    @staticmethod
    def remove_user(username):
        with open(V2RayManager.CONFIG_PATH, 'r') as f: cfg = json.load(f)
        clients = cfg['inbounds'][0]['settings']['clients']
        new_clients = [c for c in clients if c.get('email') != username]
        if len(clients) == len(new_clients): return
        cfg['inbounds'][0]['settings']['clients'] = new_clients
        with open(V2RayManager.CONFIG_PATH, 'w') as f: json.dump(cfg, f, indent=4)
        subprocess.run("systemctl restart nexus-xray", shell=True)
        log.success(f"V2Ray 用户 {username} 已删除。")
