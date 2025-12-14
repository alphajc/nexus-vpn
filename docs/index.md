# Nexus-VPN 文档

欢迎使用 Nexus-VPN！这是一个一键部署 **VLESS-Reality** + **IKEv2** VPN 的综合代理工具。

## 功能特性

- **VLESS-Reality**: 基于 Xray-core，支持 Reality 协议，抗检测能力强
- **IKEv2 VPN**: 基于 StrongSwan，支持证书认证和 EAP 认证
- **多用户管理**: 支持添加、删除、列出用户
- **自动配置**: 自动配置 BBR、NAT 转发、防火墙规则
- **iOS/macOS 支持**: 自动生成 `.mobileconfig` 配置文件

## 文档目录

### 快速开始

- [安装指南](installation.md) - 系统要求、安装步骤、部署服务

### 使用指南

- [用户管理](user-management.md) - 添加、删除、列出用户
- [客户端配置](client-configuration.md) - 各平台客户端的配置方法

### 参考手册

- [命令参考](command-reference.md) - 所有命令的详细说明
- [故障排除](troubleshooting.md) - 常见问题诊断与解决

## 快速开始

### 1. 安装

```bash
pip install nexus-vpn
```

### 2. 部署服务

```bash
nexus-vpn install --domain <服务器IP>
```

### 3. 添加用户

```bash
# V2Ray 用户
nexus-vpn user add --type v2ray --username alice

# IKEv2 EAP 用户
nexus-vpn user add --type ikev2-eap --username bob
```

### 4. 查看状态

```bash
nexus-vpn status
```

## 支持的协议

| 协议 | 端口 | 说明 |
|------|------|------|
| VLESS-Reality | TCP/443 | 基于 Xray，伪装成正常 HTTPS 流量 |
| IKEv2 | UDP/500, 4500 | 原生 VPN 协议，系统级支持 |

## 支持的平台

### 服务端

- Ubuntu 20.04+
- Debian 11+
- CentOS 7+

### 客户端

| 平台 | VLESS | IKEv2 |
|------|-------|-------|
| iOS | Shadowrocket, V2Box | 原生支持 |
| macOS | V2rayU, Qv2ray | 原生支持 |
| Android | v2rayNG | strongSwan |
| Windows | v2rayN | 原生支持 |
| Linux | v2rayA | strongSwan |

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                     Nexus-VPN                           │
├─────────────────────────────────────────────────────────┤
│  CLI Layer (Click)                                      │
│  ├── install / uninstall / status                       │
│  └── user add / del / list                              │
├─────────────────────────────────────────────────────────┤
│  Core Layer                                             │
│  ├── Installer      - 系统依赖、Xray、网络配置          │
│  ├── UserManager    - 用户 CRUD 操作                    │
│  └── CertManager    - PKI 证书管理                      │
├─────────────────────────────────────────────────────────┤
│  Protocol Layer                                         │
│  ├── V2RayManager   - VLESS-Reality 配置                │
│  └── IKEv2Manager   - StrongSwan 配置                   │
├─────────────────────────────────────────────────────────┤
│  Runtime                                                │
│  ├── Xray Core      - VLESS 代理服务                    │
│  └── StrongSwan     - IKEv2 VPN 服务                    │
└─────────────────────────────────────────────────────────┘
```

## 安全说明

- 所有证书有效期为 10 年
- P12 证书使用统一密码 `nexusvpn`
- EAP 密码以明文存储在 `/etc/ipsec.secrets`，请确保服务器安全
- 建议定期更换用户凭据

## 许可证

MIT License
