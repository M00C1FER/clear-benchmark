# CLEAR Benchmark

> Composite scoring across five existing benchmark axes — Cost, Latency, Efficiency, Assurance, Reliability — under a single reproducible 4-tier test architecture, persisted to SQLite, plugin-extensible.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20WSL%20%7C%20Termux-lightgrey)](install.sh)

## What's actually new here, what isn't

The five axes of CLEAR are **not new**. Each maps to a layer that already has dominant public benchmarks — HELM, Artificial Analysis, LMSys Arena, TruthfulQA, Vectara HHEM — which CLEAR composes rather than replaces. The contribution is **the 4-tier pluggable test architecture and the composite scoring**, not the dimensions themselves.

| CLEAR axis | What it measures | Established benchmarks the axis maps to |
|---|---|---|
| **Cost** | Token / API cost per operation | OpenRouter cost-per-task tables; Helicone / Langsmith spend dashboards |
| **Latency** | p50/p95 response time, time-to-first-token | [Artificial Analysis](https://artificialanalysis.ai) latency tables |
| **Efficiency** | Quality-per-token, quality-per-dollar | LMSys Chatbot Arena (cost-normalized leaderboards); [HELM](https://crfm.stanford.edu/helm/) efficiency |
| **Assurance** | Hallucination resistance, factual correctness | [TruthfulQA](https://github.com/sylinrl/TruthfulQA), [Vectara HHEM](https://huggingface.co/vectara/hallucination_evaluation_model) |
| **Reliability** | Run-to-run consistency / variance | Less-served by existing benchmarks; CLEAR's main contribution |

Reliability is the axis the public ecosystem under-serves — most leaderboards report single-run scores. CLEAR weights it 0.15 in the composite and treats run-to-run variance as a first-class metric.

## What It Does

Evaluating AI agent pipelines requires more than pass/fail. CLEAR Benchmark measures five dimensions of system health in a single composite score (0.0–1.0), persists results in SQLite for trend analysis, and generates HTML reports. A plugin API lets you add custom benchmarks without modifying core code.

**CLEAR dimensions:**
| Dimension | Weight | Measures |
|-----------|--------|---------|
| Cost | 0.15 | Token or API cost per operation |
| Latency | 0.20 | p50/p95 response time |
| Efficiency | 0.25 | Resource utilization (CPU/mem) |
| Assurance | 0.25 | Correctness, assertion pass rate |
| Reliability | 0.15 | Retry rate, failure recovery |

**Benchmark tiers:**
- **Tier 1** — Unit tests (plugin correctness)
- **Tier 2** — Integration (import chains, registry, config loading)
- **Tier 3** — Performance (latency, resource snapshot, CLEAR metrics)
- **Tier 4** — State machine (think-tank phases, consensus build, quality gate)

## Quick Start

```bash
bash install.sh
clear-bench          # Run all tiers
clear-bench --tier 3 # Single tier
clear-bench --json   # JSON output for CI
clear-bench --html   # HTML report
```

## Installation

| Platform | Method |
|----------|--------|
| Debian / Ubuntu / WSL | `bash install.sh` (uses apt-get) |
| Arch / Manjaro | `bash install.sh` (uses pacman) |
| Fedora / RHEL / Rocky | `bash install.sh` (uses dnf) |
| Alpine | `bash install.sh` (uses apk; best-effort) |
| Termux (Android) | `bash install.sh` (no sudo) |
| pip | `pip install .` |

```bash
git clone https://github.com/M00C1FER/clear-benchmark
cd clear-benchmark
bash install.sh
```

## Usage

```python
from clear_benchmark import BenchmarkRunner, BenchmarkPlugin

# Run all built-in tiers
runner = BenchmarkRunner()
results = runner.run_all()
print(f"CLEAR score: {results.composite_score:.3f}")
print(f"Tier 3 pass rate: {results.tier_results[3].pass_rate:.1%}")

# Write a custom benchmark plugin
class MyLatencyPlugin(BenchmarkPlugin):

    @property
    def name(self) -> str:
        return "my_api_latency"

    def run(self, tier: int) -> list:
        import time
        start = time.perf_counter()
        # ... call your API ...
        elapsed_ms = (time.perf_counter() - start) * 1000
        from clear_benchmark import BenchmarkResult
        return [BenchmarkResult(
            name=self.name, tier=tier,
            duration_ms=elapsed_ms, passed=elapsed_ms < 2000,
        )]

runner.register_plugin(MyLatencyPlugin())
results = runner.run_tier(3)
```

## Architecture (MOSA)

```
clear-benchmark/
├── src/clear_benchmark/
│   ├── benchmark.py       # Tier runner + CLEAR scoring
│   └── __init__.py
├── install.sh             # Cross-platform wizard
├── examples/
│   ├── demo.py            # All-tier run with report
│   └── custom_plugin.py   # Plugin authoring example
└── TOOLS.md
```

## Results Persistence

All runs saved to SQLite (default: `~/.clear-benchmark/data/benchmarks.db`, override with `CLEAR_BENCHMARK_DB`):

```sql
SELECT run_date, composite_score, tier3_latency_p50_ms
FROM benchmark_runs
ORDER BY run_date DESC LIMIT 10;
```

## Cross-Platform Notes

- **Linux (Debian/Ubuntu/Arch/Fedora/Alpine):** `psutil` resource monitoring fully supported; `install.sh` auto-detects `apt-get`, `dnf`, `pacman`, and `apk`
- **WSL2 (Ubuntu base):** Identical to Linux; no `/sys/firmware/efi` assumptions made
- **Termux (Android arm64):** `psutil` supported; `install.sh` uses `pkg` (no sudo); `getloadavg` falls back gracefully
- **CI:** `clear-bench --json --no-persist` for ephemeral runs

## License

[MIT](LICENSE)
