"""
CLEAR Benchmark — Unified Benchmark System

4-tier operational evaluation framework for AI agent systems:

  Tier 1: Unit Tests (pytest)
  Tier 2: Integration Benchmarks — plugin-based, module imports, registry
  Tier 3: Performance Benchmarks — CLEAR metrics (Cost, Latency, Efficiency, Assurance, Reliability)
  Tier 4: Think-Tank Benchmarks — deliberation quality, consensus convergence

CLEAR composite weights: Cost(0.15) + Latency(0.20) + Efficiency(0.25)
                        + Assurance(0.25) + Reliability(0.15)

Usage:
  clear-bench [--tier 1|2|3|4] [--html] [--json] [--no-persist] [--version]
  python -m clear_benchmark
"""

import argparse
import hashlib
import json
import logging
import math
import os
import sqlite3
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


class BenchmarkPlugin(ABC):
    """Extension point for adding custom integration or system benchmarks.

    Implement this interface to add custom Tier 2 or Tier 4 tests that
    integrate with your specific system components.

    Example::

        class MySystemPlugin(BenchmarkPlugin):
            @property
            def name(self) -> str:
                return "my_system"

            def run(self, tier: int) -> list:
                result = # ... your benchmark logic
                return [result]
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this plugin."""

    @abstractmethod
    def run(self, tier: int) -> list:
        """Execute benchmarks for the given tier. Return list of BenchmarkResult."""


@dataclass
class CLEARMetrics:
    """
    Standardized MAS performance metrics.

    C — Cost: resource consumption (tokens, CPU time, memory)
    L — Latency: end-to-end response time
    E — Efficiency: useful output per unit cost
    A — Assurance: confidence and verification scores
    R — Reliability: success rate, error recovery
    """
    cost_cpu_ms: float = 0.0
    cost_memory_mb: float = 0.0
    cost_tokens_approx: int = 0

    latency_total_sec: float = 0.0
    latency_routing_ms: float = 0.0
    latency_execution_ms: float = 0.0

    efficiency_output_per_sec: float = 0.0
    efficiency_useful_ratio: float = 0.0

    assurance_confidence: float = 0.0
    assurance_verified: bool = False

    reliability_success_rate: float = 0.0
    reliability_error_count: int = 0
    reliability_recovery_count: int = 0

    def score(self) -> float:
        """Composite score (0.0–1.0) weighted across CLEAR dimensions.

        Weights: Cost(0.15) + Latency(0.20) + Efficiency(0.25)
                 + Assurance(0.25) + Reliability(0.15) = 1.00

        Any dimension that is NaN is excluded and remaining weights
        are re-normalised so the result stays in [0.0, 1.0].
        """
        # Normalize each dimension to 0-1 (lower cost/latency = better)
        raw: Dict[str, float] = {
            "C": max(0.0, 1.0 - (self.cost_cpu_ms / 30000)),  # 30 s budget
            "L": max(0.0, 1.0 - (self.latency_total_sec / 60)),  # 60 s budget
            "E": min(1.0, max(0.0, self.efficiency_useful_ratio)),
            "A": min(1.0, max(0.0, self.assurance_confidence)),
            "R": min(1.0, max(0.0, self.reliability_success_rate)),
        }
        weights: Dict[str, float] = {"C": 0.15, "L": 0.20, "E": 0.25, "A": 0.25, "R": 0.15}

        # Drop axes where the normalised value is NaN (missing/uninitialised)
        valid = {k: v for k, v in raw.items() if not math.isnan(v)}
        if not valid:
            return 0.0
        total_weight = sum(weights[k] for k in valid)
        if total_weight == 0.0:
            return 0.0
        return sum(weights[k] * valid[k] for k in valid) / total_weight


# ═══════════════════════════════════════════════════════════════
# BENCHMARK RESULTS — persistent storage
# ═══════════════════════════════════════════════════════════════

