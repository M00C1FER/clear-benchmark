"""Demo: run all benchmark tiers and print the CLEAR composite score."""
from clear_benchmark import BenchmarkRunner

runner = BenchmarkRunner(db_path=":memory:")  # ephemeral run
results = runner.run_all()

print(f"CLEAR composite score : {results.composite_score:.3f} / 1.000")
print(f"Total tests           : {results.total_tests}")
print()
tier_labels = {2: "Integration", 3: "Performance", 4: "Think-Tank"}
for tier_num, tier_result in sorted(results.tier_results.items()):
    status = "✓" if tier_result.passed == tier_result.total else "✗"
    label = tier_labels.get(tier_num, f"Tier {tier_num}")
    print(f"  {status} Tier {tier_num} ({label}): "
          f"{tier_result.passed}/{tier_result.total} — "
          f"{tier_result.pass_rate:.0%} pass rate")
