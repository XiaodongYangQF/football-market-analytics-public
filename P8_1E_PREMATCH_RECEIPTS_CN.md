# P8.1E — GitHub Pre-Match Forecast Receipt System（中文安装与交接）

## 目的和边界

- **GitHub Issue 是首个公开发布证据**。每个相同开赛时间的批次创建一个 Issue，包含全量公开的 P7.4 预测输入（AH、OU、固定2.5双方赔率）、AH/OU 模型输出、`NO SIGNAL`、模型策略标识及用户提供的 UTC 开赛时间。
- **GitHub 仓库 JSON 是同一份预测的可浏览镜像**，在页面的 `Pre-match archive` 查看。使用 SHA-256 连接 Issue 与 JSON。
- `Daily Performance` 仍由 **P8.1D** 从 Local Public 的公开结算快照更新。P8.1E 不重算模型、不自动下注，也不把这些新预测重复加入 P&L。
- **X 不参与每日赛事存证**，个人 X 仅精选分享。
- Private 和 Local Public（8502）不修改，8504 本机模型连接不变，云端模型仍默认关闭。

> **证据含义**：GitHub REST API 的 `created_at` 是平台记录的创建时间，可用于判断何时公开 Issue 的现存内容；用户手输的 kickoff UTC 不由我们独立核实。GitHub Issue 可被编辑或删除，故这是可公开核查的记录，**不是不可篡改的公证**。有过编辑后恢复的情况也未必能靠当前内容核验发现。不要把它描述成第三方审计认证。

## 安装（Mac）

关闭运行中的8504服务，然后下载 ZIP，放入 `~/Downloads`：

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_1E_GitHub_Prematch_Receipt_Patch_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/security_check.py
python -m pytest -q
```

预期：`SECURITY CHECK PASS` 和 **73 passed**（取决于你现有补丁是否完整，基础应先为 P8.1D）。

安装完先将 P8.1E **代码本身提交到 GitHub 公共仓库**。真实发布脚本故意要求当前 main 分支干净，并且本地与 `origin/main` 同步；它不会悄悄把新代码随赛事一起上传。

如果 GitHub 公共仓库尚未创建，先使用已有的 `bash scripts/publish_github.sh` 进行首次发布；若已存在，在审核 `git status` 后按你正常的 `git add / git commit / git push` 工作流推送此次代码更新。如果还有其他未完成修改，先分别处理，避免混入公开仓库。

## 单批次发布（默认不联网的 Dry Run）

### 1. 在比赛开赛前生成并保存预测

使用 Local Public P7.4 或 Portfolio owner-local（8504）生成预测，点击 `Save forecast to history`；然后在 `Saved forecasts` 点击 `Backup / export (JSON)` 下载 P7.4 归档，例如：

`~/Downloads/fma_saved_forecasts.json`

**必须先保存成功并下载 JSON。** 页面 CSV 的单条导出不适用此脚本。该 JSON 可以包含多天历史记录，但发布命令必须提供显式筛选条件。

### 2. 对同开赛时间的比赛制作预览

下面日期/时间仅是 **命令格式示范，不代表实际赛程**。请核实官方开赛时间并换算为 UTC，例如爱尔兰冬令时 UTC+0，夏令时 UTC+1。

```bash
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/publish_prematch_receipt.py \
  --archive "$HOME/Downloads/fma_saved_forecasts.json" \
  --fixture-date 2026-11-14 \
  --competition "Bundesliga" \
  --saved-after "2026-11-14T14:00:00Z" \
  --kickoff-utc "2026-11-14T14:30:00Z"
```

**每场必须是这个 UTC 时间开赛**，而且必须确实在开赛前生成预测。`--saved-after` 是额外筛选，不是开赛时间核验；若混入当天其他时间的比赛，必须用 `--record-id UUID`（可重复）精确筛选，不能将其错误发布为同一批次。必须检查预览输出中的**全部**比赛、方向及状态。

### 3. 真正发布

确认全部比赛和输入没有问题后，使用同一条命令，末尾追加 `--publish`：

```bash
python scripts/publish_prematch_receipt.py \
  --archive "$HOME/Downloads/fma_saved_forecasts.json" \
  --fixture-date 2026-11-14 \
  --competition "Bundesliga" \
  --saved-after "2026-11-14T14:00:00Z" \
  --kickoff-utc "2026-11-14T14:30:00Z" \
  --publish
```

程序将：

1. 解析严格的 P7.4 公开 JSON 格式；拒绝其它私有格式及未知字段。
2. 检查赛前本地生成时间、重复比赛、赔率和市场输出；打印将公开的记录供确认。
3. 检查 GitHub origin 是 `XiaodongYangQF/football-market-analytics-public`，仓库为 Public、Issues 已开启、代码已提交且 main 无远端分歧。
4. 要求输入 `PUBLISH` 后，**先通过 GitHub API 创建公开 Issue**；以 GitHub 返回的 `created_at` 与用户声明 kickoff 比较。若服务器时间已晚于开赛，则明确记为 `LATE_PUBLICATION`。
5. 再把内容镜像到 `data/forecast_receipts/日期_批次ID.json` 并只提交该一个文件到 GitHub main。
6. 输出公开 Issue URL 和 GitHub UTC 时间。成功后，在网站 `Pre-match archive` 查看。

**建议留至少10–15分钟发布缓冲**，不要把网络上传、人工核对和 Git 提交压缩进开赛前最后3分钟。GitHub Issue 创建失败，不能用事后 Git 提交冒充赛前公开证据。

## 成功或失败如何判断

- `ON_TIME_DECLARED`：GitHub Issue 的服务器创建时间早于你提供的 kickoff。**并不证明 kickoff 本身准确或报价可成交**。
- `LATE_PUBLICATION`：Issue 的服务器创建时间晚于/等于所提供 kickoff，只能算迟发，不得纳入前瞻性 track record。
- GitHub Issue 成功但 Git push 失败：Issue 仍是公开存在的；不要再建一份 Issue。检查 `git status`，可 `git push origin main` 推送已有 commit，或使用同一参数额外指定 `--resume-issue <Issue编号>` 尝试恢复镜像（支持赛后恢复已有 Issue）。
- 预览成功 **不等于** 已公开。只有实际收到 Github Issue URL 和其 `created_at` 才是公开发布证据。

## 每日赛果如何更新

原 P8.1D 不变：

```bash
bash scripts/publish_daily_performance.sh --dry-run
bash scripts/publish_daily_performance.sh --apply
bash scripts/publish_daily_performance.sh --push
```

`Pre-match archive` 会只读地尝试匹配 Public V2 结算记录：必须同时精确匹配赛程日期、联赛、双方球队、方向、盘口和相应赔率。如果没有唯一精确匹配，保持 `UNLINKED`，**不自动计入 ROI**。因此未来可能仍需要专门的记录 ID 对接/结果同步优化，但不会伪造历史一致性。

## 持续自检

```bash
python scripts/security_check.py
python -m pytest -q
python scripts/verify_forecast_receipts.py
```

最后一个命令会读取仓库保存的所有 Issue 链接，再通过 GitHub API 检查当前 Issue 正文与镜像数据是否一致。它不能证明未来不会被编辑，也不能检测所有“编辑后恢复原文”的历史情形。程序不会联网访问 Private 引擎。

## 本次验证状态

补丁在独立副本中通过 **73 项自动测试 + 本地安全检查 + Python 编译检查**。`--publish` 所需的 GitHub 身份验证、真实网络创建 Issue、实际比赛 kickoff 校对及 Mac 本地网页渲染，仍待你在真实环境完成；没有将模拟测试宣称为真实公开发布。
