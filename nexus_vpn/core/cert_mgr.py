import os
import subprocess
from nexus_vpn.utils.logger import log

class CertManager:
    PKI_DIR = "/etc/nexus-vpn/pki"
    
    @staticmethod
    def run_pki(cmd):
        subprocess.check_call(f"ipsec pki {cmd}", shell=True, stderr=subprocess.DEVNULL)

    @staticmethod
    def setup_ca(domain):
        if os.path.exists(f"{CertManager.PKI_DIR}/ca.crt"): return
        
        os.makedirs(f"{CertManager.PKI_DIR}/private", exist_ok=True)
        os.makedirs(f"{CertManager.PKI_DIR}/certs", exist_ok=True)
        
        log.info("生成 CA 与服务器证书...")
        # CA
        CertManager.run_pki(f"--gen --type rsa --size 4096 --outform pem > {CertManager.PKI_DIR}/private/ca.key")
        CertManager.run_pki(f"--self --ca --lifetime 3650 --in {CertManager.PKI_DIR}/private/ca.key --type rsa --dn \"CN=NexusVPN Root CA\" --outform pem > {CertManager.PKI_DIR}/ca.crt")
        
        # Server
        CertManager.run_pki(f"--gen --type rsa --size 4096 --outform pem > {CertManager.PKI_DIR}/private/server.key")
        CertManager.run_pki(f"--pub --in {CertManager.PKI_DIR}/private/server.key --type rsa | ipsec pki --issue --lifetime 3650 --cacert {CertManager.PKI_DIR}/ca.crt --cakey {CertManager.PKI_DIR}/private/ca.key --dn \"CN={domain}\" --san=\"{domain}\" --flag serverAuth --flag ikeIntermediate --outform pem > {CertManager.PKI_DIR}/certs/server.crt")
        
        # Link to StrongSwan
        subprocess.run(f"cp {CertManager.PKI_DIR}/ca.crt /etc/ipsec.d/cacerts/", shell=True)
        subprocess.run(f"cp {CertManager.PKI_DIR}/certs/server.crt /etc/ipsec.d/certs/", shell=True)
        subprocess.run(f"cp {CertManager.PKI_DIR}/private/server.key /etc/ipsec.d/private/", shell=True)

    @staticmethod
    def issue_user_cert(username):
        user_key = f"{CertManager.PKI_DIR}/private/{username}.key"
        user_crt = f"{CertManager.PKI_DIR}/certs/{username}.crt"
        p12_path = f"{CertManager.PKI_DIR}/certs/{username}.p12"
        
        # 强制清理旧文件，确保生成新的
        if os.path.exists(user_key): os.remove(user_key)
        if os.path.exists(user_crt): os.remove(user_crt)
        if os.path.exists(p12_path): os.remove(p12_path)
        
        # 1. 生成 Key 和 Cert (ClientAuth)
        CertManager.run_pki(f"--gen --type rsa --size 2048 --outform pem > {user_key}")
        CertManager.run_pki(f"--pub --in {user_key} --type rsa | ipsec pki --issue --lifetime 3650 --cacert {CertManager.PKI_DIR}/ca.crt --cakey {CertManager.PKI_DIR}/private/ca.key --dn \"CN={username}\" --san=\"{username}\" --flag clientAuth --outform pem > {user_crt}")
        
        # 2. 导出 P12 (关键修复: 尝试使用 -legacy，如果失败则回退到默认)
        # OpenSSL 3 需要 -legacy 才能让 macOS 识别 P12
        # -passout pass:nexusvpn 固定密码，防止安装时弹窗问密码
        cmd = f"openssl pkcs12 -export -legacy -inkey {user_key} -in {user_crt} -name \"{username}\" -certfile {CertManager.PKI_DIR}/ca.crt -caname \"NexusVPN Root CA\" -out {p12_path} -passout pass:nexusvpn 2>/dev/null || openssl pkcs12 -export -inkey {user_key} -in {user_crt} -name \"{username}\" -certfile {CertManager.PKI_DIR}/ca.crt -caname \"NexusVPN Root CA\" -out {p12_path} -passout pass:nexusvpn"
        
        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError:
            # 如果 -legacy 也不行，尝试指定具体算法 (兼容更老的 OpenSSL)
            cmd_fallback = f"openssl pkcs12 -export -keypbe PBE-SHA1-3DES -certpbe PBE-SHA1-3DES -macalg sha1 -inkey {user_key} -in {user_crt} -name \"{username}\" -certfile {CertManager.PKI_DIR}/ca.crt -out {p12_path} -passout pass:nexusvpn"
            subprocess.check_call(cmd_fallback, shell=True)

        return p12_path

    @staticmethod
    def get_ca_content():
        with open(f"{CertManager.PKI_DIR}/ca.crt", "rb") as f: return f.read()
