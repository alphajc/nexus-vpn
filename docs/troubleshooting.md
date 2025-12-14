# 故障排除

本文档提供常见问题的诊断和解决方案。

## 诊断工具

### 检查服务状态

```bash
# 综合状态检查
nexus-vpn status

# Xray 服务状态
sudo systemctl status nexus-xray

# StrongSwan 服务状态
sudo systemctl status strongswan-starter
# 或
sudo systemctl status strongswan
```

### 查看日志

```bash
# Xray 日志
sudo journalctl -u nexus-xray -f

# StrongSwan 日志
sudo journalctl -u strongswan-starter -f

# 系统日志中的 charon 信息
sudo tail -f /var/log/syslog | grep charon

# 查看最近 100 行日志
sudo journalctl -u nexus-xray -n 100
sudo journalctl -u strongswan-starter -n 100
```

### 检查端口

```bash
# 检查 TCP 443 端口
sudo ss -tlnp | grep 443
sudo lsof -i :443

# 检查 UDP 500/4500 端口
sudo ss -ulnp | grep -E '500|4500'
sudo lsof -i :500
sudo lsof -i :4500
```

### 检查网络配置

```bash
# IP 转发状态
cat /proc/sys/net/ipv4/ip_forward

# BBR 状态
sysctl net.ipv4.tcp_congestion_control

# NAT 规则
sudo iptables -t nat -L POSTROUTING -n -v
```

---

## 安装问题

### 依赖安装失败

**症状**：安装过程中提示包安装失败

**解决方案**：

```bash
# 更新软件源
sudo apt-get update

# 手动安装依赖
sudo apt-get install -y curl wget openssl unzip \
    strongswan strongswan-pki libcharon-extra-plugins \
    iptables iptables-persistent

# CentOS 用户
sudo yum install -y epel-release
sudo yum install -y curl wget openssl unzip strongswan iptables
```

### Xray 下载失败

**症状**：无法下载 Xray 二进制文件

**解决方案**：

```bash
# 手动下载
wget https://github.com/XTLS/Xray-core/releases/download/v1.8.4/Xray-linux-64.zip

# 解压并安装
unzip Xray-linux-64.zip
sudo mv xray /usr/local/bin/
sudo chmod +x /usr/local/bin/xray

# 重新运行安装
nexus-vpn install --domain <your-domain>
```

### 权限不足

**症状**：提示 "必须使用 root 权限运行"

**解决方案**：

```bash
# 直接运行（会自动请求 sudo）
nexus-vpn install --domain <your-domain>

# 或切换到 root 用户
sudo -i
nexus-vpn install --domain <your-domain>
```

---

## VLESS-Reality 问题

### Xray 服务无法启动

**症状**：`nexus-xray` 服务状态为 inactive 或 failed

**诊断**：

```bash
sudo journalctl -u nexus-xray -n 50
```

**常见原因及解决**：

1. **配置文件语法错误**
   ```bash
   # 验证配置
   sudo /usr/local/bin/xray -test -config /usr/local/etc/xray/config.json
   ```

2. **端口被占用**
   ```bash
   sudo lsof -i :443
   # 停止占用端口的进程
   sudo systemctl stop nginx  # 如果是 nginx
   sudo systemctl stop apache2  # 如果是 apache
   ```

3. **二进制文件损坏**
   ```bash
   # 重新下载
   sudo rm /usr/local/bin/xray
   nexus-vpn install --domain <your-domain>
   ```

### 客户端连接超时

**症状**：客户端无法连接，超时

**诊断**：

```bash
# 检查端口是否开放
sudo ss -tlnp | grep 443

# 从外部测试端口
nc -zv <server-ip> 443
```

**解决方案**：

1. **检查防火墙**
   ```bash
   # UFW
   sudo ufw allow 443/tcp
   
   # firewalld
   sudo firewall-cmd --permanent --add-port=443/tcp
   sudo firewall-cmd --reload
   
   # iptables
   sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
   ```

2. **检查云服务商安全组**
   - 登录云控制台
   - 检查安全组/防火墙规则
   - 确保 TCP 443 入站规则已添加

### TLS 握手失败

**症状**：客户端报告 TLS 握手错误

**解决方案**：

1. **更换 Reality 目标网站**
   ```bash
   nexus-vpn uninstall
   nexus-vpn install --domain <your-domain> --reality-dest www.apple.com:443
   ```

2. **检查目标网站可访问性**
   ```bash
   curl -I https://www.microsoft.com
   ```

---

## IKEv2 VPN 问题

### StrongSwan 服务无法启动

**症状**：strongswan 服务状态为 inactive 或 failed

**诊断**：

```bash
sudo journalctl -u strongswan-starter -n 50
# 或
sudo journalctl -u strongswan -n 50
```

**常见原因及解决**：

1. **配置文件错误**
   ```bash
   # 检查配置语法
   sudo ipsec statusall
   ```

2. **证书问题**
   ```bash
   # 检查证书是否存在
   ls -la /etc/ipsec.d/cacerts/
   ls -la /etc/ipsec.d/certs/
   ls -la /etc/ipsec.d/private/
   ```