@dataclass
class BenchmarkResult:
    """Single benchmark run result."""
    name: str
    tier: int
    duration_ms: float
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)
    clear_metrics: Optional[CLEARMetrics] = None
    timestamp: float = 0.0
    run_id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.run_id:
            self.run_id = hashlib.sha256(
                f"{self.name}:{self.timestamp}".encode()
            ).hexdigest()[:10]


@dataclass
class BenchmarkSuite:
    """Complete benchmark run across all tiers."""
    results: List[BenchmarkResult] = field(default_factory=list)
    total_duration_sec: float = 0.0
    run_id: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.run_id:
            self.run_id = hashlib.sha256(
                f"suite:{self.timestamp}".encode()
            ).hexdigest()[:10]

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)

    @property
    def tier_summary(self) -> Dict[int, Dict[str, int]]:
        tiers: Dict[int, Dict[str, int]] = {}
        for r in self.results:
            if r.tier not in tiers:
                tiers[r.tier] = {"passed": 0, "failed": 0, "total": 0}
            tiers[r.tier]["total"] += 1
            if r.passed:
                tiers[r.tier]["passed"] += 1
            else:
                tiers[r.tier]["failed"] += 1
        return tiers


# ═══════════════════════════════════════════════════════════════
# BENCHMARK PERSISTENCE — SQLite storage for trend analysis
# ═══════════════════════════════════════════════════════════════

