# P8.1B · 本地赛程选择修复（2026-11-09）

**现象：** 在 8504 `Interactive forecast` 的 La Liga 下显示 `0 fixtures shown · 0 in league`。

**原因：** 公开 GitHub 模板的 `data/fixtures.csv` 只有表头，没有比赛数据（此前有意按第三方赛程授权边界留空）。

**修复：** 仅在使用 `scripts/run_owner_local.py` 并绑定 `127.0.0.1` 的 owner-local 模式下，自动**只读**使用原 Local Public 的 `deployment/public_web/data/fixtures.csv`。此文件已经带有科学模型所需 canonical team mapping，不会复制到本仓库。

## Mac 安装

先在运行 8504 的终端按 Ctrl+C，然后：

```bash
cd "$HOME/Projects/football-market-analytics-public"
mkdir -p "$HOME/fma_patch_backups/p8_1b_schedule"
cp -p fma_portfolio/p7/forecast_ui.py "$HOME/fma_patch_backups/p8_1b_schedule/"

unzip -o "$HOME/Downloads/FMA_P8_1B_Local_Schedule_Hotfix_20261109.zip" \
  -d "$HOME/Projects"

conda activate fma-portfolio
python scripts/security_check.py
python -m pytest -q
python scripts/check_owner_fixtures.py \
  --project-root "$HOME/Projects/football_market_analytics_v2_2"
```

预期：原 Local Public 数据在 ZIP 采样里覆盖 5 个联赛，合计约 1751 场；各联赛详情以你的**Mac 实际版本**为准。如果该检查提示找不到源赛程，不要在 Portfolio 内造一个假文件，应先核查原项目位置。

启动：

```bash
python scripts/run_owner_local.py \
  --science-root "$HOME/Projects/football_market_analytics" \
  --data-root "$HOME/Projects/football_market_analytics" \
  --port 8504
```

打开 `http://127.0.0.1:8504`，选择 `Interactive forecast` → `La Liga` → `Upcoming`，应出现比赛清单；也可以切换 `All` 查看历史比赛。

## 冻结与边界

- **不修改**原 Private、8502 Local Public、任何科学模型或 V2 交易策略。
- **不包含或复制**原始赛程数据；GitHub 发布仍只有 header-only 的 CSV。
- Hosted 模式仍**不**调用本地赛程或冻结引擎。Hosted 预测继续禁用。
- 本修复只验证 UI 赛程接入。要验证实际预测输出，还需要在 Mac 上用相同的 AH/OU 报价与原 Local Public 对照一次。
