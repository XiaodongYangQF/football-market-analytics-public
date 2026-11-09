# P8.1C-2 — 科学运行环境与 Mac → Linux 一致性验收

**阶段结论：代码和测试工具已完成；真实 Mac baseline 与 Linux 验证需要分别在对应机器执行。没有上线公开预测服务。**

## 1. 本阶段有什么

- `scripts/build_private_parity_cases.py`：从既有 **Private 分析导出 ZIP** 中无损读取真实模型输入（AH 主盘口、OU 亚洲主盘口、固定2.5赔率、比赛身份和日期），生成私人 JSON 测试语料。不复制或重跑模型，也不公开历史数据。
- `scripts/verify_scientific_runtime.py`：三个模式 `preflight`、`baseline`、`verify`。调用原有 P7 Worker，分别执行代码依赖核验、Mac 基准测算、Linux 同输入逐场核验。
- `fma_portfolio/runtime_parity.py`：冻结代码 SHA-256、**明确指定**的参考数据 SHA-256、科学 Python/关键第三方包版本与单场耗时；严格核对 AH/OU 预测结果。
- 额外防护：private baseline/cases/report 禁止保存在公开项目根目录；GitHub `security_check.py` 会识别并拒绝意外复制进去的私人语料。
- 测试和文档。**没有改变任何 Public V2 AH/OU 规则、Private 计算或 Local Public 8502。**

### 路线图（已经实装与未实装）

| 内容 | 进度 |
|---|---|
| 真实 Private 导出 → 多场模型输入语料 | 已实装，测试通过 |
| SHA-256 源码与显式参考数据审计 | 已实装，测试通过 |
| 原 P7 Worker 批量 Mac baseline | 已实装，等待在用户 Mac 真机执行 |
| 相同输入在 Linux 重跑并比较 | 已实装，等待独立 Linux 环境 |
| 科学环境及参考数据的**许可审核后**安全迁移 | 待落实，不能盲目全量复制 |
| 真实服务器、HTTPS、限流、OAuth、公开访客 | 未部署，不在本轮打开 |

## 2. 安装

**先完成 P8.1C-1 安装**，本补丁是覆盖更新。关闭 8504（`Ctrl+C`）。将 ZIP 放在 Downloads 后：

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_1C2_Scientific_Runtime_Parity_Patch_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/security_check.py
python -m pytest -q
```

本阶段所需科学根目录已通过你之前的 `find` 确认：

- `--project-root "$HOME/Projects/football_market_analytics_v2_2"`
- `--science-root "$HOME/Projects/football_market_analytics"`
- `--data-root "$HOME/Projects/football_market_analytics"`

如果原科学模型使用另一 Python 环境，用 `--model-python /absolute/path/to/python` 或私下设置 `FMA_PORTFOLIO_MODEL_PYTHON`。它不是新装的 UI Python 一定能替代的。

## 3. Mac：自动构建40场真实输入测试语料

```bash
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
mkdir -p "$HOME/Documents/fma-private-parity"
chmod 700 "$HOME/Documents/fma-private-parity"

python scripts/build_private_parity_cases.py \
  --analysis-export "$HOME/Downloads/FMA_Analysis_Export_20261108_220349.zip" \
  --output "$HOME/Documents/fma-private-parity/cases.json" \
  --count 40
```

导出 ZIP 文件名以上传过的2026-11-08版本为例；如果在 Mac 上另有文件名，请用其实际路径。**不要把 `cases.json` 放进 GitHub 项目。**

从此前上传的同一份 ZIP 中，我在本地进行了只读抽样：可抽出40条不同输入（五个联赛各8条），但没有在这里执行真正的科学模型。注意旧记录只是用于 **parity**，不产生新的「赛前公开」证据。

## 4. Mac：核验并生成原始科学输出 baseline

首先仅检查源文件与科学 Python：

```bash
python scripts/verify_scientific_runtime.py preflight \
  --project-root "$HOME/Projects/football_market_analytics_v2_2" \
  --science-root "$HOME/Projects/football_market_analytics" \
  --data-root "$HOME/Projects/football_market_analytics"
```

通过后运行原有模型40次，生成在 Mac 上私存的基准报告：

```bash
python scripts/verify_scientific_runtime.py baseline \
  --project-root "$HOME/Projects/football_market_analytics_v2_2" \
  --science-root "$HOME/Projects/football_market_analytics" \
  --data-root "$HOME/Projects/football_market_analytics" \
  --cases "$HOME/Documents/fma-private-parity/cases.json" \
  --baseline-file "$HOME/Documents/fma-private-parity/mac_baseline.json"