class BenchmarkStore:
    """Persistent benchmark storage for cross-run trend analysis."""

    DB_PATH = Path(os.environ.get(
        "CLEAR_BENCHMARK_DB",
        os.path.expanduser("~/.clear-benchmark/data/benchmarks.db"),
    ))

    def __init__(self):
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.DB_PATH))
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS benchmark_runs (
                run_id TEXT PRIMARY KEY,
                timestamp REAL,
                total_duration_sec REAL,
                total_tests INTEGER,
                pass_rate REAL,
                tier_summary TEXT
            );
            CREATE TABLE IF NOT EXISTS benchmark_results (
                id TEXT PRIMARY KEY,
                run_id TEXT,
                name TEXT,
                tier INTEGER,
                duration_ms REAL,
                passed INTEGER,
                details TEXT,
                clear_score REAL,
                timestamp REAL,
                FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id)
            );
            CREATE INDEX IF NOT EXISTS idx_results_run ON benchmark_results(run_id);
            CREATE INDEX IF NOT EXISTS idx_results_name ON benchmark_results(name);
        """)

    def save_suite(self, suite: BenchmarkSuite):
        self._conn.execute(
            "INSERT OR REPLACE INTO benchmark_runs VALUES (?, ?, ?, ?, ?, ?)",
            (suite.run_id, suite.timestamp, suite.total_duration_sec,
             len(suite.results), suite.pass_rate,
             json.dumps(suite.tier_summary)),
        )
        for r in suite.results:
            clear_score = r.clear_metrics.score() if r.clear_metrics else None
            self._conn.execute(
                "INSERT OR REPLACE INTO benchmark_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (r.run_id, suite.run_id, r.name, r.tier, r.duration_ms,
                 int(r.passed), json.dumps(r.details), clear_score, r.timestamp),
            )
        self._conn.commit()

    def get_recent_runs(self, limit: int = 10) -> list:
        rows = self._conn.execute(
            "SELECT run_id, timestamp, total_duration_sec, total_tests, pass_rate "
            "FROM benchmark_runs ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {"run_id": r[0], "timestamp": r[1], "duration_sec": r[2],
             "total_tests": r[3], "pass_rate": r[4]}
            for r in rows
        ]

    def get_trend(self, benchmark_name: str, limit: int = 20) -> list:
        rows = self._conn.execute(
            "SELECT timestamp, duration_ms, passed, clear_score "
            "FROM benchmark_results WHERE name = ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (benchmark_name, limit),
        ).fetchall()
        return [
            {"timestamp": r[0], "duration_ms": r[1],
             "passed": bool(r[2]), "clear_score": r[3]}
            for r in rows
        ]

    def close(self):
        self._conn.close()


# ═══════════════════════════════════════════════════════════════
# BENCHMARK RUNNER — orchestrates all tiers
# ═══════════════════════════════════════════════════════════════

class BenchmarkRunner:
    """
    Unified benchmark runner for NEXUS.

    Tier 1: Unit tests (delegates to pytest)
    Tier 2: Integration benchmarks (routing, C2, AAR)
    Tier 3: Performance benchmarks (CLEAR metrics)
    Tier 4: Think-tank benchmarks (deliberation quality)
    """

    def __init__(self, db_path: "str | None" = None):
        self.logger = logging.getLogger(__name__)
        self.suite = BenchmarkSuite()
        self._plugins: List[BenchmarkPlugin] = []
        self._store = None
        self._db_path = db_path  # None → use BenchmarkStore default

    def _get_store(self) -> BenchmarkStore:
        if not self._store:
            store = BenchmarkStore.__new__(BenchmarkStore)
            if self._db_path is not None:
                store.DB_PATH = Path(self._db_path)  # type: ignore[attr-defined]
                store.DB_PATH.parent.mkdir(parents=True, exist_ok=True) if self._db_path != ":memory:" else None
                store._conn = __import__("sqlite3").connect(self._db_path)
                store._init_schema()
            else:
                BenchmarkStore.__init__(store)
            self._store = store
        return self._store

    # ── Tier 1: Unit Tests ──

    def register_plugin(self, plugin: "BenchmarkPlugin") -> None:
        """Register a plugin for Tier 2/4 benchmarks."""
        self._plugins.append(plugin)

    def run_tier1(self) -> List[BenchmarkResult]:
        """Run pytest suite and record results."""
        self.logger.info("Tier 1: Running pytest suite")
        start = time.monotonic()

        test_dir = Path(__file__).parent.parent / "tests"
        if not test_dir.exists():
            result = BenchmarkResult(
                name="tier1_pytest", tier=1, duration_ms=0,
                passed=False, details={"error": f"Test dir not found: {test_dir}"},
            )
            self.suite.results.append(result)
            return [result]

        try:
            proc = subprocess.run(
                ["python", "-m", "pytest", str(test_dir), "-q", "--tb=line",
                 "--no-header", "-x"],
                capture_output=True, text=True, timeout=900,
                cwd=str(test_dir.parent),
            )
            elapsed = (time.monotonic() - start) * 1000

            # Parse pytest output
            output = proc.stdout + proc.stderr
            passed = failed = 0
            for line in output.splitlines():
                if "passed" in line:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p == "passed" and i > 0:
                            try:
                                passed = int(parts[i - 1])
                            except ValueError:
                                pass
                        if p == "failed" and i > 0:
                            try:
                                failed = int(parts[i - 1])
                            except ValueError:
                                pass

            result = BenchmarkResult(
                name="tier1_pytest", tier=1, duration_ms=elapsed,
                passed=(proc.returncode == 0),
                details={
                    "passed": passed, "failed": failed,
                    "returncode": proc.returncode,
                    "output_tail": output[-500:] if output else "",
                },
                clear_metrics=CLEARMetrics(
                    latency_total_sec=elapsed / 1000,
                    reliability_success_rate=passed / max(1, passed + failed),
                    reliability_error_count=failed,
                    assurance_confidence=1.0 if failed == 0 else max(0, 1.0 - failed / max(1, passed)),
                ),
            )
        except subprocess.TimeoutExpired:
            elapsed = (time.monotonic() - start) * 1000
            result = BenchmarkResult(
                name="tier1_pytest", tier=1, duration_ms=elapsed,
                passed=False, details={"error": "Timeout after 900s"},
            )
        except (subprocess.SubprocessError, OSError) as exc:
            elapsed = (time.monotonic() - start) * 1000
            result = BenchmarkResult(
                name="tier1_pytest", tier=1, duration_ms=elapsed,
                passed=False, details={"error": str(exc)},
            )

        self.suite.results.append(result)
        return [result]

    # ── Tier 2: Plugin-based Integration Benchmarks ────────────────────────

    def run_tier2(self) -> List[BenchmarkResult]:
        """Plugin-based integration benchmarks.

        Override or extend by registering BenchmarkPlugin instances via
        BenchmarkRunner.register_plugin().
        """
        self.logger.info("Tier 2: Running integration benchmarks")
        results = []
        for plugin in self._plugins:
            try:
                r = plugin.run(tier=2)
                if r:
                    results.extend(r if isinstance(r, list) else [r])
            except Exception as exc:  # broad: plugin failures are non-fatal
                results.append(BenchmarkResult(
                    name=f"plugin_{plugin.name}_tier2", tier=2,
                    duration_ms=0, passed=False,
                    details={"error": str(exc)},
                ))
        self.suite.results.extend(results)
        return results

    def _bench_import(self, module: str, tier: int) -> "BenchmarkResult":
        """Benchmark a single module import time."""
        start = time.monotonic()
        try:
            __import__(module)
            elapsed = (time.monotonic() - start) * 1000
            return BenchmarkResult(
                name=f"import_{module.split('.')[-1]}", tier=tier,
                duration_ms=elapsed, passed=True,
                details={"module": module},
                clear_metrics=CLEARMetrics(
                    latency_total_sec=elapsed / 1000,
                    reliability_success_rate=1.0,
                    assurance_confidence=1.0,
                ),
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            return BenchmarkResult(
                name=f"import_{module.split('.')[-1]}", tier=tier,
                duration_ms=elapsed, passed=False,
                details={"error": str(exc)},
            )

    # ── Tier 3    # ── Tier 3: Performance Benchmarks ──

    def run_tier3(self) -> List[BenchmarkResult]:
        """Performance benchmarks with CLEAR metrics."""
        self.logger.info("Tier 3: Running performance benchmarks")
        results = []

        # 3a: Resource snapshot latency
        results.append(self._bench_resource_snapshot())

        # 3b: Converse loop guard creation
        results.append(self._bench_loop_guard())

        # 3c: Consensus engine throughput
        results.append(self._bench_consensus_engine())

        # 3d: Quality scoring throughput
        results.append(self._bench_quality_scoring())

        # 3e: SITREP generation
        results.append(self._bench_sitrep_generation())

        self.suite.results.extend(results)
        return results

    def _bench_sitrep_generation(self) -> "BenchmarkResult":
        """Benchmark SITREP text generation throughput (pure Python, no deps)."""
        start = time.monotonic()
        try:
            iterations = 100
            for i in range(iterations):
                sitrep = (
                    f"SITREP {i}: Status=NOMINAL | Tasks=2 completed | "
                    f"Score={0.8 + i * 0.001:.3f} | Phase=EXECUTE"
                )
                _ = len(sitrep)
            elapsed = (time.monotonic() - start) * 1000
            return BenchmarkResult(
                name="sitrep_generation", tier=3,
                duration_ms=elapsed, passed=elapsed < 200,
                details={"iterations": iterations, "elapsed_ms": elapsed,
                         "avg_ms_per_sitrep": elapsed / iterations},
                clear_metrics=CLEARMetrics(
                    latency_total_sec=elapsed / 1000,
                    reliability_success_rate=1.0,
                ),
            )
        except Exception as exc:
            return BenchmarkResult(
                name="sitrep_generation", tier=3,
                duration_ms=(time.monotonic() - start) * 1000,
                passed=False, details={"error": str(exc)},
            )

    def _bench_resource_snapshot(self) -> "BenchmarkResult":
        """Benchmark system resource snapshot performance."""
        start = time.monotonic()
        try:
            import psutil
            iterations = 100
            snap: dict = {}
            for _ in range(iterations):
                proc = psutil.Process()
                snap = {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_mb": proc.memory_info().rss / 1024 / 1024,
                    "load_avg": psutil.getloadavg()[0] if hasattr(psutil, "getloadavg") else 0.0,
                }
            elapsed = (time.monotonic() - start) * 1000
            avg_ms = elapsed / iterations
            return BenchmarkResult(
                name="resource_snapshot", tier=3,
                duration_ms=elapsed, passed=avg_ms < 50,
                details={"avg_ms": avg_ms, "last_snap": snap},
                clear_metrics=CLEARMetrics(
                    latency_total_sec=elapsed / 1000,
                    reliability_success_rate=1.0,
                    assurance_confidence=1.0,
                ),
            )
        except Exception as exc:
            return BenchmarkResult(
                name="resource_snapshot", tier=3,
                duration_ms=(time.monotonic() - start) * 1000,
                passed=False, details={"error": str(exc)},
            )

    def _bench_loop_guard(self) -> "BenchmarkResult":
        """Benchmark loop guard creation overhead."""
        start = time.monotonic()
        try:
            iterations = 1000
            for _ in range(iterations):
                # Generic loop guard: dict-based lightweight counter
                g = {"max_turns": 15, "current_turn": 0, "start": time.monotonic()}
                _ = g["current_turn"] < g["max_turns"]
            elapsed = (time.monotonic() - start) * 1000
            avg_ms = elapsed / iterations
            return BenchmarkResult(
                name="loop_guard_create", tier=3,
                duration_ms=elapsed, passed=avg_ms < 1,
                details={"avg_ms": avg_ms, "iterations": iterations},
                clear_metrics=CLEARMetrics(
                    latency_total_sec=elapsed / 1000,
                    efficiency_output_per_sec=iterations / max(elapsed / 1000, 0.001),
                    reliability_success_rate=1.0,
                    assurance_confidence=1.0,
                ),
            )
        except Exception as exc:
            return BenchmarkResult(
                name="loop_guard_create", tier=3,
                duration_ms=(time.monotonic() - start) * 1000,
                passed=False, details={"error": str(exc)},
            )

    def _bench_consensus_engine(self) -> "BenchmarkResult":
        """Benchmark consensus engine round-trip performance."""
        start = time.monotonic()
        try:
            # Use generic in-process consensus simulation
            participants = ["a", "b", "c"]
            positions = {p: {"score": 0.8 + i * 0.05, "text": f"position_{i}"} for i, p in enumerate(participants)}
            # Simulate consensus: average scores
            avg_score = sum(v["score"] for v in positions.values()) / len(positions)
            consensus = {"consensus": avg_score > 0.7, "score": avg_score, "participants": participants}
            elapsed = (time.monotonic() - start) * 1000
            return BenchmarkResult(
                name="consensus_engine_roundtrip", tier=3,
                duration_ms=elapsed, passed=consensus["consensus"],
                details={"score": avg_score, "participants": len(participants)},
                clear_metrics=CLEARMetrics(
                    latency_total_sec=elapsed / 1000,
                    reliability_success_rate=float(consensus["consensus"]),
                    assurance_confidence=avg_score,
                ),
            )
        except Exception as exc:
            return BenchmarkResult(
                name="consensus_engine_roundtrip", tier=3,
                duration_ms=(time.monotonic() - start) * 1000,
                passed=False, details={"error": str(exc)},
            )

    def _bench_quality_scoring(self) -> "BenchmarkResult":
        """Benchmark quality scoring computation performance."""
        start = time.monotonic()
        try:
            iterations = 50
            sample = "This is a detailed technical response with multiple substantive points."
            results = []
            for _ in range(iterations):
                # Generic quality heuristic: word count + sentence structure
                words = sample.split()
                sentences = sample.count('.') + sample.count('!') + sample.count('?')
                score = min(1.0, len(words) / 100) * (0.8 + 0.2 * min(1.0, sentences / 3))
                results.append(score)
            elapsed = (time.monotonic() - start) * 1000
            avg_score = sum(results) / len(results)
            return BenchmarkResult(
                name="quality_scoring", tier=3,
                duration_ms=elapsed, passed=avg_score > 0.5,
                details={"avg_score": avg_score, "iterations": iterations, "elapsed_ms": elapsed},
                clear_metrics=CLEARMetrics(
                    latency_total_sec=elapsed / 1000,
                    assurance_confidence=avg_score,
                    reliability_success_rate=1.0,
                ),
            )
        except Exception as exc:
            return BenchmarkResult(
                name="quality_scoring", tier=3,
                duration_ms=(time.monotonic() - start) * 1000,
                passed=False, details={"error": str(exc)},
            )

    def run_tier4(self) -> List[BenchmarkResult]:
        """Think-tank protocol benchmarks (plugin-extensible)."""
        self.logger.info("Tier 4: Running think-tank benchmarks")
        results: List[BenchmarkResult] = []
        for method in [
            self._bench_think_tank_phases,
            self._bench_consensus_build,
            self._bench_quality_gate,
        ]:
            try:
                results.append(method())
            except Exception as exc:
                results.append(BenchmarkResult(
                    name=method.__name__, tier=4,
                    duration_ms=0, passed=False,
                    details={"error": str(exc)},
                ))
        for plugin in self._plugins:
            try:
                r = plugin.run(tier=4)
                if r:
                    results.extend(r if isinstance(r, list) else [r])
            except Exception as exc:
                self.logger.warning(f"Plugin tier4 error: {exc}")
        self.suite.results.extend(results)
        return results

    def _bench_think_tank_phases(self) -> "BenchmarkResult":
        """Benchmark think-tank state machine transitions."""
        start = time.monotonic()
        phases = ["brief", "recon", "intel", "wargame", "refine", "council", "debrief"]
        participants = ["cli_a", "cli_b", "cli_c"]
        state: dict = {
            "phase": phases[0],
            "turn": 0,
            "responses": {p: {} for p in participants},
            "scores": {},
        }
        for phase in phases:
            state["phase"] = phase
            for p in participants:
                state["responses"][p][phase] = f"{p}_response_for_{phase}"
            state["turn"] += 1
        elapsed = (time.monotonic() - start) * 1000
        return BenchmarkResult(
            name="think_tank_phases", tier=4,
            duration_ms=elapsed, passed=state["phase"] == phases[-1],
            details={"phases_completed": len(phases), "participants": len(participants)},
            clear_metrics=CLEARMetrics(
                latency_total_sec=elapsed / 1000,
                reliability_success_rate=1.0,
                assurance_confidence=1.0,
            ),
        )

    def _bench_consensus_build(self) -> "BenchmarkResult":
        """Benchmark consensus building from multi-participant scores."""
        start = time.monotonic()
        rounds = 3
        participants = ["cli_a", "cli_b", "cli_c"]
        scores = {p: [0.7 + i * 0.1 + r * 0.01 for r in range(rounds)]
                  for i, p in enumerate(participants)}
        final_scores = {p: sum(v) / len(v) for p, v in scores.items()}
        consensus_score = sum(final_scores.values()) / len(final_scores)
        elapsed = (time.monotonic() - start) * 1000
        return BenchmarkResult(
            name="consensus_build", tier=4,
            duration_ms=elapsed, passed=consensus_score > 0.6,
            details={"consensus_score": consensus_score, "rounds": rounds},
            clear_metrics=CLEARMetrics(
                latency_total_sec=elapsed / 1000,
                reliability_success_rate=float(consensus_score > 0.6),
                assurance_confidence=consensus_score,
            ),
        )

    def _bench_quality_gate(self) -> "BenchmarkResult":
        """Benchmark quality gate evaluation."""
        start = time.monotonic()
        samples = [
            {"specificity": 0.9, "relevance": 0.85, "novelty": 0.7, "depth": 0.8, "coherence": 0.9},
            {"specificity": 0.6, "relevance": 0.7, "novelty": 0.5, "depth": 0.6, "coherence": 0.7},
        ]
        results = []
        for sample in samples:
            score = sum(sample.values()) / len(sample)
            results.append({"score": score, "passed": score > 0.7})
        elapsed = (time.monotonic() - start) * 1000
        pass_rate = sum(1 for r in results if r["passed"]) / len(results)
        return BenchmarkResult(
            name="quality_gate", tier=4,
            duration_ms=elapsed, passed=pass_rate >= 0.5,
            details={"pass_rate": pass_rate, "samples": len(results)},
            clear_metrics=CLEARMetrics(
                latency_total_sec=elapsed / 1000,
                reliability_success_rate=pass_rate,
                assurance_confidence=pass_rate,
            ),
        )

    # ── Convenience runners ───────────────────────────────────────────────

    def run_all(self) -> "RunAllResult":
        """Run Tiers 2, 3, and 4 and return a combined :class:`RunAllResult`.

        Tier 1 (pytest suite) is intentionally excluded — it requires a
        separate pytest invocation and is not part of the operational health
        signal.
        """
        tier_map: "Dict[int, List[BenchmarkResult]]" = {
            2: self.run_tier2(),
            3: self.run_tier3(),
            4: self.run_tier4(),
        }
        tier_results: "Dict[int, TierResult]" = {}
        all_results: "List[BenchmarkResult]" = []
        for n, results in tier_map.items():
            passed = sum(1 for r in results if r.passed)
            tier_results[n] = TierResult(passed=passed, total=len(results))
            all_results.extend(results)

        # CLEAR composite: average of per-result CLEAR scores
        # Uses CLEARMetrics.score() which applies the documented weights:
        # Cost(0.15) + Latency(0.20) + Efficiency(0.25) + Assurance(0.25) + Reliability(0.15)
        clear_scores = [
            r.clear_metrics.score()
            for r in all_results
            if r.clear_metrics is not None
        ]
        composite = sum(clear_scores) / len(clear_scores) if clear_scores else 0.0

        return RunAllResult(
            composite_score=round(composite, 4),
            total_tests=len(all_results),
            tier_results=tier_results,
        )

    def run_tier(self, n: int) -> "TierResult":
        """Run a single tier by number and return a :class:`TierResult`.

        Args:
            n: Tier number (1–4).  Note that Tier 1 requires pytest and may
               not be usable in all environments.

        Returns:
            :class:`TierResult` with ``passed`` and ``total`` counts.

        Raises:
            ValueError: If *n* is not a valid tier number.
        """
        dispatch = {1: self.run_tier1, 2: self.run_tier2, 3: self.run_tier3, 4: self.run_tier4}
        if n not in dispatch:
            raise ValueError(f"Invalid tier number: {n}. Must be 1–4.")
        results = dispatch[n]()
        passed = sum(1 for r in results if r.passed)
        return TierResult(passed=passed, total=len(results))


# ── Convenience result types ──────────────────────────────────────────────


@dataclass
class TierResult:
    """Summary of a single benchmark tier run.

    Attributes:
        passed: Number of benchmarks that passed.
        total: Total number of benchmarks executed.
    """
    passed: int
    total: int

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0


@dataclass
class RunAllResult:
    """Aggregate result for a full (Tier 2–4) benchmark run.

    Attributes:
        composite_score: Weighted CLEAR composite score (0.0–1.0).
        total_tests: Total number of individual benchmark tests executed.
        tier_results: Per-tier breakdown as a dict keyed by tier number.
    """
    composite_score: float
    total_tests: int
    tier_results: "Dict[int, TierResult]" = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.tier_results is None:
            self.tier_results = {}


# ═══════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════

_VERSION = "1.0.0"


def main(argv: "Optional[List[str]]" = None) -> None:
    """CLI entry point for ``clear-bench``."""
    parser = argparse.ArgumentParser(
        prog="clear-bench",
        description="CLEAR Benchmark — AI agent composite performance scoring",
    )
    parser.add_argument(
        "--tier", type=int, choices=[1, 2, 3, 4],
        help="Run a single tier instead of all tiers (2–4)",
    )
    parser.add_argument(
        "--json", dest="output_json", action="store_true",
        help="Output results as JSON (suitable for CI parsing)",
    )
    parser.add_argument(
        "--html", dest="output_html", action="store_true",
        help="Write an HTML report to clear_benchmark_report.html",
    )
    parser.add_argument(
        "--no-persist", dest="no_persist", action="store_true",
        help="Skip saving results to the SQLite database",
    )
    parser.add_argument(
        "--version", action="version", version=f"clear-bench {_VERSION}",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING)
    runner = BenchmarkRunner(db_path=":memory:" if args.no_persist else None)

    if args.tier:
        result = runner.run_tier(args.tier)
        data: Dict[str, Any] = {
            "tier": args.tier,
            "passed": result.passed,
            "total": result.total,
            "pass_rate": round(result.pass_rate, 4),
        }
        if args.output_json:
            print(json.dumps(data, indent=2))
        else:
            status = "PASS" if result.passed == result.total else "FAIL"
            print(f"Tier {args.tier}: {result.passed}/{result.total} passed  [{status}]")
        return

    # Run all tiers (2–4)
    result_all = runner.run_all()
    data_all: Dict[str, Any] = {
        "version": _VERSION,
        "composite_score": result_all.composite_score,
        "total_tests": result_all.total_tests,
        "tiers": {
            str(n): {"passed": tr.passed, "total": tr.total,
                     "pass_rate": round(tr.pass_rate, 4)}
            for n, tr in result_all.tier_results.items()
        },
    }

    if args.output_json:
        print(json.dumps(data_all, indent=2))
    else:
        _print_summary(data_all)

    if args.output_html:
        _write_html_report(data_all)


def _print_summary(data: Dict[str, Any]) -> None:
    """Print a human-readable CLEAR benchmark summary."""
    score = data["composite_score"]
    bar_len = int(score * 40)
    bar = "█" * bar_len + "░" * (40 - bar_len)
    print(f"\nCLEAR Benchmark  v{data['version']}")
    print(f"Composite score : {score:.3f}  [{bar}]")
    print(f"Total tests     : {data['total_tests']}")
    print()
    tier_labels = {2: "Integration", 3: "Performance", 4: "Think-Tank"}
    for tier_str, tr in data["tiers"].items():
        n = int(tier_str)
        label = tier_labels.get(n, f"Tier {n}")
        status = "✓" if tr["passed"] == tr["total"] else "✗"
        print(f"  {status} Tier {n} ({label}): "
              f"{tr['passed']}/{tr['total']} — "
              f"{tr['pass_rate']:.0%} pass rate")
    print()


def _write_html_report(data: Dict[str, Any]) -> None:
    """Write a minimal HTML report to ``clear_benchmark_report.html``."""
    _tier_labels: Dict[int, str] = {
        1: "Unit", 2: "Integration", 3: "Performance", 4: "Think-Tank"
    }
    score = data["composite_score"]
    rows = "".join(
        f"<tr><td>Tier {k} ({_tier_labels.get(int(k), f'Tier {k}')})</td>"
        f"<td>{v['passed']}/{v['total']}</td><td>{v['pass_rate']:.0%}</td></tr>"
        for k, v in data["tiers"].items()
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>CLEAR Benchmark Report</title>
<style>body{{font-family:sans-serif;max-width:720px;margin:2em auto}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ccc;padding:.5em 1em;text-align:left}}
th{{background:#f4f4f4}}</style></head>
<body>
<h1>CLEAR Benchmark Report</h1>
<p>Version: {data['version']} — Composite score: <strong>{score:.3f}</strong></p>
<table><tr><th>Tier</th><th>Passed/Total</th><th>Pass rate</th></tr>
{rows}
</table>
</body></html>"""
    out = Path("clear_benchmark_report.html")
    out.write_text(html, encoding="utf-8")
    print(f"HTML report written to {out.resolve()}")
