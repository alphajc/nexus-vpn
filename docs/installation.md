# 安装指南

本文档详细介绍 Nexus-VPN 的安装与部署流程。

## 系统要求

### 操作系统

- **Ubuntu** 20.04 LTS 或更高版本（推荐）
- **Debian** 11 或更高版本
- **CentOS** 7 或更高版本

### 软件依赖

- **Python** 3.8 或更高版本
- **root 权限**（安装和运行均需要）

### 硬件要求

- **CPU**: 1 核心及以上
- **内存**: 512MB 及以上
- **硬盘**: 1GB 可用空间
- **网络**: 公网 IP 地址

### 端口要求

确保以下端口未被占用且防火墙已放行：

| 端口 | 协议 | 用途 |
|------|------|------|
| 443 | TCP | VLESS-Reality (Xray) |
| 500 | UDP | IKEv2 VPN |
| 4500 | UDP | IKEv2 NAT-T |

## 安装方式

### 方式一：通过 pip 安装（推荐）

```bash
pip install nexus-vpn
```

### 方式二：从源码安装

```bash
# 克隆仓库
git clone https://github.com/your-repo/nexus-vpn.git
cd nexus-vpn

# 安装依赖
pip install -r requirements.txt

# 安装包
pip install -e .
```

## 部署服务

### 基本部署

```bash
sudo nexus-vpn install --domain <服务器IP或域名>
```

**示例**：

```bash
# 使用 IP 地址
sudo nexus-vpn install --domain 203.0.113.10

# 使用域名
sudo nexus-vpn install --domain vpn.example.com
```

### 高级部署选项

```bash
sudo nexus-vpn install \
    --domain <服务器IP或域名> \
    --proto vless \
    --reality-dest <目标网站>
```

**参数说明**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--domain` | (必填) | 服务器公网 IP 或域名 |
| `--proto` | `vless` | 协议类型（目前仅支持 vless） |
| `--reality-dest` | `www.microsoft.com:443` | Reality 协议伪装的目标网站 |

### 部署过程

安装程序会自动执行以下步骤：

1. **安装系统依赖**
   - curl, wget, openssl, unzip
   - strongswan, strongswan-pki
   - libcharon-extra-plugins
   - iptables, iptables-persistent

2. **部署 Xray Core**
   - 下载 Xray v1.8.4
   - 配置 systemd 服务 (`nexus-xray`)

3. **配置网络**
   - 启用 IP 转发
   - 启用 BBR 拥塞控制
   - 配置 NAT 转发规则

4. **初始化 PKI**
   - 生成 CA 根证书
   - 生成服务器证书
   - 配置 StrongSwan

5. **生成连接信息**
   - 输出 VLESS 连接 URL
   - 显示二维码（可扫码导入）

## 验证安装

### 检查服务状态

```bash
sudo nexus-vpn status
```

正常输出示例：

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

### 手动检查服务

```bash
# 检查 Xray 服务
sudo systemctl status nexus-xray

# 检查 StrongSwan 服务
sudo systemctl status strongswan-starter
# 或
sudo systemctl status strongswan

# 检查端口监听
sudo ss -tlnp | grep 443
sudo ss -ulnp | grep -E '500|4500'
```

## 卸载

```bash
sudo nexus-vpn uninstall
```

卸载操作会：
- 停止所有相关服务
- 删除 Xray 二进制文件和配置
- 删除 PKI 证书
- 删除 StrongSwan 配置
- 清理 systemd 服务文件

## 故障排除

### 安装依赖失败

如果依赖安装失败，可手动安装：

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y curl wget openssl unzip \
    strongswan strongswan-pki libcharon-extra-plugins \
    iptables iptables-persistent

# CentOS
sudo yum install -y epel-release
sudo yum install -y curl wget openssl unzip \
    strongswan strongswan-pki iptables
```

### Xray 服务无法启动

```bash
# 查看日志
sudo journalctl -u nexus-xray -f

# 检查配置文件
sudo cat /usr/local/etc/xray/config.json
```

### StrongSwan 服务无法启动

```bash
# 查看日志
sudo journalctl -u strongswan-starter -f

# 检查配置
sudo cat /etc/ipsec.conf
sudo cat /etc/ipsec.secrets
```

### 端口被占用

```bash
# 查找占用 443 端口的进程
sudo lsof -i :443

# 查找占用 500/4500 端口的进程
sudo lsof -i :500
sudo lsof -i :4500
```

### 防火墙问题

```bash
# UFW (Ubuntu)
sudo ufw allow 443/tcp
sudo ufw allow 500/udp
sudo ufw allow 4500/udp

# firewalld (CentOS)
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=500/udp
sudo firewall-cmd --permanent --add-port=4500/udp
sudo firewall-cmd --reload

# iptables
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 500 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 4500 -j ACCEPT
```
