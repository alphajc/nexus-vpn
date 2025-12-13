# Nexus-VPN

一键部署 **VLESS-Reality** + **IKEv2** VPN 的综合代理工具。

## 功能特性

- **VLESS-Reality**: 基于 Xray-core，支持 Reality 协议，抗检测能力强
- **IKEv2 VPN**: 基于 StrongSwan，支持证书认证和 EAP 认证
- **多用户管理**: 支持添加、删除、列出用户
- **自动配置**: 自动配置 BBR、NAT 转发、防火墙规则
- **iOS/macOS 支持**: 自动生成 `.mobileconfig` 配置文件

## 系统要求

- **操作系统**: Ubuntu 20.04+ / Debian 11+ / CentOS 7+
- **Python**: 3.8+
- **权限**: 需要 root 权限运行

## 安装

```bash
pip install nexus-vpn
```

## 快速开始

### 部署服务

```bash
sudo nexus-vpn install --domain your-server-ip
```

### 查看状态

```bash
sudo nexus-vpn status
```

### 用户管理

```bash
# 添加 V2Ray 用户
sudo nexus-vpn user add --type v2ray --username alice

# 添加 IKEv2 证书用户
sudo nexus-vpn user add --type ikev2-cert --username bob

# 添加 IKEv2 EAP 用户
sudo nexus-vpn user add --type ikev2-eap --username charlie

# 列出所有用户
sudo nexus-vpn user list

# 删除用户
sudo nexus-vpn user del --type v2ray --username alice
```

### 卸载

```bash
sudo nexus-vpn uninstall
```

## 命令参考

| 命令 | 说明 |
|------|------|
| `nexus-vpn install` | 部署 VPN 服务 |
| `nexus-vpn uninstall` | 卸载 VPN 服务 |
| `nexus-vpn status` | 查看服务状态 |
| `nexus-vpn user add` | 添加用户 |
| `nexus-vpn user del` | 删除用户 |
| `nexus-vpn user list` | 列出用户 |

## 安装选项

```bash
nexus-vpn install --domain <域名/IP> [--proto vless] [--reality-dest <目标网站>]
```

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--domain` | (必填) | 服务器公网 IP 或域名 |
| `--proto` | `vless` | 协议类型 |
| `--reality-dest` | `www.microsoft.com:443` | Reality 偷取的目标网站 |

## 客户端配置

### V2Ray / Xray

安装完成后会自动显示连接 URL 和二维码，支持以下客户端：

- **iOS/macOS**: Shadowrocket, V2Box
- **Android**: v2rayNG
- **Windows**: v2rayN
- **Linux**: v2rayA

### IKEv2

- **iOS/macOS**: 使用生成的 `.mobileconfig` 文件
- **Windows**: 手动配置 IKEv2 VPN
- **Android**: strongSwan VPN Client

## 许可证

MIT License
