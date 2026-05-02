"""Demo: run all benchmark tiers and print the CLEAR composite score."""
from clear_benchmark import BenchmarkRunner

runner = BenchmarkRunner(db_path=":memory:")  # ephemeral run
results = runner.run_all()

print(f"CLEAR composite score : {results.composite_score:.3f} / 1.000")
print(f"Total tests           : {results.total_tests}")
print(f"Passed                : {results.passed_tests}")
print(f"Failed                : {results.failed_tests}")
print()
for tier_name, tier_result in results.tiers.items():
    status = "✓" if tier_result.all_pass else "✗"
    print(f"  {status} Tier {tier_result.tier_number}: {tier_result.passed}/{tier_result.total} tests — {tier_result.label}")
