# P8.1C-2 · Linux scientific runtime migration gates

Public repository contains **only tooling**, no private science code or private market inputs.

1. Prepare a reviewed inventory of private model code, nested scientific imports, read-only coefficients/reference data, executable dependencies, and the legal right to deploy them on a private host. Source SHA-256 under selected subtrees is collected by `scripts/verify_scientific_runtime.py`; complete reference-data coverage must be confirmed separately, because only explicitly declared `--reference-root` directories are hashed.
2. Keep the scientific runtime **outside** the GitHub checkout, in permission-restricted folders. No automatic rsync, tarball, Docker build context, credential migration, or firewall modification is performed by this patch.
3. Extract real saved Private analysis inputs to a **private** parity corpus. Compute the baseline on the original Mac worker. Transfer only the approved scientific runtime and private comparison evidence using a secure channel.
4. Verify exact source and reference hashes, pinned scientific Python/package versions, and full AH/OU projection parity for 20+ saved cases across 3+ leagues with forecast and no-signal states in both markets. Check missing/extra cases and request-content hashes.
5. Separately check normal and worst-case compute time, peak RAM, process startup under load, nested writes/read-only mounts, restart resilience, quotas and simultaneous visitor handling. The Python parity tool measures per-case **wall time only**; it does not certify memory or throughput.
6. Harden independent authenticated HTTPS ingress, durable account/IP quotas, identity-provider verification, container/systemd privileges, network egress policy, resource limits, logs without secrets, and commercial data licensing. Only then consider the hosted allowlisted pilot. **Never expose `127.0.0.1:8765` directly through a public port or naive tunnel.**
7. Anonymous access requires a separate security/cost/legal review; keep `FMA_HOSTED_FORECAST_ENABLED=0` unless explicitly ready.

Parity evidence formats:
- `FMA_PRIVATE_RUNTIME_PARITY_CASES_V1`: exact model input contract, private only.
- `FMA_PRIVATE_RUNTIME_PARITY_BASELINE_V1`: Mac outputs, runtime manifests and interpreter metadata, private only.
- `FMA_PRIVATE_RUNTIME_PARITY_REPORT_V1`: Linux comparison, private only.

Outputs are never represented as prospective GitHub Issue receipts. Git commit timestamps or test-fixture dates have no evidentiary role in cross-platform model equality.
