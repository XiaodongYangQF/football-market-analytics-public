# P8.1B — 同一个网页：真实 P7 预测界面 + Public V2 历史成绩

## 0. 边界

- GitHub 项目是 **独立 Portfolio**。不覆盖 `football_market_analytics_v2_2`，也不修改 Private 或 Local Public 策略。
- 新版 `http://127.0.0.1:8504` 有 **Interactive forecast**、**Performance overview**、**Forecast ledger** 和方法说明。
- **普通启动**只显示预测输入与研究页面，但**不产生真实新预测**。真正调用原 P7 科学引擎需使用 `run_owner_local.py` 且只在 Mac 本机开放。
- GitHub/Cloud 版暂不具备真正模型的在线执行条件，不能假装已经部署了预测引擎。

## 1. 安装到已有 Portfolio 文件夹

先停止 8504 上的 Streamlit。下载本轮 ZIP：`FMA_P8_1B_Integrated_Portfolio_20261109.zip`。再运行：

```bash
cd "$HOME/Projects"
mkdir -p "$HOME/fma_env_backups"
# 如果此前旧环境被备份在仓库内，先移出去，避免误发布
find football-market-analytics-public -maxdepth 1 -type d -name '.venv_python38_backup_*' \
  -exec mv {} "$HOME/fma_env_backups/" \;
# 如果尚未用 Git 提交之前的 Portfolio，备份关键入口
cp -p football-market-analytics-public/app.py "$HOME/fma_env_backups/app_before_p8_1b.py"
unzip -o "$HOME/Downloads/FMA_P8_1B_Integrated_Portfolio_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
```

若尚未建立 Conda 环境：

```bash
conda create -n fma-portfolio python=3.11 pip -y
```

之后使用：

```bash
conda activate fma-portfolio
python --version
python -m pip install -r requirements-dev.txt
python scripts/security_check.py
python -m pytest -q
python -m pip check
```

**注意**不要在 Anaconda `base` 中执行依赖安装，避免之前 Python 3.8 的安装问题。

## 2. 启动普通 Portfolio（GitHub/云端相同安全模式）

```bash
python -m streamlit run app.py --server.address=127.0.0.1 --server.port=8504
```

打开 `http://127.0.0.1:8504`，浏览历史成绩，选择 `Interactive forecast` 查看完整 P7 报价输入流程。在这个模式下 `Generate` 会被有意禁用，防止制造虚假预测。

## 3. 在自己的 Mac 调用真正的 P7 科学引擎

原项目的 `deployment/public_web/p7_2/tools/run_local_preview.py` 之前使用过两个外部科研目录；我们继续读取原项目 `.env` 中的 `FMA_SCIENCE_ROOT` 与 `FMA_DATA_ROOT`，不把这些信息复制到 GitHub。

运行：

```bash
# 先 Ctrl+C 退出上面的普通 Streamlit
conda activate fma-portfolio
python scripts/run_owner_local.py --check
python scripts/run_owner_local.py --port 8504
```

如果预检提示缺少外部路径，可以提供路径（以下用占位符替换为你实际已有的目录）：

```bash
python scripts/run_owner_local.py --check \
  --science-root "/实际的/science/root" \
  --data-root "/实际的/data/root"
```

若原科学程序依赖原有的 Python 3.11 环境，可在启动前设置本机解释器：

```bash
export FMA_PORTFOLIO_MODEL_PYTHON="/原Private环境/bin/python"
python scripts/run_owner_local.py --port 8504
```

不要将这些本地 `export` 配置写入公开仓库。该启动器严格限制为 `127.0.0.1`；不要将其改成 `0.0.0.0` 或接入公共隧道。

**验收**：选一场之前已有完整市场输入记录的比赛，保持 AH、主 OU、固定 2.5 的赔率一致，比较本 Portfolio 与 Local Public 生成的 AH/OU 方向。若不一致，停止公开预测部署，不要修改策略使其碰巧一致。只有实际跑过同输入对比，才可以称作实盘模型输出一致性验证。

## 4. 何时推送 GitHub

发布前至少确认 `SECURITY CHECK PASS`、全部测试通过、修改过的公开文件合适，并确定公开赛程或历史数据的使用权。若还未创建 GitHub 仓库，按原有方式运行：

```bash
bash scripts/publish_github.sh
```

**这个操作只发布仓库代码/公开数据，不会把真实冻结模型变成公网服务。** 真正在线预测属于下一阶段 P8.1C，先完成安全与许可审核。


## P8.1B Local Fixture Hotfix（2026-11-09）

如果 `Interactive forecast` 显示 `0 fixtures shown · 0 in league`，说明公开仓库的
`data/fixtures.csv` 仍是刻意留空的发布模板。使用 `scripts/run_owner_local.py`
在 Mac 本机启动后，页面会直接只读加载原项目：

`$HOME/Projects/football_market_analytics_v2_2/deployment/public_web/data/fixtures.csv`

先运行 `python scripts/check_owner_fixtures.py` 检查赛程文件，再使用原有
`run_owner_local.py --science-root ... --data-root ... --port 8504` 启动。
本修复不复制第三方赛程进入 GitHub，也不修改 Private 或 Local Public。
公开云部署仍须解决赛程数据许可和科学引擎保护问题。

## P8.1D 每日业绩更新（Local Public → GitHub Public）

先在原项目中完成 Private → Local Public 的正常 Publish；不要将 Private 原始账本直接放入公开仓库。

```bash
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio

# 1) 先只读预览，不改任何文件
bash scripts/publish_daily_performance.sh --dry-run

# 2) 检查结果后，更新独立 GitHub Portfolio 的安全数据文件
bash scripts/publish_daily_performance.sh --apply

# 3) 检查变更，再在已经建立 GitHub 仓库的前提下发布
bash scripts/publish_daily_performance.sh --push
```

`--push` 仅上传通过白名单审查的 `data/public_v2.json` 和 `data/public_release_manifest.json`，并要求手动输入 `PUBLISH`；它不会复制 Private 模型/源码，也不会自动创建 GitHub 仓库。第一次公开上传整个项目仍使用既有的 `bash scripts/publish_github.sh`，需要先仔细检查仓库内容。

**注意：** 每天同步业绩的 Git 提交只能证明当天发布的数据版本，不能回溯证明预测在开赛前已公开。真正赛前发布记录（GitHub Issue + 个人 X 转发）将作为后续独立阶段实现。
