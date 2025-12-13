# 命令参考

本文档提供 Nexus-VPN 所有命令的完整参考。

## 命令概览

```
nexus-vpn
├── install      # 部署 VPN 服务（幂等，可重复执行）
├── uninstall    # 卸载 VPN 服务
├── status       # 查看服务状态
├── update       # 更新组件
│   ├── xray         # 更新 Xray Core
│   └── strongswan   # 更新 StrongSwan
└── user         # 用户管理
    ├── add      # 添加用户
    ├── del      # 删除用户
    └── list     # 列出用户
```

## 全局说明

- 命令本身**不需要 sudo 执行**，需要特权操作时会自动请求 sudo
- 也可使用 `sudo nexus-vpn <命令>` 或以 root 用户运行

---

## nexus-vpn install

部署 VPN 服务，包括 VLESS-Reality 和 IKEv2。

**幂等性**：此命令可重复执行。重新运行时会：
- 保留现有用户和密钥
- 更新配置文件（如 Reality 目标）
- 跳过已安装的组件

### 语法

```bash
nexus-vpn install [OPTIONS]
```

### 选项

| 选项 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--domain` | TEXT | 是 | - | 服务器公网 IP 或域名 |
| `--proto` | CHOICE | 否 | `vless` | 协议类型，目前仅支持 `vless` |
| `--reality-dest` | TEXT | 否 | `www.microsoft.com:443` | Reality 协议伪装的目标网站（可多次指定） |

### 示例

```bash
# 基本安装
nexus-vpn install --domain 203.0.113.10

# 使用域名
nexus-vpn install --domain vpn.example.com

# 自定义 Reality 目标
nexus-vpn install --domain 203.0.113.10 --reality-dest gateway.icloud.com:443

# 多个 Reality 目标（增加伪装多样性）
nexus-vpn install --domain 203.0.113.10 \
  --reality-dest www.microsoft.com:443 \
  --reality-dest gateway.icloud.com:443 \
  --reality-dest dl.google.com:443

# 修复/更新配置（重新运行 install，保留用户和证书）
nexus-vpn install --domain vpn.example.com --reality-dest itunes.apple.com:443

# 交互式安装（不提供 --domain 参数时会提示输入）
nexus-vpn install
```

### 执行流程

1. 检查操作系统兼容性
2. 安装系统依赖包
3. 下载并部署 Xray Core（已存在则跳过）
4. 配置网络（IP 转发、BBR、NAT）
5. 初始化 PKI 环境（已存在则跳过）
6. 生成 VLESS 配置并启动服务（保留现有用户）
7. 初始化 IKEv2 VPN
8. 输出连接信息和二维码

---

## nexus-vpn uninstall

卸载 VPN 服务，停止所有服务并清理文件。

### 语法

```bash
nexus-vpn uninstall
```

### 选项

无

### 示例

```bash
nexus-vpn uninstall
```

### 执行流程

1. 显示确认提示
2. 停止 nexus-xray 服务
3. 停止 strongswan 服务
4. 删除 Xray 二进制文件和配置
5. 删除 PKI 证书目录
6. 删除 IPsec 配置文件
7. 清理 systemd 服务文件

### 清理的文件

- `/usr/local/bin/xray`
- `/usr/local/etc/xray/`
- `/etc/nexus-vpn/`
- `/etc/ipsec.conf`
- `/etc/ipsec.secrets`
- `/etc/systemd/system/nexus-xray.service`

---

## nexus-vpn update

更新组件版本命令组。

### 子命令

| 命令 | 说明 |
|------|------|
| `xray` | 更新 Xray Core |
| `strongswan` | 更新 StrongSwan |

---

## nexus-vpn update xray

更新 Xray Core 到指定版本或最新版本。

### 语法

```bash
nexus-vpn update xray [OPTIONS]
```

### 选项

| 选项 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--version` | TEXT | 否 | (最新版) | 指定版本号（如 1.8.6） |

### 示例

```bash
# 更新到最新版
nexus-vpn update xray

# 更新到指定版本
nexus-vpn update xray --version 1.8.6
```

---

## nexus-vpn update strongswan

更新 StrongSwan 到最新版本。

### 语法

```bash
nexus-vpn update strongswan
```

