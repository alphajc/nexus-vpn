# 客户端配置指南

本文档详细介绍各平台客户端的配置方法。

## VLESS-Reality 客户端配置

### 连接信息获取

安装完成后，系统会输出 VLESS 连接 URL 和二维码：

```
URL: vless://550e8400-e29b-41d4-a716-446655440000@203.0.113.10:443?security=reality&sni=gateway.icloud.com&fp=chrome&pbk=xxxxx&sid=xxxx&type=tcp&flow=xtls-rprx-vision#NexusVPN
```

### iOS / macOS

#### Shadowrocket（推荐）

1. 打开 Shadowrocket
2. 点击左上角 `+` 添加节点
3. 选择「扫描二维码」或「从剪贴板导入」
4. 粘贴 VLESS URL 或扫描二维码
5. 保存并连接

#### V2Box

1. 打开 V2Box
2. 点击「添加配置」
3. 选择「从剪贴板导入」
4. 粘贴 VLESS URL
5. 保存并启用

### Android

#### v2rayNG（推荐）

1. 下载安装 [v2rayNG](https://github.com/2dust/v2rayNG/releases)
2. 点击右上角 `+` → 「从剪贴板导入」
3. 或点击 `+` → 「扫描二维码」
4. 选择配置并点击右下角连接按钮

#### 手动配置

如需手动配置，参数如下：

| 参数 | 值 |
|------|-----|
| 地址 (Address) | 服务器 IP |
| 端口 (Port) | 443 |
| 用户 ID (UUID) | 安装时生成的 UUID |
| 流控 (Flow) | xtls-rprx-vision |
| 传输协议 | tcp |
| 安全类型 | reality |
| SNI | gateway.icloud.com (或其他伪装域名) |
| Fingerprint | chrome |
| PublicKey | 安装时生成的公钥 |
| ShortId | 安装时生成的短 ID |

### Windows

#### v2rayN

1. 下载安装 [v2rayN](https://github.com/2dust/v2rayN/releases)
2. 右键系统托盘图标 → 「从剪贴板导入」
3. 或点击「服务器」→「从剪贴板导入批量URL」
4. 选择节点，右键设为活动服务器
5. 右键托盘图标 → 「系统代理」→「自动配置系统代理」

### Linux

#### v2rayA（Web 管理界面）

1. 安装 v2rayA：
   ```bash
   # Debian/Ubuntu
   wget -qO - https://apt.v2raya.org/key/public-key.asc | sudo tee /etc/apt/keyrings/v2raya.asc
   echo "deb [signed-by=/etc/apt/keyrings/v2raya.asc] https://apt.v2raya.org/ v2raya main" | sudo tee /etc/apt/sources.list.d/v2raya.list
   sudo apt update && sudo apt install v2raya
   ```

2. 启动服务：
   ```bash
   sudo systemctl enable --now v2raya
   ```

3. 访问 `http://localhost:2017`
4. 点击「导入」→ 粘贴 VLESS URL
5. 选择节点并启动

---

## IKEv2 VPN 客户端配置

### iOS

#### 证书认证方式（推荐）

1. 将 `.mobileconfig` 文件传输到 iOS 设备
   - 通过 AirDrop
   - 通过邮件附件
   - 通过 iCloud Drive

2. 打开文件，系统提示「已下载描述文件」

3. 进入「设置」→「通用」→「VPN与设备管理」

4. 点击「已下载的描述文件」→「NexusVPN」

5. 点击「安装」，输入设备密码

6. 安装完成后，进入「设置」→「VPN」

7. 开启 VPN 开关即可连接

#### EAP 账号密码方式

1. **下载 CA 证书**
   
   在电脑上执行：
   ```bash
   scp root@<服务器IP>:/etc/nexus-vpn/pki/ca.crt ./nexus-ca.crt
   ```
   
   将 `nexus-ca.crt` 通过 AirDrop 或邮件发送到 iOS 设备

2. **安装 CA 证书**
   - 打开证书文件
   - 进入「设置」→「通用」→「VPN与设备管理」
   - 安装已下载的描述文件
   - 进入「设置」→「通用」→「关于本机」→「证书信任设置」
   - 启用「NexusVPN Root CA」的完全信任

3. **配置 VPN**
   - 进入「设置」→「VPN」→「添加 VPN 配置」
   - 类型：IKEv2
   - 描述：NexusVPN
   - 服务器：`<服务器IP>`
   - 远程 ID：`<服务器IP>`（必填！）
   - 本地 ID：留空
   - 用户鉴定：用户名
   - 用户名：`<你的用户名>`
   - 密码：`<你的密码>`

4. 保存并连接

### macOS

#### 证书认证方式（推荐）

1. 双击 `.mobileconfig` 文件
2. 系统提示「描述文件安装」
3. 打开「系统偏好设置」→「描述文件」
4. 点击「安装」
5. 进入「系统偏好设置」→「网络」
6. 选择 NexusVPN，点击「连接」

#### EAP 账号密码方式

1. **下载并安装 CA 证书**
   ```bash
   scp root@<服务器IP>:/etc/nexus-vpn/pki/ca.crt ./nexus-ca.crt
   # 双击 nexus-ca.crt 安装到钥匙串
   ```

2. **信任 CA 证书**
   - 打开「钥匙串访问」
   - 找到「NexusVPN Root CA」
   - 双击 → 「信任」→ 「始终信任」

3. **配置 VPN**
   - 打开「系统偏好设置」→「网络」
   - 点击 `+` 添加新服务
   - 接口：VPN
   - VPN 类型：IKEv2
   - 服务名称：NexusVPN

4. **填写配置**
   - 服务器地址：`<服务器IP>`
   - 远程 ID：`<服务器IP>`
   - 本地 ID：留空
   - 点击「鉴定设置」
   - 选择「用户名」
   - 输入用户名和密码

5. 点击「连接」

### Android

#### strongSwan VPN Client（推荐）

1. 从 Google Play 安装 [strongSwan VPN Client](https://play.google.com/store/apps/details?id=org.strongswan.android)

2. **导入 CA 证书**（Android 11+ 必须）
   
   在电脑上执行：
   ```bash
   scp root@<服务器IP>:/etc/nexus-vpn/pki/ca.crt ./nexus-ca.crt
   ```
   
   将文件传输到手机，然后：
   - 打开「设置」→「安全」→「加密与凭据」→「安装证书」
   - 选择「CA 证书」
   - 选择 `nexus-ca.crt` 文件安装

3. **配置 VPN**
   - 打开 strongSwan VPN Client
   - 点击「ADD VPN PROFILE」
   - Server：`<服务器IP>`
   - VPN Type：IKEv2 EAP (Username/Password)
   - Username：`<你的用户名>`
   - Password：`<你的密码>`（可选择保存）
   - CA certificate：选择「Select automatically」或手动选择已安装的证书

4. 保存并连接

#### 证书认证方式

1. 将 P12 证书文件传输到手机
   ```bash
   scp root@<服务器IP>:/etc/nexus-vpn/pki/certs/<用户名>.p12 ./
   ```

2. 安装证书
   - 打开「设置」→「安全」→「加密与凭据」→「安装证书」
   - 选择「VPN 和应用用户证书」
   - 选择 P12 文件，输入密码：`nexusvpn`

3. 配置 strongSwan
   - VPN Type：IKEv2 Certificate
   - User certificate：选择已安装的用户证书

### Windows 10/11

#### EAP 账号密码方式

1. **下载并安装 CA 证书**
   ```powershell
   scp root@<服务器IP>:/etc/nexus-vpn/pki/ca.crt ./nexus-ca.crt
   ```

2. **安装证书到受信任的根证书颁发机构**
   - 双击 `nexus-ca.crt`
   - 点击「安装证书」
   - 选择「本地计算机」→「下一步」
   - 选择「将所有证书放入下列存储」
   - 点击「浏览」→ 选择「受信任的根证书颁发机构」
   - 完成安装

3. **配置 VPN**
   - 打开「设置」→「网络和 Internet」→「VPN」
   - 点击「添加 VPN 连接」
   - VPN 提供商：Windows (内置)
   - 连接名称：NexusVPN
   - 服务器名称或地址：`<服务器IP>`
   - VPN 类型：IKEv2
   - 登录信息类型：用户名和密码
   - 用户名：`<你的用户名>`
   - 密码：`<你的密码>`

4. **配置远程 ID（重要！）**
   - 打开「控制面板」→「网络和共享中心」
   - 点击「更改适配器设置」
   - 右键「NexusVPN」→「属性」
   - 切换到「安全」选项卡
   - 确认 VPN 类型为「IKEv2」
   - 点击「高级设置」
   - 勾选「使用证书进行身份验证」下的「验证服务器的名称或 IP 地址」
   - 输入服务器 IP

5. 连接 VPN

---

## 常见问题

### VLESS 连接问题

**Q: 连接超时**
- 检查服务器 443 端口是否开放
- 检查 Xray 服务是否运行：`systemctl status nexus-xray`

**Q: TLS 握手失败**
- 确认 Reality 配置的目标网站可访问
- 尝试更换 `--reality-dest` 参数

### IKEv2 连接问题

**Q: 证书验证失败**
- 确保已安装 CA 根证书
- 确保 CA 证书已设为「完全信任」

**Q: 连接被拒绝**
- 检查远程 ID 是否正确填写（必须与服务器 IP/域名一致）
- 检查 StrongSwan 服务状态：`systemctl status strongswan-starter`

**Q: 认证失败 (EAP)**
- 确认用户名和密码正确
- 检查 `/etc/ipsec.secrets` 中是否存在该用户

**Q: Android 无法连接**
- Android 11+ 必须手动安装 CA 证书
- 确保选择正确的证书类型安装

### 获取连接日志

**服务器端**：
```bash
# Xray 日志
sudo journalctl -u nexus-xray -f

# StrongSwan 日志
sudo journalctl -u strongswan-starter -f
# 或
sudo tail -f /var/log/syslog | grep charon
```
