# CLEAR Benchmark

> Composite AI agent performance scoring: Cost, Latency, Efficiency, Assurance, Reliability — in one reproducible benchmark suite.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20WSL%20%7C%20Termux-lightgrey)](install.sh)

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
| Linux / WSL | `bash install.sh` |
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
print(f"Tier 3 pass rate: {results.tier3.pass_rate:.1%}")

# Write a custom benchmark plugin
class MyLatencyPlugin(BenchmarkPlugin):
    name = "my_api_latency"
    tier = 3

    def run(self) -> dict:
        import time
        start = time.perf_counter()
        # ... call your API ...
        return {"latency_ms": (time.perf_counter() - start) * 1000}

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

All runs saved to SQLite (default: `~/.local/share/clear-benchmark/benchmarks.db`):

```sql
SELECT run_date, composite_score, tier3_latency_p50_ms
FROM benchmark_runs
ORDER BY run_date DESC LIMIT 10;
```

## Cross-Platform Notes

- **Linux/WSL:** `psutil` resource monitoring fully supported
- **Termux:** `psutil` supported; battery metrics available
- **CI:** `clear-bench --json` + `--no-persist` for ephemeral runs

## License

[MIT](LICENSE)
