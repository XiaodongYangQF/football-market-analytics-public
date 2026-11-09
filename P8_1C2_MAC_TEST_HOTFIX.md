# P8.1C-2 — Cross-platform macOS Test Correction

This historic patch changed only `tests/test_runtime_parity.py`, not production code, Private, Local Public, or the scientific model.

The old test assumed its runner was Linux. On macOS, `source_identity(...).interpreter.platform` returns `Darwin`; comparison with an intentionally constructed `Darwin` baseline could therefore pass unexpectedly and fail the test assertion. The corrected test explicitly simulates Darwin as the Mac baseline and Linux as the verification environment, while ensuring Darwin-to-Darwin does **not** pass the promotion gate.

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_1C2_Mac_Test_Hotfix_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python -m pytest -q tests/test_runtime_parity.py
python -m pytest -q
python scripts/security_check.py
```

The historic combined test target was 93 passing tests. Unit tests validate the *parity tooling*, not actual parity of predictions on a separately provisioned Linux machine. Both real Mac baseline and Linux verification must still be run.
