---
name: proxy-node-deploy
description: |
  在云服务器上部署代理节点（Hysteria2 / SS / VMess / VLESS / Trojan / TUIC），并同步到 clash-rules 仓库，push 后通过 Cloudflare Worker (proxy.scoheart.com) 即时生效。
  当用户要求"部署代理节点"、"新建节点"、"添加节点并同步"、"部署 Hysteria2/SS/VMess/VLESS/Trojan/TUIC"、"同步节点到 clash-rules"时触发。
  也适用于用户提到"添加代理"、"新建节点"且上下文涉及代理协议或 clash-rules 的场景。
---

# 代理节点部署 + 配置同步

VPS 部署代理协议 → 节点配置写入 clash-rules → git push → proxy.scoheart.com 即时生效。

## 支持的协议

| 协议 | 部署脚本 | 传输层 |
|------|---------|--------|
| Hysteria2 | `scripts/deploy/hysteria2.sh` | QUIC/UDP |
| SS / VMess / VLESS / Trojan / TUIC | `scripts/deploy/sing-box.sh <协议>` | TCP 或 UDP |

## 工作流

### 1. 收集信息

确认：协议类型、SSH 连接（IP/端口/用户）、节点名称（如 `US-Vultr-hy2`）、监听端口。

### 2. 部署服务端

**Hysteria2：**
```bash
ssh root@<IP> 'bash -s' < scripts/deploy/hysteria2.sh <端口> [密码]
```

**其他协议（sing-box）：**
```bash
ssh root@<IP> 'bash -s' < scripts/deploy/sing-box.sh <协议> <端口> <密码/UUID>
```

HY2 / TUIC 使用 UDP，确保防火墙已开放。

### 3. 生成节点配置

根据协议，从 `references/protocols/<协议>.yaml` 选取模板，填入部署输出的参数（IP、端口、密码等），写入临时文件。

### 4. 同步到仓库

```bash
scripts/sync-repo.sh /tmp/node.yaml    # 从文件
scripts/sync-repo.sh < /tmp/node.yaml  # 从 stdin
```

sync-repo.sh 会自动：**clone 到临时目录** → 更新 `proxy-providers/sub.yaml`（追加节点）→ 更新 `config.yaml`（节点注释）→ commit & push → 清理临时目录。

仓库地址：`git@github.com:Scoheart/clash-rules.git`。

### 5. 验证

```bash
curl -s https://proxy.scoheart.com/config/mihomo/proxy-providers/sub.yaml | grep "<节点名称>"
```

## 输出

向用户提供：节点信息摘要（协议/IP/端口/密码）、commit hash、线上验证结果。

## 注意

- commit message 不含密码
- HY2 / TUIC 需开放 UDP 端口
