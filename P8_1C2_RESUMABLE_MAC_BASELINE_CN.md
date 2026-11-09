# P8.1C-2B — 逐场进度与断点续跑修复

## 为什么此前运行了 5分52秒后停止？

原 `verify_scientific_runtime.py baseline` 中每场执行的上限为 `--max-case-seconds 300`，且脚本没有逐场进度或检查点。一场超时、模型契约失败或其他运行异常都会导致整批停止，同时丢失此前成功场次的临时结果。**5分52秒与某一场耗时达到300秒相符，但不构成确定诊断**。

本工具不修改原脚本，不更改科学引擎/P7/Private/8502，也不上传任何私有数据到 GitHub。新增：逐场 START/PASS/FAILED 提示；每成功一场单独写入安全检查点；运行失败后再次执行会验证输入哈希、源码与运行环境身份，一致才复用之前成功的场次。仅全部完成后生成原有格式的 Mac Baseline。

## 安装

从 Downloads 解压：

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_1C2_Resumable_Mac_Baseline_Hotfix_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python -m pytest -q tests/test_resumable_mac_baseline.py
python scripts/security_check.py
```

## 运行（原40组输入，无需重新提取）

```bash
python scripts/resumable_mac_baseline.py \
  --project-root "$HOME/Projects/football_market_analytics_v2_2" \
  --science-root "$HOME/Projects/football_market_analytics" \
  --data-root "$HOME/Projects/football_market_analytics" \
  --cases "$HOME/Documents/fma-private-parity/cases.json" \
  --baseline-file "$HOME/Documents/fma-private-parity/mac_baseline.json" \
  --checkpoint-dir "$HOME/Documents/fma-private-parity/mac_checkpoints" \
  --max-case-seconds 120
```

- `CASE i/40: PASS`：该场成功，并已写入私人 checkpoint。
- `CASE i/40: FAILED (CASE_TIMEOUT)`：第 i 场超时，之前的 checkpoint 保留。
- `CASE i/40: FAILED (WORKER_FAILURE)`：该场 Worker 返回错误，需要单独诊断；不等于模型输出错误。
- 发生失败后可**原样重新执行**，先前已成功的场次显示 `CHECKPOINT REUSED`；但若失败场仍有问题，则会再次失败，而非被跳过。
- 需要更大超时可把 `--max-case-seconds 120` 改成 `300`；从同一 checkpoint 目录继续即可。
- 如果已经成功生成 `mac_baseline.json`，再次执行会拒绝覆盖。请勿删除既有证据。
- **禁止**把 cases、checkpoints、baseline 文件夹复制到 GitHub repo。它们必须位于 `~/Documents/fma-private-parity/` 等私有位置。

## 范围边界

这只是诊断和工程验收工具，不改变预测表现或模型规则。`REFERENCE COVERAGE: NOT_CAPTURED` 仍然意味着参考数据指纹未完成，Mac Baseline 即使成功也不等于 Linux Parity。GitHub Repo 和独立 Streamlit 公开网址可以先上线，**不受本轮失败阻碍**；只有公众即时运行真实科学模型时才必须完成跨平台验收。