### 示例

```bash
nexus-vpn update strongswan
```

---

## nexus-vpn status

检查 VPN 服务的运行状态。

### 语法

```bash
nexus-vpn status
```

### 选项

无

### 示例

```bash
nexus-vpn status
```

### 输出说明

```
🛡️ Nexus-VPN 系统状态
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 组件          ┃ 状态信息      ┃ 附加详情              ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━┩
│ Xray (VLESS)  │ active        │ TCP/443: OPEN         │
│ StrongSwan    │ active        │ UDP/500: OPEN         │
│               │               │ UDP/4500: OPEN        │
│ Kernel        │ 已开启 (BBR)  │ IP Forward: Enabled   │
└───────────────┴───────────────┴───────────────────────┘
```

**状态说明**：

| 状态 | 颜色 | 说明 |
|------|------|------|
| active | 绿色 | 服务正常运行 |
| inactive | 红色 | 服务未运行 |
| OPEN | 绿色 | 端口正常监听 |
| CLOSED | 红色 | 端口未监听 |
| Enabled | 绿色 | 功能已启用 |
| Disabled | 红色 | 功能未启用 |

---

## nexus-vpn user

用户管理命令组。

### 子命令

| 命令 | 说明 |
|------|------|
| `add` | 添加用户 |
| `del` | 删除用户 |
| `list` | 列出所有用户 |

---

## nexus-vpn user add

添加新用户。

### 语法

```bash
nexus-vpn user add --type <TYPE> --username <USERNAME>
```

### 选项

| 选项 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--type` | CHOICE | 是 | 用户类型：`v2ray`、`ikev2-cert`、`ikev2-eap` |
| `--username` | TEXT | 是 | 用户名 |

### 用户类型

| 类型 | 说明 | 生成物 |
|------|------|--------|
| `v2ray` | VLESS 代理用户 | 自动分配 UUID |
| `ikev2-cert` | IKEv2 证书用户 | `.mobileconfig` 文件 |
| `ikev2-eap` | IKEv2 账号密码用户 | 需输入密码 |

### 示例

```bash
nexus-vpn user add --type v2ray --username alice
```

---

## nexus-vpn user del

删除用户。

### 语法

```bash
nexus-vpn user del --type <TYPE> --username <USERNAME>
```

### 选项

| 选项 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `--type` | CHOICE | 是 | 用户类型：`v2ray`、`ikev2-cert`、`ikev2-eap` |
| `--username` | TEXT | 是 | 用户名 |

### 示例

```bash
# 删除 V2Ray 用户
nexus-vpn user del --type v2ray --username alice

# 删除 IKEv2 证书用户
nexus-vpn user del --type ikev2-cert --username bob

# 删除 IKEv2 EAP 用户
nexus-vpn user del --type ikev2-eap --username charlie
```

### 删除内容

**v2ray**：
- 从 Xray 配置中移除用户
- 重启 Xray 服务

**ikev2-cert**：
- 用户证书 (`.crt`)
- 用户私钥 (`.key`)
- P12 文件 (`.p12`)
- mobileconfig 文件

**ikev2-eap**：
- 从 `/etc/ipsec.secrets` 中移除用户
- 重新加载 IPsec 密钥

---

## nexus-vpn user list

列出所有用户。

### 语法

```bash
nexus-vpn user list
```

### 选项

无

### 示例

```bash
nexus-vpn user list
```

### 输出

分三个表格显示：
1. **V2Ray 用户** - 显示用户名和 UUID
2. **IKEv2 证书用户** - 显示用户名和证书状态
3. **IKEv2 EAP 用户** - 显示用户名和认证类型

---

## 退出码

| 退出码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1 | 一般错误（权限不足、参数错误等） |

---

## 环境变量

目前 Nexus-VPN 不使用环境变量配置。

---

## 配置文件

| 文件 | 说明 |
|------|------|
| `/usr/local/etc/xray/config.json` | Xray/VLESS 配置 |
| `/etc/ipsec.conf` | StrongSwan 主配置 |
| `/etc/ipsec.secrets` | IPsec 密钥和 EAP 凭据 |
| `/etc/nexus-vpn/pki/` | PKI 证书目录 |
