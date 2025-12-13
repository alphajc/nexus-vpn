import os
import re
import secrets
import subprocess
import shutil
from nexus_vpn.utils.logger import log

class CertManager:
    PKI_DIR = "/etc/nexus-vpn/pki"
    P12_PASSWORD = os.environ.get("NEXUS_P12_PASSWORD", "nexusvpn")
    
    @staticmethod
    def _validate_name(name):
        """验证域名或用户名，防止命令注入"""
        if not name or not re.match(r'^[a-zA-Z0-9._-]+$', name):
            raise ValueError(f"无效的名称: {name}")
        return name

    @staticmethod
    def setup_ca(domain):
        domain = CertManager._validate_name(domain)
        if os.path.exists(f"{CertManager.PKI_DIR}/ca.crt"):
            return
        
        os.makedirs(f"{CertManager.PKI_DIR}/private", exist_ok=True)
        os.makedirs(f"{CertManager.PKI_DIR}/certs", exist_ok=True)
        
        log.info("生成 CA 与服务器证书...")
        
        ca_key = f"{CertManager.PKI_DIR}/private/ca.key"
        ca_crt = f"{CertManager.PKI_DIR}/ca.crt"
        server_key = f"{CertManager.PKI_DIR}/private/server.key"
        server_crt = f"{CertManager.PKI_DIR}/certs/server.crt"
        
        # CA Key
        with open(ca_key, "w") as f:
            subprocess.run(
                ["ipsec", "pki", "--gen", "--type", "rsa", "--size", "4096", "--outform", "pem"],
                stdout=f, check=True
            )
        
        # CA Cert
        with open(ca_key, "r") as key_in, open(ca_crt, "w") as crt_out:
            subprocess.run(
                ["ipsec", "pki", "--self", "--ca", "--lifetime", "3650",
                 "--in", "/dev/stdin", "--type", "rsa",
                 "--dn", "CN=NexusVPN Root CA", "--outform", "pem"],
                stdin=key_in, stdout=crt_out, check=True
            )
        
        # Server Key
        with open(server_key, "w") as f:
            subprocess.run(
                ["ipsec", "pki", "--gen", "--type", "rsa", "--size", "4096", "--outform", "pem"],
                stdout=f, check=True
            )
        
        # Server Cert (需要管道，使用两步)
        pub_key_proc = subprocess.run(
            ["ipsec", "pki", "--pub", "--in", server_key, "--type", "rsa"],
            capture_output=True, check=True
        )
        with open(server_crt, "w") as f:
            subprocess.run(
                ["ipsec", "pki", "--issue", "--lifetime", "3650",
                 "--cacert", ca_crt, "--cakey", ca_key,
                 "--dn", f"CN={domain}", f"--san={domain}",
                 "--flag", "serverAuth", "--flag", "ikeIntermediate", "--outform", "pem"],
                input=pub_key_proc.stdout, stdout=f, check=True
            )
        
        # Link to StrongSwan
        os.makedirs("/etc/ipsec.d/cacerts", exist_ok=True)
        os.makedirs("/etc/ipsec.d/certs", exist_ok=True)
        os.makedirs("/etc/ipsec.d/private", exist_ok=True)
        shutil.copy(ca_crt, "/etc/ipsec.d/cacerts/")
        shutil.copy(server_crt, "/etc/ipsec.d/certs/")
        shutil.copy(server_key, "/etc/ipsec.d/private/")

    @staticmethod
    def issue_user_cert(username):
        username = CertManager._validate_name(username)
        user_key = f"{CertManager.PKI_DIR}/private/{username}.key"
        user_crt = f"{CertManager.PKI_DIR}/certs/{username}.crt"
        p12_path = f"{CertManager.PKI_DIR}/certs/{username}.p12"
        ca_key = f"{CertManager.PKI_DIR}/private/ca.key"
        ca_crt = f"{CertManager.PKI_DIR}/ca.crt"
        
        # 强制清理旧文件
        for f in [user_key, user_crt, p12_path]:
            if os.path.exists(f):
                os.remove(f)
        
        # 1. 生成用户 Key
        with open(user_key, "w") as f:
            subprocess.run(
                ["ipsec", "pki", "--gen", "--type", "rsa", "--size", "2048", "--outform", "pem"],
                stdout=f, check=True
            )
        
        # 2. 生成用户 Cert
        pub_key_proc = subprocess.run(
            ["ipsec", "pki", "--pub", "--in", user_key, "--type", "rsa"],
            capture_output=True, check=True
        )
        with open(user_crt, "w") as f:
            subprocess.run(
                ["ipsec", "pki", "--issue", "--lifetime", "3650",
                 "--cacert", ca_crt, "--cakey", ca_key,
                 "--dn", f"CN={username}", f"--san={username}",
                 "--flag", "clientAuth", "--outform", "pem"],
                input=pub_key_proc.stdout, stdout=f, check=True
            )
        
        # 3. 导出 P12 (尝试 -legacy，失败则回退)
        p12_password = CertManager.P12_PASSWORD
        try:
            subprocess.run(
                ["openssl", "pkcs12", "-export", "-legacy",
                 "-inkey", user_key, "-in", user_crt,
                 "-name", username, "-certfile", ca_crt,
                 "-caname", "NexusVPN Root CA",
                 "-out", p12_path, "-passout", f"pass:{p12_password}"],
                check=True, stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError:
            # 回退到兼容模式
            subprocess.run(
                ["openssl", "pkcs12", "-export",
                 "-keypbe", "PBE-SHA1-3DES", "-certpbe", "PBE-SHA1-3DES", "-macalg", "sha1",
                 "-inkey", user_key, "-in", user_crt,
                 "-name", username, "-certfile", ca_crt,
                 "-out", p12_path, "-passout", f"pass:{p12_password}"],
                check=True
            )

        return p12_path

    @staticmethod
    def get_ca_content():
        with open(f"{CertManager.PKI_DIR}/ca.crt", "rb") as f:
            return f.read()
