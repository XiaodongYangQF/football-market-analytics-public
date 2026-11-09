# P8.1C-1 — 受控在线预测试运行（中文交接）

## 这次已经做了什么

1. 复用 P7.4 **原有科学模型 worker**，并把它从 8504 本地 Streamlit 界面的调用方式抽取成共用的隔离执行函数。不改变模型输入、AH/OU 规则、结算或策略。
2. 新增 `scripts/run_private_forecast_gateway.py`：仅监听 `127.0.0.1:8765`；Bearer Token；严格 JSON 白名单；全局单任务运行；默认每小时最多4次、至少间隔30秒；异常响应不包含内部路径及日志。**不应直接暴露公网。**
3. 新增 `fma_portfolio/hosted_client.py`：云端 Streamlit 服务端可通过 HTTPS 调用独立的模型 Gateway。**默认禁用**；只有 OIDC 登录且邮箱在服务端白名单中时才可使用。所有密钥保存在服务器端，不允许写入 GitHub。
4. 网页 `Interactive forecast` 自动区分：原 8504 owner-local（保持不变）；已授权的 Hosted Pilot；普通在线访客（只读，预测按钮禁用）。
5. 保留 P8.1D 每日 Performance 与 P8.1E GitHub 存证系统，绝不将未公开的内部计算自动算作公开赛前记录。

## 安装到 Mac

在已有 **P8.1E** 项目上，下载本补丁到 `~/Downloads`，关闭8504：

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_1C_Hosted_Prediction_Pilot_Patch_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/security_check.py
python -m pytest -q
```

### A. 确保旧的8504没有变化

```bash
python scripts/run_owner_local.py --check \
  --science-root "$HOME/Projects/football_market_analytics" \
  --data-root "$HOME/Projects/football_market_analytics"
```

随后用原来 `run_owner_local.py --port 8504 ...` 启动，它仍在 Mac 的 127.0.0.1 上运行真实预测，功能和原逻辑一致。

### B. 验证独立服务的准备状态（不会联网、也不会运行模型）

```bash
python scripts/run_private_forecast_gateway.py --check \
  --project-root "$HOME/Projects/football_market_analytics_v2_2" \
  --science-root "$HOME/Projects/football_market_analytics" \
  --data-root "$HOME/Projects/football_market_analytics"
```

预期出现 `GATEWAY PREFLIGHT PASS`。这是**目录及解释器预检**，不是模型的线上验证。

### C. 本机真正 API 试运行（可选）

详细步骤见 `docs/hosted_prediction.md`。需设置 `FMA_GATEWAY_TOKEN`，在另一终端从受信任客户端调用 `/v1/forecast`，返回经过检查的 AH/OU 预测。在同样的科学引擎环境和相同的预测请求上，再运行 `python scripts/check_gateway_parity.py --request "$HOME/Documents/fma_pilot_request.json" --science-root "$HOME/Projects/football_market_analytics" --data-root "$HOME/Projects/football_market_analytics"` 比较原本的冻结 worker 与独立 Gateway 的输出。至少覆盖不同联赛、AH/OU 各类信号及 NO SIGNAL。只有严格一致才进入云部署。

## 下一轮上线之前必须完成

- 科学引擎 Linux 打包及版本冻结，不拷贝 Mac Private 的原始数据目录上 GitHub。
- 服务器选择、HTTPS 与独立网络访问控制；Streamlit OIDC 身份认证的真实测试。
- 模型输出一致性测试、性能/并发审计；持久化限额和异常恢复。
- 未来公开访问者开放策略及第三方赔率授权检查。

**目前完成的是独立安全调用的第一版代码，不是已经在互联网开放的真实预测服务。** 不需要今天就部署，也不会擅自访问或改动你电脑上的 Private / Local Public。