3. **AppArmor 限制**
   ```bash
   sudo aa-complain /usr/lib/ipsec/charon
   sudo aa-complain /usr/lib/ipsec/stroke
   sudo systemctl restart strongswan-starter
   ```

### 客户端认证失败

**症状**：客户端报告认证失败

**诊断**：

```bash
sudo journalctl -u strongswan-starter -f
# 在另一个终端尝试连接，观察日志
```

**解决方案**：

1. **EAP 用户 - 检查凭据**
   ```bash
   # 查看已配置的用户
   sudo cat /etc/ipsec.secrets | grep EAP
   
   # 重新添加用户
   nexus-vpn user del --type ikev2-eap --username <user>
   nexus-vpn user add --type ikev2-eap --username <user>
   ```

2. **证书用户 - 重新生成证书**
   ```bash
   nexus-vpn user del --type ikev2-cert --username <user>
   nexus-vpn user add --type ikev2-cert --username <user>
   ```

### 远程 ID 不匹配

**症状**：日志显示 "peer didn't accept" 或 "no matching peer config"

**解决方案**：

客户端配置中的「远程 ID」必须与服务器配置一致：
- 如果安装时使用 IP 地址，远程 ID 填写 IP 地址
- 如果安装时使用域名，远程 ID 填写域名

### 证书不受信任

**症状**：客户端报告证书不受信任

**解决方案**：

1. **iOS/macOS**
   - 确保已安装 `.mobileconfig` 或 CA 证书
   - 进入「设置」→「通用」→「关于本机」→「证书信任设置」
   - 启用 CA 证书的完全信任

2. **Android**
   - 必须手动安装 CA 证书
   - 「设置」→「安全」→「加密与凭据」→「安装证书」→「CA 证书」

3. **Windows**
   - 将 CA 证书安装到「受信任的根证书颁发机构」
   - 使用「本地计算机」存储，而非「当前用户」

### VPN 已连接但无法上网

**症状**：VPN 显示已连接，但无法访问网络

**诊断**：

```bash
# 检查 IP 转发
cat /proc/sys/net/ipv4/ip_forward

# 检查 NAT 规则
sudo iptables -t nat -L POSTROUTING -n -v
```

**解决方案**：

```bash
# 启用 IP 转发
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward

# 获取默认网卡
IFACE=$(ip route show default | awk '/default/ {print $5}')

# 添加 NAT 规则
sudo iptables -t nat -A POSTROUTING -s 10.10.10.0/24 -o $IFACE -j MASQUERADE

# 保存规则
sudo netfilter-persistent save
```

---

## 用户管理问题

### 无法添加用户

**症状**：添加用户时报错

**解决方案**：

1. **V2Ray 用户 - 检查配置文件**
   ```bash
   sudo cat /usr/local/etc/xray/config.json
   # 确保文件存在且格式正确
   ```

2. **IKEv2 用户 - 检查 PKI 目录**
   ```bash
   ls -la /etc/nexus-vpn/pki/
   # 如果不存在，重新运行安装
   ```

### 用户列表为空

**症状**：`user list` 显示无用户

**解决方案**：

```bash
# 检查配置文件
sudo cat /usr/local/etc/xray/config.json
sudo cat /etc/ipsec.secrets
sudo ls /etc/nexus-vpn/pki/certs/
```

---

## 性能问题

### 连接速度慢

**诊断**：

```bash
# 检查 BBR 状态
sysctl net.ipv4.tcp_congestion_control

# 检查服务器负载
top
htop
```

**解决方案**：

1. **启用 BBR**
   ```bash
   echo "net.core.default_qdisc=fq" | sudo tee -a /etc/sysctl.conf
   echo "net.ipv4.tcp_congestion_control=bbr" | sudo tee -a /etc/sysctl.conf
   sudo sysctl -p
   ```

2. **检查服务器带宽**
   ```bash
   # 安装测速工具
   sudo apt-get install speedtest-cli
   speedtest-cli
   ```

---

## 重置与恢复

### 完全重置

```bash
# 卸载
nexus-vpn uninstall

# 清理残留文件
sudo rm -rf /etc/nexus-vpn
sudo rm -rf /usr/local/etc/xray
sudo rm -f /etc/ipsec.conf /etc/ipsec.secrets

# 重新安装
nexus-vpn install --domain <your-domain>
```

### 仅重置 PKI

```bash
# 删除 PKI 目录
sudo rm -rf /etc/nexus-vpn/pki

# 重新运行安装以重新生成证书
nexus-vpn install --domain <your-domain>
```

### 仅重置 Xray 配置

```bash
# 删除 Xray 配置
sudo rm -rf /usr/local/etc/xray

# 重新运行安装
nexus-vpn install --domain <your-domain>
```

---

## 获取帮助

如果以上方案无法解决问题：

1. **收集诊断信息**
   ```bash
   nexus-vpn status
   sudo journalctl -u nexus-xray -n 100 > xray.log
   sudo journalctl -u strongswan-starter -n 100 > strongswan.log
   ```

2. **提交 Issue**
   - 附上系统版本信息
   - 附上错误日志
   - 描述复现步骤
