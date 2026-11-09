# P8.1C-2 — macOS 跨平台测试修复

本补丁仅替换 `tests/test_runtime_parity.py`，不修改任何生产代码、Private、Local Public 或科学模型。

## 原因

旧测试假设测试机运行 Linux。Mac 上 `source_identity(...).interpreter.platform` 为 `Darwin`，与人为构造的 `Darwin` baseline 相同，故原断言误失败。

## 安装

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_1C2_Mac_Test_Hotfix_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python -m pytest -q tests/test_runtime_parity.py
python -m pytest -q
python scripts/security_check.py
```

修复后测试显式模拟 Mac 基准 (`Darwin`) 与 Linux 验证端 (`Linux`)，并单独检验 `Darwin`→`Darwin` 不能通过 promotion gate。完整测试预期为93 passed。

注意：测试通过只是工具自身正确性的验证；**尚不代表真实 Linux 服务器预测已与 Mac 预测一致**。真实 Mac baseline 和 Linux verify 仍需要另行执行。
