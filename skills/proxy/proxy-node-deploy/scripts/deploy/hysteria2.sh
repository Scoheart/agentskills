#!/bin/bash
# hysteria2.sh [端口] [密码]
# 默认端口 443，密码随机生成
set -euo pipefail

PORT="${1:-443}"
PASSWORD="${2:-$(openssl rand -hex 16)}"

# 安装
bash <(curl -fsSL https://get.hy2.sh/)

# 证书
mkdir -p /etc/hysteria
openssl req -x509 -nodes -newkey ec:<(openssl ecparam -name prime256v1) \
  -keyout /etc/hysteria/server.key \
  -out /etc/hysteria/server.crt \
  -subj "/CN=bing.com" -days 3650 2>/dev/null

FINGERPRINT=$(openssl x509 -in /etc/hysteria/server.crt -noout -fingerprint -sha256 | cut -d= -f2 | tr -d ':')

# 配置
cat > /etc/hysteria/config.yaml << EOF
listen: :${PORT}
tls:
  cert: /etc/hysteria/server.crt
  key: /etc/hysteria/server.key
auth:
  type: password
  password: ${PASSWORD}
masquerade:
  type: proxy
  proxy:
    url: https://www.bing.com
    rewriteHost: true
bandwidth:
  up: 100 mbps
  down: 100 mbps
EOF

# 服务
cat > /etc/systemd/system/hysteria.service << 'EOF'
[Unit]
Description=Hysteria Server
After=network.target
[Service]
Type=simple
ExecStart=/usr/local/bin/hysteria server -c /etc/hysteria/config.yaml
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now hysteria

IP=$(curl -s ip.sb 2>/dev/null || echo "<IP>")
echo "✓ ${IP}:${PORT} | password=${PASSWORD} | fingerprint=${FINGERPRINT}"
