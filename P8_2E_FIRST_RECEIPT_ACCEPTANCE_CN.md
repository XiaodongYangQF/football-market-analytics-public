# P8.2E — 第一份真实 GitHub 赛前预测存证：安全操作清单

**状态：尚未实际发布。** 本清单是第一次 live acceptance 的流程，不应拿历史已开赛比赛冒充赛前公开预测。模型的 Private/Local Public 规则保持不变。

## 0. GitHub 环境检查（只读）

在已经完成 P8.2D 的 Git 提交与推送后运行：

```bash
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
git status -sb
gh auth status
gh api repos/XiaodongYangQF/football-market-analytics-public \
  --jq '{private,has_issues,default_branch,archived}'
```

期望 `private=false`、`has_issues=true`、`default_branch=main`、`archived=false`，并且工作区无意外未提交修改。如 Issues 未启用，先在 GitHub 仓库 Settings → General → Features 中开启，或经你确认后执行 `gh repo edit XiaodongYangQF/football-market-analytics-public --enable-issues`。

## 1. 选择真正尚未开赛、符合资格的比赛

- 核对准确开赛时间（**UTC**）、联赛、主队、客队。项目赛程快照只含日期，不能据此推导实际开赛钟点。
- 2026–27赛季升班马或不明球队属于 `INELIGIBLE` / `UNVERIFIED`，不得强行生成正式模型预测。
- 同一个 GitHub Issue 批次只能包含**确实相同 UTC 开赛时间**的比赛；不同联赛或比赛时间必须分别发布。
- 最好在开赛前预留足够时间进行模型计算、数据检查、GitHub Issue 创建与 Git push；本地模型生成时间不能替代 GitHub 服务器发布时间。

## 2. 保存真实模型输出并导出 P7.4 JSON

在现有 Owner-local / Local Public 流程中使用真正冻结的模型；在预测页面按 Save forecast，将记录保存到会话，然后通过 Backup / export (JSON) 保存原始 P7.4 archive 到私人 `Downloads` 或其他 Mac 私人位置。没有成功计算模型、没有保存预测时不发布假记录。

**不要**把整个 Private 分析 ZIP、P1/P2 数据、模型日志或私人 parity case 文件提交 GitHub。

## 3. 先检查导出里将被选中的记录 ID（只输出比赛信息）

把下面 `ARCHIVE` 改成你实际导出的 JSON 文件路径：

```bash
ARCHIVE="$HOME/Downloads/实际导出的P7_4预测归档.json"
python - "$ARCHIVE" <<'PY'
from pathlib import Path
import sys
from fma_portfolio.p7.saved_forecasts import parse_archive
for row in parse_archive(Path(sys.argv[1]).read_bytes()):
    print(row['record_id'], row['fixture_date'], row['competition'],
          row['home_team'], 'vs', row['away_team'], row['saved_at_utc'])
PY
```

确认准备发布的比赛与真正的开赛时间一致。建议用一个或多个 `--record-id` 精确指定批次，不依赖整个归档自动全选。

## 4. 必须先 dry-run；人工核对输入与方向

以下是**命令模板**，并非一场实际比赛。请替换真实的 ID、比赛日期和**经核查**的 UTC 开赛时间。

```bash
python scripts/publish_prematch_receipt.py \
  --archive "$ARCHIVE" \
  --record-id "真正的record_id" \
  --kickoff-utc "YYYY-MM-DDTHH:MM:SSZ" \
  --kickoff-basis "Official fixture kickoff checked manually" \
  --quote-source "Your actual quote source and observed timestamp"
```

dry-run 会打印即将公开的全部主客队、AH/OU 盘口、双方赔率、固定2.5赔率、方向和模型生成时间。**在发布前人工逐项复核**；例如14:27分析14:30比赛，留给上传与网络响应的时间非常紧张，不应在临近开赛时绕过检查。

## 5. 正式发布（不可用于赛后补录）

将与 dry-run 完全相同的命令追加 `--publish`，在 Terminal 核对后亲自输入 `PUBLISH`。脚本会首先建立公开 GitHub Issue，使用 GitHub `created_at` 与用户声明的 UTC 开赛时刻比较，并将同一批次的 JSON 镜像提交到 GitHub main。

成功后会返回 `PUBLIC ISSUE`、`GITHUB CREATED (UTC)`、`DECLARED KICKOFF`、`RESULT` 及 `MIRRORED`。

**验收标准：** `RESULT: ON_TIME_DECLARED`；公开 Issue 的正文和 SHA-256 与镜像文件一致；Streamlit `Pre-match archive` 能显示相应比赛及原始 Issue 链接。该状态依赖于用户声明的开赛时刻，**不构成独立官方开球时间或赔率可执行性的认证**。

如 Issue 已经创建，但 Git push 失败，**不要再创建第二条 Issue**。参照现有 `docs/prematch_receipts.md` 使用 `--resume-issue N` 或恢复原有已提交镜像。

## 6. 赛后再更新 Daily Performance

按现有 P8.1D 流程更新 Local Public 和 GitHub Public 的模拟结算；原始 Issue 不覆盖为赛果。公开网页只有在比赛、盘口、方向、赔率等字段严格唯一匹配时才显示对应结算；找不到匹配显示 `UNLINKED`，不人为补齐。

## 重要研究边界

- GitHub Issue 可被编辑或删除，哈希 + 镜像 + 提交历史提供**可核查性**，不是不可篡改公证。
- 公开时间由 GitHub 服务器的 `created_at` 提供；本地 Mac 时间和 Git commit 作者日期不能独立证明事前公开。
- 赛后从历史赛前赔率重放的预测不得列入前瞻性存证样本。
- `INELIGIBLE`、`NO SIGNAL`、`WORKER ERROR` 是不同的状态；不要把升班马排除记为无交易机会。
- 访客自行请求的预测（将来开放在线 API 后）不会自动计入官方策略 Track Record。
