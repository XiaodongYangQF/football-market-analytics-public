# P8.1B 交付摘要：P7.4 预测入口与 GitHub Portfolio 合并

**完成范围**

- 在原 Portfolio 入口 `app.py` 加入 **Interactive forecast**，保留历史绩效、Forecast ledger、方法说明。
- 保留 P7.4 三类赛前输入：AH 盘口与双边赔率、Asian Total 主盘口与双边赔率、Fixed 2.5 双边校准赔率；只输出 AH/OU 两个市场。
- 预测结果、NO SIGNAL、1u 策略投影沿用 P7 公开契约；不修改 Private 或 Local Public 既有冻结逻辑。
- 只有点击 **Save forecast** 后才进入浏览器会话记录，支持 CSV、JSON 导出/JSON 导入；不进入官方 P&L。
- 切换比赛自动清除未保存的旧预测预览，防止误把上一场信号当成新比赛。
- 原 P7 科学引擎不进入 Github。仅在 Mac 本地 `run_owner_local.py` 通过子进程调用 Private 原 P7 的 `model_worker.py`；必须 loopback 127.0.0.1。公开托管时生成预测按钮禁用。
- 原本 P8.1A 的 Public V2 数据和收益（34条结算、+3.80u、11.18%）原封不动；不自动连接 Private/Local Public 同步。
- 此版公开 `data/fixtures.csv` 故意只有字段表头，避免未经确认转发原项目赛程资料；可在网页 Manual match 模式输入球队。

**测试**：42项在本执行环境通过；安全扫描 PASS，源码静态编译通过。真实冻结引擎的 Mac 同输入对照尚未完成（需要用户当前 Mac 的外部科研文件与配置）。当前环境未安装 Streamlit，因此无法宣称 GUI 已在真实浏览器端完整验收。

**下一步**：按 `INSTALL_CN.md` 覆盖已有 Portfolio，使用 Conda Python 3.11 验证，普通模式预览，再运行 owner-local 模式对同场输入检查模型一致性。通过后可用现有 `scripts/publish_github.sh` 创建或更新新公开仓库；网页公开可展示表单与历史表现，真正云端实时预测需要 P8.1C 的独立安全执行服务。
