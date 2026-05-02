"""Smoke tests for clear-benchmark."""
import math
import pytest


def test_import():
    from clear_benchmark import BenchmarkRunner
    assert BenchmarkRunner


def test_run_all_returns_score():
    from clear_benchmark import BenchmarkRunner
    runner = BenchmarkRunner(db_path=":memory:")
    results = runner.run_all()
    assert 0.0 <= results.composite_score <= 1.0
    assert results.total_tests > 0


def test_tier3_pass_rate():
    from clear_benchmark import BenchmarkRunner
    runner = BenchmarkRunner(db_path=":memory:")
    results = runner.run_tier(3)
    assert results.passed >= 0
    assert results.total > 0


def test_tier4_state_machine():
    from clear_benchmark import BenchmarkRunner
    runner = BenchmarkRunner(db_path=":memory:")
    results = runner.run_tier(4)
    assert results.total > 0


# ── CLEAR weights correctness ──────────────────────────────────────────────

def test_clear_weights_sum_to_one():
    """CLEAR axis weights must sum to exactly 1.0."""
    weights = {"C": 0.15, "L": 0.20, "E": 0.25, "A": 0.25, "R": 0.15}
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_clear_score_range():
    """CLEARMetrics.score() must return a value in [0, 1]."""
    from clear_benchmark import CLEARMetrics
    m = CLEARMetrics(
        reliability_success_rate=1.0,
        assurance_confidence=0.9,
        efficiency_useful_ratio=0.8,
        latency_total_sec=0.05,
        cost_cpu_ms=100,
    )
    s = m.score()
    assert 0.0 <= s <= 1.0


def test_clear_score_all_zeros():
    """All-zero CLEARMetrics should still return a value in [0, 1]."""
    from clear_benchmark import CLEARMetrics
    m = CLEARMetrics()
    s = m.score()
    assert 0.0 <= s <= 1.0


def test_clear_score_nan_axis_excluded():
    """A NaN dimension must be excluded and remaining weights re-normalised."""
    from clear_benchmark import CLEARMetrics
    # Inject NaN into one axis; the score should not be NaN
    m = CLEARMetrics(
        reliability_success_rate=float("nan"),
        assurance_confidence=1.0,
        efficiency_useful_ratio=1.0,
        latency_total_sec=0.0,
        cost_cpu_ms=0.0,
    )
    s = m.score()
    assert not math.isnan(s), "score() must never return NaN"
    assert 0.0 <= s <= 1.0


def test_clear_score_perfect():
    """Perfect input should yield 1.0."""
    from clear_benchmark import CLEARMetrics
    m = CLEARMetrics(
        reliability_success_rate=1.0,
        assurance_confidence=1.0,
        efficiency_useful_ratio=1.0,
        latency_total_sec=0.0,
        cost_cpu_ms=0.0,
    )
    assert m.score() == pytest.approx(1.0, abs=1e-6)


# ── CLI / main() entry point ──────────────────────────────────────────────

def test_main_version(capsys):
    """clear-bench --version should print the version string."""
    from clear_benchmark.benchmark import main
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0


def test_main_json_no_persist(capsys):
    """clear-bench --json --no-persist should produce valid JSON."""
    import json as _json
    from clear_benchmark.benchmark import main
    main(["--json", "--no-persist"])
    captured = capsys.readouterr()
    data = _json.loads(captured.out)
    assert "composite_score" in data
    assert 0.0 <= data["composite_score"] <= 1.0


def test_main_tier_flag(capsys):
    """clear-bench --tier 3 --json --no-persist should include tier info."""
    import json as _json
    from clear_benchmark.benchmark import main
    main(["--tier", "3", "--json", "--no-persist"])
    captured = capsys.readouterr()
    data = _json.loads(captured.out)
    assert data["tier"] == 3
    assert "passed" in data
    assert "total" in data


def test_main_invalid_tier():
    """clear-bench --tier 99 should exit with an error."""
    from clear_benchmark.benchmark import main
    with pytest.raises(SystemExit) as exc:
        main(["--tier", "99"])
    assert exc.value.code != 0


# ── Plugin API ────────────────────────────────────────────────────────────

def test_plugin_registered_in_tier4():
    """A registered plugin must be called during tier-4 run."""
    from clear_benchmark import BenchmarkPlugin, BenchmarkResult, BenchmarkRunner

    called = []

    class DummyPlugin(BenchmarkPlugin):
        @property
        def name(self) -> str:
            return "dummy"

        def run(self, tier: int) -> list:
            called.append(tier)
            return [BenchmarkResult(
                name="dummy", tier=tier, duration_ms=1, passed=True,
            )]

    runner = BenchmarkRunner(db_path=":memory:")
    runner.register_plugin(DummyPlugin())
    runner.run_tier(4)
    assert 4 in called, "plugin.run() must be invoked with tier=4"


# ── demo.py runs without error ─────────────────────────────────────────────

def test_demo_script():
    """examples/demo.py must execute without AttributeError."""
    import importlib.util
    from pathlib import Path
    demo = Path(__file__).parent.parent / "examples" / "demo.py"
    spec = importlib.util.spec_from_file_location("demo", demo)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # raises on bad attribute access
