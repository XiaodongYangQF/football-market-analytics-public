# P8.1C-2E · 2026–27 赛季 Eligibility Gate（Mac 安装及使用）

## 目的与边界

本更新**只修改独立 GitHub Portfolio**，不触碰 Private 科学引擎、Local Public (8502) 及 Public V2 交易规则。

- **ELIGIBLE**：名单核实且非本赛季升班马，可以调用原模型；不意味着必然出现 FORECAST。
- **INELIGIBLE**：2026–27 赛季当赛季升班马；直接停止，不调用 AH/P2；**不是 NO SIGNAL**。
- **UNVERIFIED**：球队不在冻结的该联赛球队名录、跨赛季/超出时间范围或配置缺失；保守拒绝，不猜测。
- **NO SIGNAL**：真正运行成功后才可由原模型输出。

政策数据 `data/eligibility_policy_2026_27.json`：五大联赛2026–27赛季名单及公开来源网址；球队名称使用原 Local Public 中的 canonical 名称（仅球队名称，不含赛程、赔率及私有数据），并加入必要官方/显示名称别名。

**历史数据检查**：此前40个真实输入中，`CASE 24/40`（Lazio–Monza）和 `CASE 32/40`（Freiburg–Schalke 04）属于当前赛季升班马排除范围；另外38场通过资格检查。第24场以前返回过 Worker 成功，因此不能把第32场的 P2 故障直接认定为升班马导致；此次专门新增统一的前置适用范围控制。

## 安装（前提：已安装 P8.1C-2 的 resumable Mac baseline 补丁）

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_1C2E_Season_Eligibility_Gate_Patch_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/security_check.py
python -m pytest -q
```

## 第一步：仅检查，不运行模型

```bash
python scripts/eligible_mac_baseline.py \
  --cases "$HOME/Documents/fma-private-parity/cases.json" \
  --plan-only
```

预期显示 `40 total; 38 eligible; 2 ineligible; 0 unverified`，第24和32场被标记为 INELIGIBLE。原始 `cases.json` 和 `mac_checkpoints/` 不会修改。

## 第二步：复用旧 checkpoint，完成符合资格的 Baseline

```bash
python scripts/eligible_mac_baseline.py \
  --project-root "$HOME/Projects/football_market_analytics_v2_2" \
  --science-root "$HOME/Projects/football_market_analytics" \
  --data-root "$HOME/Projects/football_market_analytics" \
  --cases "$HOME/Documents/fma-private-parity/cases.json" \
  --checkpoint-dir "$HOME/Documents/fma-private-parity/mac_checkpoints" \
  --eligible-cases-file "$HOME/Documents/fma-private-parity/eligible_cases.json" \
  --coverage-file "$HOME/Documents/fma-private-parity/eligibility_coverage.json" \
  --baseline-file "$HOME/Documents/fma-private-parity/mac_baseline_eligible.json" \
  --max-case-seconds 120
```

新脚本**保持原始第1–40场编号不变**，对已存的 Case 1–23、25–31 等符合条件的 checkpoint 进行哈希校验后复用；第24、32场不执行模型，未来第33–40场按原编号继续计算。若新出现真实模型错误则立刻停止，但已成功 checkpoint 保留。

完整成功时会在 Mac 私人目录生成：

- `eligible_cases.json`：原始40场里符合资格的38组输入；用于后续 Linux parity。
- `eligibility_coverage.json`：原始输入哈希、资格版本哈希、两场排除原因及数量；**不作为预测或收益记录**。
- `mac_baseline_eligible.json`：符合资格场次实际运行结果；**不等于 Linux parity**。

脚本不会覆盖上述已有文件；如文件已存在，应核实后另选文件名。所有证据必须保存在 GitHub 仓库外。

## 后续 Linux 验收

Linux 端需使用同一份 **`eligible_cases.json`** 和 Mac 的 **`mac_baseline_eligible.json`**，并提供 **`--eligibility-coverage-file`** 指向随测试材料安全传输的私有覆盖报告。新版 `verify_scientific_runtime.py verify` 会检查资格政策 SHA-256；未提供或不匹配时，即便数值输出一致，也**不会显示 `PROMOTION-CANDIDATE GATE: PASS`**。

仍需核实 `--reference-root` 对真实 P1/P2 参考数据的覆盖范围、依赖版本、Linux 真实运算和公网安全。当前 `REFERENCE COVERAGE: NOT_CAPTURED` 代表尚未达到生产验收。

## UI / API / 发布一致性

- GitHub Portfolio 的本地预测页面会在填写盘口前标出排除状态，并禁用预测按钮。
- Owner-local `predict` 和 Hosted Gateway 在调用模型前重复核验，阻止绕过 UI。
- 新增的 GitHub 赛前 Issue 发布程序，在创建新记录时拒绝把升班马或身份不明比赛当作 `NO SIGNAL` 发布。
- 历史已有的 Public V2 结果和 GitHub Issue **不重写、不追认、不删除**；是否需要另做研究范围注释，后续单独审核。

**本阶段不会修改任何冻结的模型输出、决策门槛或历史收益统计。**
