"""Smoke tests for clear-benchmark."""
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
