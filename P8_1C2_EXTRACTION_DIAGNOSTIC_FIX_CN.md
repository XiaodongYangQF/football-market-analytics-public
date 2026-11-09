# P8.1C-2 私人测试输入提取诊断修复

## 用途

修复 `STOPPED: private analysis extraction could not complete safely.` 错误信息过于笼统的问题。**不放宽任何安全限制，不覆盖已有私人文件，不修改科学引擎、Private、Local Public 或预测规则。**

## 安装

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_1C2_Extraction_Diagnostic_Hotfix_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python -m pytest -q
python scripts/security_check.py
```

当前独立项目测试结果：`96 passed`，`SECURITY CHECK PASS`。

## 推荐先检查两个文件是否存在

```bash
ls -lh "$HOME/Downloads/FMA_Analysis_Export_20261108_220349.zip"
ls -lh "$HOME/Documents/fma-private-parity/cases.json"
```

其中某条 `ls` 报 `No such file` 时说明对应文件不存在。这两条检查不会修改任何文件。

## 重试提取

```bash
python scripts/build_private_parity_cases.py \
  --analysis-export "$HOME/Downloads/FMA_Analysis_Export_20261108_220349.zip" \
  --output "$HOME/Documents/fma-private-parity/cases.json" \
  --count 40
```

如果脚本停止，新增的 `REASON:` 会显示以下之一：

- `SOURCE_MISSING`：指定的 ZIP 不在该位置，寻找真实路径后修改 `--analysis-export`。
- `OUTPUT_EXISTS`：`cases.json` 已存在（安全设计禁止覆盖）。**先验证并复用**，不要直接删除。
- `OUTPUT_PARENT_MISSING`：运行 `mkdir -p "$HOME/Documents/fma-private-parity"`。
- `SOURCE_NOT_ZIP`：指向的不是 ZIP 文件。
- `NO_VALID_SNAPSHOTS`：ZIP 中没有兼容的 Private 分析快照。
- `PERMISSION_DENIED` / `IO_ERROR`：检查读写权限。

## 复用已有 cases.json

如果诊断为 `OUTPUT_EXISTS`，运行这个不修改任何文件的检查：

```bash
python - <<'PY'
from pathlib import Path
from fma_portfolio.runtime_parity import load_cases
p = Path.home() / 'Documents/fma-private-parity/cases.json'
rows = load_cases(p)
print('EXISTING CASES VALID:', len(rows))
print('LEAGUE COUNTS:', {k: sum(r['request']['league'] == k for r in rows) for k in ('E0','D1','SP1','I1','F1')})
PY
```

若输出40场、五个联赛各8场，直接使用这份 `cases.json` 进入 `verify_scientific_runtime.py preflight` 和 `baseline`，不必重复提取。

## 安全注意

`cases.json` 包含私人输入，只保存在 `$HOME/Documents/fma-private-parity/`，**不要提交到 GitHub**。不要把 `cases.json` 内容粘贴到聊天中；如需进一步排查，只贴 `STOPPED` / `REASON` 两行。
