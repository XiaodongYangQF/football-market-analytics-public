# P8.1C — Why the genuine model is not yet publicly hosted

The original P7.2 scientific worker is in the separate FMA V2.2 project and launches additional frozen research programs and reference-data files located outside that codebase. The GitHub Public repository does **not** redistribute those components. P8.1C-1 adds a loopback-only token-protected bridge and disabled-by-default authenticated hosted client; it is not a public Internet deployment.

Required before deploying a public real-time inference service:

1. **Scientific parity:** hash/version-pin P7 worker, rule evaluator, scientific adapters and read-only reference bundle; compare many identical input cases with original Mac Private/Local Public output; detect failures and resource consumption.
2. **Linux/container packaging:** create an explicitly licensed, permission-reviewed read-only science artifact. Validate every nested import and relative file reference in an isolated Linux runtime. Do not mount the owner's Mac home or Private `runtime_data`.
3. **Public security:** authenticated/rate-limited ingress, strict request budgets, service separation, isolated worker filesystem, no raw subprocess errors, constrained egress and public-only response allowlist. Check adversarial payloads and third-party package vulnerabilities.
4. **Concurrency, recovery and abuse resistance:** queue limits, worker isolation, timeouts, idempotency and restart behavior, including multiple simultaneous fixtures.
5. **Reference-data rights:** verify bookmaker/fixture/market data licenses before redistributing or exposing a derived public feed. The P8.1B GitHub repo includes only a header-only fixture placeholder.
6. **Deployment:** only then enable an explicit secure predictor API in the public frontend; keep GitHub source and Private executor in separate repositories/services.

Until these conditions are met, **anonymous/public Internet forecast generation remains disabled intentionally**. An OIDC-allowlisted pilot client exists but still requires an independently secured HTTPS model server and real deployment verification. A localhost-only gateway is available for integration testing; it is **not** a public API. See `docs/hosted_prediction.md`.
