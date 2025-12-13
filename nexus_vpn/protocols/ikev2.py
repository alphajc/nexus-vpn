import os
import base64
import subprocess
from nexus_vpn.core.cert_mgr import CertManager
from nexus_vpn.utils.logger import log

class IKEv2Manager:
    SECRETS_FILE = "/etc/ipsec.secrets"

    @staticmethod
    def init_pki(domain):
        CertManager.setup_ca(domain)

    @staticmethod
    def generate_config(domain):
        # 保持配置不变
        pass 

    @staticmethod
    def add_eap_user(username, password):
        if os.path.exists(IKEv2Manager.SECRETS_FILE):
            subprocess.run(f"sed -i '/{username} /d' {IKEv2Manager.SECRETS_FILE}", shell=True)
            subprocess.run(f"sed -i '/\"{username}\" /d' {IKEv2Manager.SECRETS_FILE}", shell=True)
        
        with open(IKEv2Manager.SECRETS_FILE, "a") as f:
            f.write(f'{username} : EAP "{password}"\n')
        subprocess.run("ipsec rereadsecrets", shell=True)
        log.success(f"EAP 用户 {username} 已激活。")

    @staticmethod
    def remove_eap_user(username):
        if os.path.exists(IKEv2Manager.SECRETS_FILE):
            subprocess.run(f"sed -i '/{username} /d' {IKEv2Manager.SECRETS_FILE}", shell=True)
            subprocess.run("ipsec rereadsecrets", shell=True)
            log.success(f"EAP 用户 {username} 已删除。")

    @staticmethod
    def create_mobileconfig(username, domain, p12_path):
        ca_content = CertManager.get_ca_content()
        with open(p12_path, "rb") as f: p12_content = f.read()
        ca_b64 = base64.b64encode(ca_content).decode()
        p12_b64 = base64.b64encode(p12_content).decode()
        
        domain = domain.split()[0].strip()

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
            <string>nexusvpn</string>
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
                
                <!-- 核心修复: 强制指定 LocalIdentifier 为用户名 -->
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
