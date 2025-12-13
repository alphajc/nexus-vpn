import os
import re
import secrets
import subprocess
import shutil
import tempfile
from nexus_vpn.utils.logger import log
from nexus_vpn.utils.sudo import sudo_run, sudo_write_file, sudo_read_file, sudo_makedirs, sudo_move, sudo_remove, need_sudo

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
        
        sudo_makedirs(f"{CertManager.PKI_DIR}/private")
        sudo_makedirs(f"{CertManager.PKI_DIR}/certs")
        
        log.info("生成 CA 与服务器证书...")
        
        ca_key = f"{CertManager.PKI_DIR}/private/ca.key"
        ca_crt = f"{CertManager.PKI_DIR}/ca.crt"
        server_key = f"{CertManager.PKI_DIR}/private/server.key"
        server_crt = f"{CertManager.PKI_DIR}/certs/server.crt"
        
        # 使用临时目录生成证书，然后移动到目标位置
        with tempfile.TemporaryDirectory() as tmp:
            tmp_ca_key = os.path.join(tmp, "ca.key")
            tmp_ca_crt = os.path.join(tmp, "ca.crt")
            tmp_server_key = os.path.join(tmp, "server.key")
            tmp_server_crt = os.path.join(tmp, "server.crt")
            
            # CA Key
            with open(tmp_ca_key, "w") as f:
                subprocess.run(
                    ["ipsec", "pki", "--gen", "--type", "rsa", "--size", "4096", "--outform", "pem"],
                    stdout=f, check=True
                )
            
            # CA Cert
            with open(tmp_ca_key, "r") as key_in, open(tmp_ca_crt, "w") as crt_out:
                subprocess.run(
                    ["ipsec", "pki", "--self", "--ca", "--lifetime", "3650",
                     "--in", "/dev/stdin", "--type", "rsa",
                     "--dn", "CN=NexusVPN Root CA", "--outform", "pem"],
                    stdin=key_in, stdout=crt_out, check=True
                )
            
            # Server Key
            with open(tmp_server_key, "w") as f:
                subprocess.run(
                    ["ipsec", "pki", "--gen", "--type", "rsa", "--size", "4096", "--outform", "pem"],
                    stdout=f, check=True
                )
            
            # Server Cert
            pub_key_proc = subprocess.run(
                ["ipsec", "pki", "--pub", "--in", tmp_server_key, "--type", "rsa"],
                capture_output=True, check=True
            )
            with open(tmp_server_crt, "w") as f:
                subprocess.run(
                    ["ipsec", "pki", "--issue", "--lifetime", "3650",
                     "--cacert", tmp_ca_crt, "--cakey", tmp_ca_key,
                     "--dn", f"CN={domain}", f"--san={domain}",
                     "--flag", "serverAuth", "--flag", "ikeIntermediate", "--outform", "pem"],
                    input=pub_key_proc.stdout, stdout=f, check=True
                )
            
            # 移动到目标位置
            sudo_move(tmp_ca_key, ca_key)
            sudo_move(tmp_ca_crt, ca_crt)
            sudo_move(tmp_server_key, server_key)
            sudo_move(tmp_server_crt, server_crt)
        
        # Link to StrongSwan
        sudo_makedirs("/etc/ipsec.d/cacerts")
        sudo_makedirs("/etc/ipsec.d/certs")
        sudo_makedirs("/etc/ipsec.d/private")
        
        if need_sudo() and shutil.which("sudo"):
            subprocess.run(["sudo", "cp", ca_crt, "/etc/ipsec.d/cacerts/"], check=True)
            subprocess.run(["sudo", "cp", server_crt, "/etc/ipsec.d/certs/"], check=True)
            subprocess.run(["sudo", "cp", server_key, "/etc/ipsec.d/private/"], check=True)
        else:
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
            sudo_remove(f)
        
        # 使用临时目录生成证书
        with tempfile.TemporaryDirectory() as tmp:
            tmp_user_key = os.path.join(tmp, f"{username}.key")
            tmp_user_crt = os.path.join(tmp, f"{username}.crt")
            tmp_p12 = os.path.join(tmp, f"{username}.p12")
            
            # 读取 CA 文件到临时目录（用于 openssl 命令）
            tmp_ca_key = os.path.join(tmp, "ca.key")
            tmp_ca_crt = os.path.join(tmp, "ca.crt")
            
            ca_key_content = sudo_read_file(ca_key)
            ca_crt_content = sudo_read_file(ca_crt)
            with open(tmp_ca_key, "w") as f:
                f.write(ca_key_content)
            with open(tmp_ca_crt, "w") as f:
                f.write(ca_crt_content)
            
            # 1. 生成用户 Key
            with open(tmp_user_key, "w") as f:
                subprocess.run(
                    ["ipsec", "pki", "--gen", "--type", "rsa", "--size", "2048", "--outform", "pem"],
                    stdout=f, check=True
                )
            
            # 2. 生成用户 Cert
            pub_key_proc = subprocess.run(
                ["ipsec", "pki", "--pub", "--in", tmp_user_key, "--type", "rsa"],
                capture_output=True, check=True
            )
            with open(tmp_user_crt, "w") as f:
                subprocess.run(
                    ["ipsec", "pki", "--issue", "--lifetime", "3650",
                     "--cacert", tmp_ca_crt, "--cakey", tmp_ca_key,
                     "--dn", f"CN={username}", f"--san={username}",
                     "--flag", "clientAuth", "--outform", "pem"],
                    input=pub_key_proc.stdout, stdout=f, check=True
                )
            
            # 3. 导出 P12 (尝试 -legacy，失败则回退)
            p12_password = CertManager.P12_PASSWORD
            try:
                subprocess.run(
                    ["openssl", "pkcs12", "-export", "-legacy",
                     "-inkey", tmp_user_key, "-in", tmp_user_crt,
                     "-name", username, "-certfile", tmp_ca_crt,
                     "-caname", "NexusVPN Root CA",
                     "-out", tmp_p12, "-passout", f"pass:{p12_password}"],
                    check=True, stderr=subprocess.DEVNULL
                )
            except subprocess.CalledProcessError:
                # 回退到兼容模式
                subprocess.run(
                    ["openssl", "pkcs12", "-export",
                     "-keypbe", "PBE-SHA1-3DES", "-certpbe", "PBE-SHA1-3DES", "-macalg", "sha1",
                     "-inkey", tmp_user_key, "-in", tmp_user_crt,
                     "-name", username, "-certfile", tmp_ca_crt,
                     "-out", tmp_p12, "-passout", f"pass:{p12_password}"],
                    check=True
                )
            
            # 移动到目标位置
            sudo_move(tmp_user_key, user_key)
            sudo_move(tmp_user_crt, user_crt)
            sudo_move(tmp_p12, p12_path)

        return p12_path

    @staticmethod
    def get_ca_content():
        content = sudo_read_file(f"{CertManager.PKI_DIR}/ca.crt")
        return content.encode() if isinstance(content, str) else content
