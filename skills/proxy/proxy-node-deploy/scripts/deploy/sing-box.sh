#!/bin/bash
# sing-box.sh <协议> <端口> <密码/UUID>
# 支持: ss, vmess, vless, trojan, tuic
set -euo pipefail

PROTOCOL="${1:?用法: sing-box.sh <协议> <端口> <密码/UUID>}"
PORT="${2:?缺少端口}"
SECRET="${3:?缺少密码/UUID}"

# 安装
VERSION="1.11.0"
ARCH=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
curl -Lo /tmp/sing-box.tar.gz "https://github.com/SagerNet/sing-box/releases/download/v${VERSION}/sing-box-${VERSION}-linux-${ARCH}.tar.gz"
tar -xzf /tmp/sing-box.tar.gz -C /tmp
mv "/tmp/sing-box-${VERSION}-linux-${ARCH}/sing-box" /usr/local/bin/
rm -rf /tmp/sing-box*

mkdir -p /etc/sing-box

# 生成 inbound 配置
inbound() {
  case "$1" in
    shadowsocks|ss)
      cat << EOF
{"type":"shadowsocks","tag":"ss-in","listen":"::","listen_port":${PORT},"method":"2022-blake3-aes-256-gcm","password":"${SECRET}"}
EOF
      ;;
    vmess)
      cat << EOF
{"type":"vmess","tag":"vmess-in","listen":"::","listen_port":${PORT},"users":[{"uuid":"${SECRET}"}]}
EOF
      ;;
    vless)
      cat << EOF
{"type":"vless","tag":"vless-in","listen":"::","listen_port":${PORT},"users":[{"uuid":"${SECRET}","flow":"xtls-rprx-vision"}],"tls":{"enabled":true,"server_name":"bing.com","reality":{"enabled":true,"handshake":{"server":"bing.com","server_port":443},"private_key":"${SECRET}","short_id":["$(openssl rand -hex 4)"]}}}
EOF
      ;;
    trojan)
      cat << EOF
{"type":"trojan","tag":"trojan-in","listen":"::","listen_port":${PORT},"users":[{"password":"${SECRET}"}],"tls":{"enabled":true,"server_name":"bing.com","reality":{"enabled":true,"handshake":{"server":"bing.com","server_port":443},"private_key":"${SECRET}","short_id":["$(openssl rand -hex 4)"]}}}
EOF
      ;;
    tuic)
      UUID="${SECRET%%:*}" PASS="${SECRET#*:}"
      cat << EOF
{"type":"tuic","tag":"tuic-in","listen":"::","listen_port":${PORT},"users":[{"uuid":"${UUID}","password":"${PASS}"}],"tls":{"enabled":true,"server_name":"bing.com","reality":{"enabled":true,"handshake":{"server":"bing.com","server_port":443},"private_key":"${PASS}","short_id":["$(openssl rand -hex 4)"]}}}
EOF
      ;;
    *) echo "不支持: $1，可用: ss vmess vless trojan tuic" >&2; exit 1 ;;
  esac
}

INBOUND=$(inbound "$PROTOCOL")

cat > /etc/sing-box/config.json << EOF
{"inbounds":[${INBOUND}],"outbounds":[{"type":"direct","tag":"direct"},{"type":"block","tag":"block"}]}
EOF

# 服务
cat > /etc/systemd/system/sing-box.service << 'EOF'
[Unit]
Description=sing-box Service
After=network.target
[Service]
Type=simple
ExecStart=/usr/local/bin/sing-box run -c /etc/sing-box/config.json
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now sing-box

IP=$(curl -s ip.sb 2>/dev/null || echo "<IP>")
echo "✓ ${PROTOCOL} ${IP}:${PORT}"
