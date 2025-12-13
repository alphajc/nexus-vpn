import os
import base64
import subprocess
from nexus_vpn.core.cert_mgr import CertManager
from nexus_vpn.utils.logger import log
from nexus_vpn.utils.sudo import sudo_run, sudo_write_file, sudo_read_file

class IKEv2Manager:
    SECRETS_FILE = "/etc/ipsec.secrets"
    IPSEC_CONF_FILE = "/etc/ipsec.conf"

    @staticmethod
    def init_pki(domain):
        CertManager.setup_ca(domain)

    @staticmethod
    def generate_config(domain):
        domain = domain.split()[0].strip()
        
        config = f"""config setup
    charondebug="ike 1, knl 1, cfg 0"
    uniqueids=no

conn %default
    keyexchange=ikev2
    ike=aes256gcm16-sha384-modp3072,aes256gcm16-sha384-modp4096,aes256-sha256-modp2048!
    esp=aes256gcm16-sha384,aes256-sha256,aes256-sha1!
    dpdaction=clear
    dpddelay=300s

conn IKEv2-Cert
    left=%any
    leftid=@{domain}
    leftcert=server.crt
    leftsendcert=always
    leftsubnet=0.0.0.0/0,::/0
    right=%any
    rightid=%any
    rightsourceip=10.10.10.0/24,fd00:10:10:10::/64
    rightdns=8.8.8.8,1.1.1.1,2001:4860:4860::8888
    auto=add

conn IKEv2-EAP
    left=%any
    leftid=@{domain}
    leftcert=server.crt
    leftsendcert=always
    leftauth=pubkey
    right=%any
    rightid=%any
    rightauth=eap-mschapv2
    rightsourceip=10.10.10.0/24,fd00:10:10:10::/64
    rightdns=8.8.8.8,1.1.1.1,2001:4860:4860::8888
    eap_identity=%identity
    auto=add
"""
        sudo_write_file(IKEv2Manager.IPSEC_CONF_FILE, config)
        
        # 初始化 ipsec.secrets，确保包含服务器私钥
        IKEv2Manager._init_secrets()
        
        sudo_run(["ipsec", "reload"])
        log.success(f"IPsec 配置已生成: {IKEv2Manager.IPSEC_CONF_FILE}")

    @staticmethod
    def _init_secrets():
        """初始化 ipsec.secrets 文件，确保包含服务器私钥"""
        try:
            content = sudo_read_file(IKEv2Manager.SECRETS_FILE)
        except Exception:
            content = ""
        
        # 检查是否已包含 RSA 私钥配置
        if ": RSA server.key" not in content and ": RSA /etc/ipsec.d/private/server.key" not in content:
            # 在文件开头添加私钥配置
            rsa_line = ": RSA server.key\n"
            if content and not content.startswith("\n"):
                rsa_line += "\n"
            content = rsa_line + content
            sudo_write_file(IKEv2Manager.SECRETS_FILE, content)
            log.info("已添加服务器私钥到 ipsec.secrets")

    @staticmethod
    def _remove_user_from_secrets(username):
        """从 secrets 文件中移除指定用户的行"""
        if not os.path.exists(IKEv2Manager.SECRETS_FILE):
            return
        try:
            content = sudo_read_file(IKEv2Manager.SECRETS_FILE)
            lines = content.splitlines(keepends=True)
            new_lines = []
            for line in lines:
                # 跳过匹配用户名的行
                if line.startswith(f'{username} :') or line.startswith(f'"{username}" :'):
                    continue
                new_lines.append(line)
            sudo_write_file(IKEv2Manager.SECRETS_FILE, "".join(new_lines))
        except Exception:
            pass

    @staticmethod
    def add_eap_user(username, password):
        IKEv2Manager._remove_user_from_secrets(username)
        
        # 追加用户
        try:
            content = sudo_read_file(IKEv2Manager.SECRETS_FILE)
        except Exception:
            content = ""
        content += f'{username} : EAP "{password}"\n'
        sudo_write_file(IKEv2Manager.SECRETS_FILE, content)
        sudo_run(["ipsec", "rereadsecrets"])
        log.success(f"EAP 用户 {username} 已激活。")

    @staticmethod
    def remove_eap_user(username):
        IKEv2Manager._remove_user_from_secrets(username)
        sudo_run(["ipsec", "rereadsecrets"])
        log.success(f"EAP 用户 {username} 已删除。")

    @staticmethod
    def create_mobileconfig(username, domain, p12_path):
        ca_content = CertManager.get_ca_content()
        with open(p12_path, "rb") as f:
            p12_content = f.read()
        ca_b64 = base64.b64encode(ca_content).decode()
        p12_b64 = base64.b64encode(p12_content).decode()
        
        domain = domain.split()[0].strip()
        p12_password = CertManager.P12_PASSWORD

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>PayloadIdentifier</key>
            <string>com.nexusvpn.ca.{domain}</string>
            <key>PayloadType</key>
            <string>com.apple.security.root</string>
            <key>PayloadUUID</key>
            <string>root-ca</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
            <key>PayloadContent</key>
            <data>{ca_b64}</data>
        </dict>
        <dict>
            <key>PayloadIdentifier</key>
            <string>com.nexusvpn.p12.{username}</string>
            <key>PayloadType</key>
            <string>com.apple.security.pkcs12</string>
            <key>PayloadUUID</key>
            <string>user-p12</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
            <key>PayloadContent</key>
            <data>{p12_b64}</data>
            <key>Password</key>
            <string>{p12_password}</string>
        </dict>
        <dict>
            <key>PayloadIdentifier</key>
            <string>com.nexusvpn.conf.{domain}</string>
            <key>PayloadType</key>
            <string>com.apple.vpn.managed</string>
            <key>PayloadUUID</key>
            <string>vpn-config</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
            <key>UserDefinedName</key>
            <string>NexusVPN ({domain})</string>
            <key>VPNType</key>
            <string>IKEv2</string>
            <key>IKEv2</key>
            <dict>
                <key>RemoteAddress</key>
                <string>{domain}</string>
                <key>RemoteIdentifier</key>
                <string>{domain}</string>
                <key>LocalIdentifier</key>
                <string>{username}</string>
                <key>AuthenticationMethod</key>
                <string>Certificate</string>
                <key>PayloadCertificateUUID</key>
                <string>user-p12</string>
            </dict>
        </dict>
    </array>
    <key>PayloadDisplayName</key>
    <string>NexusVPN ({username})</string>
    <key>PayloadIdentifier</key>
    <string>com.nexusvpn.profile</string>
    <key>PayloadType</key>
    <string>Configuration</string>
    <key>PayloadUUID</key>
    <string>config-profile</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
</dict>
</plist>"""
