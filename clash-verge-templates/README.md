# Clash Verge Rev / Mihomo 防遥测偷跑配置指南

## 为什么会偷跑几十 GB 流量？
Antigravity 后台进程 `language_server` 会持续向 `https://play.googleapis.com/log`（Google Clearcut 遥测接口）发送日志。一旦代理抖动或超时触发重传循环，单条连接即可在 20 分钟内单向上传 **130+ MB**，而不影响正常 AI 对话接口（`daily-cloudcode-pa.googleapis.com`、`aicode.googleapis.com`）。

## 两个必踩的坑
1. **必须开启 `sniffer.parse-pure-ip: true` 与 `QUIC: [443]`**：当系统把域名直接解析成 Google IP（如 `172.217.x.x`）时，不开纯 IP SNI 嗅探会直接落入兜底代理规则，导致 `DOMAIN` 规则失效；而直接按 IP 封锁又会误杀同 IP 的正常对话接口。
2. **Clash Verge Rev 的全局 `Merge.yaml` 不会把 `prepend-rules:` 展开到 `rules:`**：实测把 `- DOMAIN,play.googleapis.com,REJECT` 写在全局 `Merge.yaml` 里无效，**必须写入全局 `Script.js`**（见 [Script.block-telemetry.js](./Script.block-telemetry.js)）才能对所有订阅生效。

## 配置步骤
1. Clash Verge Rev → **订阅 (Profiles)** → 打开全局扩展配置 **Merge**，合并 [Merge.sniffer.yaml](./Merge.sniffer.yaml) 中的 `sniffer:` 段。
2. 打开全局扩展脚本 **Script**，合入 [Script.block-telemetry.js](./Script.block-telemetry.js) 的 `DOMAIN,play.googleapis.com,REJECT` 规则。
3. 右键当前使用的订阅 → **重新加载 (Reactivate)**，在「连接 / 规则」面板确认 `play.googleapis.com` 命中 `REJECT`，同时 AI 对话（`daily-cloudcode-pa.googleapis.com`）正常走代理。
