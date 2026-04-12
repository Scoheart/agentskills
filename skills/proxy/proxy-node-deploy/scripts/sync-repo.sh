#!/bin/bash
# sync-repo.sh [节点配置文件]
# clone → 追加节点到 sub.yaml → 更新 config.yaml → push
set -euo pipefail

REPO_URL="git@github.com:Scoheart/clash-rules.git"
TMP_DIR=$(mktemp -d /tmp/clash-rules-sync.XXXXXX)
trap 'rm -rf "$TMP_DIR"' EXIT

# 读取节点配置
NODE_YAML=$(cat "${1:--}")
NODE_NAME=$(echo "$NODE_YAML" | grep -m1 'name:' | sed 's/.*name: *//' | tr -d '"' | tr -d "'")
[ -z "$NODE_NAME" ] && { echo "错误: 无法提取节点名称"; exit 1; }

# Clone
git clone --depth 1 "$REPO_URL" "$TMP_DIR"

SUB_FILE="${TMP_DIR}/config/mihomo/proxy-providers/sub.yaml"
CONFIG_FILE="${TMP_DIR}/config/mihomo/config.yaml"

# 追加节点到 sub.yaml
echo "$NODE_YAML" >> "$SUB_FILE"

# 更新 config.yaml 第 2 行注释为当前所有节点
if [ -f "$CONFIG_FILE" ]; then
  ALL_NODES=$(sed -n 's/^[[:space:]]*- name:[[:space:]]*\(.*\)/\1/p' "$SUB_FILE" | tr -d '"' | tr -d "'" | paste -sd ", " -)
  sed -i.bak "2s|# .*|# 当前节点：${ALL_NODES}|" "$CONFIG_FILE" && rm -f "${CONFIG_FILE}.bak"
fi

# Commit & Push
cd "$TMP_DIR"
git add "$SUB_FILE" "$CONFIG_FILE"
git commit -m "feat: add proxy node ${NODE_NAME}"
git push

echo "✓ ${NODE_NAME} → $(git rev-parse --short HEAD) → https://proxy.scoheart.com/config/mihomo/proxy-providers/sub.yaml"
