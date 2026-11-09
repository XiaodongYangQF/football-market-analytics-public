# P8.2D — GitHub / Streamlit 公开展示优化（2026-11-09）

这是一份**仅修改公开 Portfolio** 的小补丁。不会修改 Private、Local Public (8502)、科学模型、OU/AH 规则、已经公布的 P&L、公开 JSON 或任何私人测试文件。

## 更新内容

1. 公开网页首次打开时默认进入 `Performance overview`，导航顺序为 Performance → Pre-match archive → Forecast ledger → Methodology → Interactive forecast。
2. 公开网页侧边栏增加 `Source code & public record history` GitHub 链接。
3. GitHub README 顶部增加正式上线的 Streamlit URL、GitHub URL、预留的 GitHub Issues 入口，同时显著说明云端真实预测**尚未开放**。
4. 增加3项无需导入 Streamlit 的回归测试，确保默认首页和公开说明不会倒退。

## Mac 安装

确保 ZIP 文件已保存到 `~/Downloads/FMA_P8_2D_Public_Presentation_Patch_20261109.zip`。

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_2D_Public_Presentation_Patch_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/security_check.py
python -m pytest -q
```

完整安装 P8.1C-2E 后应显示 **139 passed**。运行前后检查 `git status --short`，保证没有私人文件或意外改动。

## 将展示改动提交到 GitHub

```bash
cd "$HOME/Projects/football-market-analytics-public"
git status --short
git add -- app.py README.md tests/test_public_homepage.py P8_2D_PUBLIC_LAUNCH_CN.md P8_2E_FIRST_RECEIPT_ACCEPTANCE_CN.md
git diff --cached --name-only
git diff --cached --stat
git commit -m "portfolio: make performance the public landing page"
git push origin main
```

仅提交列出的5个安全文件，不要使用 `git add .`。如果存在与其他开发工作冲突的已暂存改动，先处理，再提交。Streamlit Community Cloud 会跟踪 GitHub main 分支的修改（如有缓存，刷新页面）。

## 设置 GitHub 仓库首页的 Website / About

本步只更新 GitHub 仓库元数据，不修改 Private 或模型：

```bash
gh repo edit XiaodongYangQF/football-market-analytics-public \
  --homepage "https://football-market-analytics.streamlit.app/" \
  --description "Public football AH/OU research: simulated performance and auditable pre-match forecast receipts"

gh repo view XiaodongYangQF/football-market-analytics-public \
  --json url,isPrivate,homepageUrl,description
```

如果当前 GitHub CLI 的 `--json` 字段不支持某个字段，可使用 GitHub 仓库页面右侧 About 的齿轮图标手动设置 Website。

## 公网验收

- 在**新建无痕窗口**中打开 `https://football-market-analytics.streamlit.app/`。
- 首先显示 `Performance overview`，而不是无法在线执行模型的 `Interactive forecast`。
- Performance 的结算数量、P&L 和 ROI 仍与此前发布的 Public V2 数据一致。
- `Pre-match archive` 在首次正式赛前存证前显示空状态，不能把历史赛后回放标记为赛前公开记录。
- `Interactive forecast` 仍不允许一般访问者调用 Private 引擎。
- GitHub README 顶部的 Live app 链接和仓库 About Website 都能进入公网应用。

后续第一份真实赛前 Issue 的发布操作，按 `P8_2E_FIRST_RECEIPT_ACCEPTANCE_CN.md` 执行。