```

运行将执行真实科学计算，不是单纯的 schema 测试；如果环境缺失或有一场不能执行，**应当失败并调查**，不能虚构结果。输出文件采用 owner-only 权限创建，不覆盖既有基准。

**重要：参考数据不是自动完整冻结的。** 上面默认只计算模型代码指纹，报告会显示 `REFERENCE COVERAGE: NOT_CAPTURED`，因此不能标记为生产就绪。定位模型实际读取的**只读参考数据目录**后，给 Mac baseline 和 Linux verify 使用完全相同顺序的一个或多个 `--reference-root /absolute/path`。工具会对所声明目录中支持的参考文件计算 SHA-256，且不复制数据。建议另外创建 `mac_baseline_with_refs.json`（不会覆盖第一次基准）。仅仅指定一个不相关目录不构成数据完整性保证；必须根据实际文件访问/模型依赖确认覆盖。

## 5. Linux：独立私有环境重复运行

在**你有权限、经过安全与数据许可审核的私有 Linux 主机**上：

1. 安装同一 `football-market-analytics-public` 公开工具代码，但任何私人资源都留在仓库之外。
2. 使用**私人传输渠道**把经过逐项许可审查、冻结的 V2.2 Worker、科学程序、P1/P2 适配器与必要参考数据放到各自只读目录。**不得**把整个 Mac Home、数据库、私密 `.env`、赔率原始账本或密钥直接拷贝进去。
3. 建立独立 Linux Python 环境，按 `mac_baseline.json` 中的 `interpreter` 版本安装经核验的依赖。科学环境和 UI 环境可不同，运行时通过 `--model-python` 指定前者。
4. 通过私人传输渠道把 `cases.json` 与 `mac_baseline_with_refs.json` 放到 Linux **仓库外**目录（建议权限0700），不要放进网页可访问目录。
5. 重复执行 `preflight` 和 `verify`；示例：

```bash
python scripts/verify_scientific_runtime.py verify \
  --project-root /srv/fma/private-project \
  --science-root /srv/fma/science \
  --data-root /srv/fma/data \
  --model-python /srv/fma/science-venv/bin/python \
  --reference-root /srv/fma/approved-reference-data \
  --cases /srv/fma/private-evidence/cases.json \
  --baseline-file /srv/fma/private-evidence/mac_baseline_with_refs.json \
  --report-file /srv/fma/private-evidence/linux_parity_report.json
```

所有 Linux 路径是**部署示例**，并非已经创建。多个 `--reference-root` 的数量、顺序和内容必须与 Mac 基准的声明一致。可重复执行验证；报告文件采用“不允许覆盖”策略，每次新建不同文件名即可。

## 6. 验收标准

程序提供两个不同判断，不能混为一谈：

- **PARITY PASS**：当前的每个真实模型输出与基准严格相同，声明的代码和参考数据哈希相同，各单场运行时间不超过所配置上限。若没有参考目录、只在 Mac 跑，仍可能得到这个局部的 PASS。
- **PROMOTION-CANDIDATE GATE PASS**：除上面的逐场一致外，还要求至少20场、覆盖至少3个联赛、AH/OU 都出现预测与 NO SIGNAL；基准确实是在 macOS 运行且复核在 Linux 运行；Python 与主要依赖包版本一致；明确声明的参考数据哈希匹配。

即使晋级 `PROMOTION-CANDIDATE`，也**不能仅凭它开放公网**：还需要确认参考数据覆盖完全、测试峰值内存、连续高峰吞吐、磁盘只读性、系统服务权限、网络访问控制、用户身份验证与定价数据许可。它是技术验收必要条件，不是充分条件。

### 如果发生 FAIL

- `scientific_source=False`：原模型代码或适配器不一致；不能直接放行。
- `declared_reference_data=False`：参考数据不同，需检查快照、目录映射及迁移过程。
- `PARITY FAIL`：至少一场 AH/OU 预测不同，或超时，当前环境不能晋级。
- `coverage_gate=INCOMPLETE`：样本过少或结果类型覆盖不足，需追加之前保存的真实输入。
- `scientific_dependency_versions_equal=False`：仅表示环境版本有漂移；即使输出全对也不直接晋级。

## 7. 与 P8.1D / P8.1E 的关系

- P8.1D Daily Performance 继续从 Local Public 导出公共结算数据。
- P8.1E 继续由 GitHub Issue 形成真正**开赛前**的公开存证。
- Mac/Linux 科学一致性验证与上述记录流程完全独立，不会更改 ROI、历史预测或交易规则。
- 不会自动发布你的个人 X，也不会自动把任何预测录入 GitHub Issue。

**下一关键实际验收：请先在 Mac 生成真实40场的 `cases.json` 与 `mac_baseline.json`，报告成功后再着手 Linux 私有服务迁移。**
