"""clear-benchmark — CLEAR composite scoring benchmark framework."""
__version__ = "1.0.0"

from clear_benchmark.benchmark import (
    BenchmarkPlugin,
    BenchmarkResult,
    BenchmarkRunner,
    CLEARMetrics,
    RunAllResult,
    TierResult,
)

__all__ = [
    "BenchmarkPlugin",
    "BenchmarkResult",
    "BenchmarkRunner",
    "CLEARMetrics",
    "RunAllResult",
    "TierResult",
]
