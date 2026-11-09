# P8.1D · Daily Public Performance Publishing Pipeline

## 本次实际交付

- 每天从 `../football_market_analytics_v2_2/public_data/tracker_snapshot.json` 读取**已经发布的 Local Public 快照**，不读取 Private 账本，不调用科学模型。
- 白名单转换为 `data/public_v2.json`，只发布政策为 POST_ACTIVATION_V2 的 AH/OU 主市场及允许的公开字段。
- 统计每日累计结算数量、净收益和 ROI；独立复核全部已结算 AH/OU 的结算与 P&L。
- 防止已公开的真实预测丢失、改盘、改方向、改赔率；防止已有已结算赛果被静默改写；允许且报告同场同市场 `NO SIGNAL` 占位记录被真正的已记录信号替换。
- 更新 `data/public_release_manifest.json`，包含来源快照 SHA256、公开记录 SHA256、公开统计和发布处理时间（不包含原始文件路径、内部规则或模型）。
- 只有显式操作才会更改：默认 dry-run；`--apply` 只写两份公开 JSON；`--push` 在检查通过、GitHub remote 匹配、用户输入 `PUBLISH` 后只提交这两份数据。
- 保留旧34条信号的冻结测试样本，当前活跃数据的测试改为动态评价，不会因为新增赛果而报假错误。

## Mac 安装（仅适用于 GitHub Portfolio，原项目保持不变）

先停止本地 Portfolio 的 8504 页面。下载补丁 ZIP 到 Downloads：

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_1D_Daily_Public_Pipeline_Patch_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/security_check.py
python -m pytest -q
```

## 每天使用

```bash
# 先在 Private 完成比赛与赛果，然后使用原有程序发布到 Local Public (8502)。
# 不要把 Private runtime_data 直接用于这个脚本。

cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio

# 1. 预览（只读）
bash scripts/publish_daily_performance.sh --dry-run

# 2. 检查差异后，更新本地 GitHub Portfolio 展示文件
bash scripts/publish_daily_performance.sh --apply

# 3. 在 GitHub 仓库已经创建并确认公开内容安全后，上传两份公开数据文件
bash scripts/publish_daily_performance.sh --push
```

注意 `--push` 前必须先有已创建的公开 GitHub 仓库。如果你还没有创建，请先检查全部代码并使用之前的 `bash scripts/publish_github.sh` 创建初始仓库。如果安装补丁后已有 GitHub 仓库但源码还未提交，先将这些**代码更新单独审核和提交**，再执行数据专用的每日 `--push`。

当数据实际上没有变化时不会重复改写收益，首次生成的 manifest 是这一次公开数据处理的记录，不代表赛前已发布。

## P8.1E（后续，不在本次部署范围）

赛前公开记录使用 GitHub Issue / 后续独立写入服务保存预测 receipt，个人 X 账号分享链接；Daily Performance Pipeline 在赛后结算更新。真正公网运行模型还需要独立的受保护科学引擎服务。参见 `docs/prematch_receipts.md`。
