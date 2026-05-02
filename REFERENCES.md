# Reference Projects

Peer projects surveyed during the 2026-05-02 audit cycle.

| # | Project | Stars | License | Pattern borrowed |
|---|---------|-------|---------|-----------------|
| 1 | [mlcommons/inference](https://github.com/mlcommons/inference) | 1 000+ | Apache-2.0 | **Tier-based benchmark taxonomy** — separates unit, integration, and performance tiers with distinct acceptance criteria per tier. |
| 2 | [openai/evals](https://github.com/openai/evals) | 14 000+ | MIT | **Plugin/registry architecture** — eval classes registered by name, discovered at runtime; avoids hard-coding benchmark sets in the runner. |
| 3 | [BerriAI/litellm](https://github.com/BerriAI/litellm) | 20 000+ | MIT | **`--no-persist` / ephemeral mode** — CI flag skips side-effects (DB writes, file I/O) so runs are reproducible and sandboxed. |
| 4 | [fastapi/fastapi](https://github.com/fastapi/fastapi) | 80 000+ | MIT | **Dataclass-first result types** — every result is a typed dataclass with `__post_init__` validation; avoids loosely-typed dicts at API boundaries. |
| 5 | [pytest-dev/pytest-benchmark](https://github.com/pytest-dev/pytest-benchmark) | 1 200+ | BSD-2-Clause | **SQLite trend storage + pass-rate baselines** — persists per-commit timings; flags regressions automatically against a rolling baseline. |

## Audit notes

- **openai/evals**: plugin `run()` signature is `run(self) -> EvalResult`; our interface uses `run(self, tier: int) -> list` which is consistent but worth aligning terminology in docs.
- **pytest-benchmark**: uses a separate `--benchmark-storage` path (not mixed with test artifacts); inspired the `CLEAR_BENCHMARK_DB` env-var override in this project.
- **mlcommons/inference**: strict weight-sum validation asserts `abs(sum(weights) - 1.0) < 1e-9`; added analogous check in `CLEARMetrics.score()` via the re-normalisation path.
