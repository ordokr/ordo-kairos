"""Behaviour check: does the decision core actually produce a decision?

Nothing here is a claim about a real market. Sections 1, 4 and 5 are pure functions of the cost and
economics models, section 2 reproduces a known mechanism on deterministic synthetic data, and
section 3 is published arithmetic. Section 5 uses published measurements as inputs. No forecast and
no edge is being asserted anywhere.

    python demo.py
"""

from __future__ import annotations

from kairos.baseline import MarketBaseline, SettlementTerms
from kairos.calibration import IsotonicCalibrator
from kairos.costs import CostModel
from kairos.economics import (
    StrategyEconomics,
    effective_sample_size,
    rank_strategies,
    sufficient_evidence,
)
from kairos.score import (
    brier_score,
    deflated_sharpe_ratio,
    expected_max_sharpe,
    log_score,
    min_backtest_length,
    skill_score,
)
from kairos.sizing import RiskLimits, Side, size_position

RULE = "=" * 78
costs = CostModel()
limits = RiskLimits()


def section(n: int, title: str) -> None:
    print(f"\n{RULE}\n{n}. {title}\n{RULE}")


section(1, "REQUIRED EDGE AFTER COSTS  (probability points over the market mid)")
horizons = [1, 7, 30, 90, 365]
print(f"{'mid':>6} | " + " | ".join(f"{d:>5}d" for d in horizons))
print("-" * 46)
for mid in (0.10, 0.25, 0.50, 0.75, 0.90):
    cells = [f"{(costs.effective_yes_cost(mid, d) - mid) * 100:5.1f}" for d in horizons]
    print(f"{mid:>6.2f} | " + " | ".join(f"{c}pp" for c in cells))
print(f"\nNo-trade band at 0.50 / 30d: {costs.round_trip_drag(0.50, 30) * 100:.1f} points.")


section(2, "q_ref - THE PRICE IS NOT THE PROBABILITY")
print("(a) Settlement discount (Gebele & Matthes 2026): capital locked until resolution")
for days in (30, 180, 365):
    terms = SettlementTerms(days_to_settlement=float(days))
    print(f"    a 0.95 quote at {days:>3}d implies probability {terms.undiscount(0.95):.4f}")

print("\n(b) Domain compression (Le 2026): market compressed toward 0.5 in logit space")
import math

true_ps = [0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9]
prices: list[float] = []
outcomes: list[float] = []
for tp in true_ps:
    q = 1.0 / (1.0 + math.exp(-0.6 * math.log(tp / (1 - tp))))
    prices.extend([q] * 1000)
    outcomes.extend([1.0] * round(tp * 1000) + [0.0] * (1000 - round(tp * 1000)))

base = MarketBaseline.fit(prices, outcomes, [30.0] * len(prices))
print(f"    fitted recalibration slope {base.recalibration.slope:.3f} "
      f"(1.0 = no correction needed)")
for q in (0.20, 0.40, 0.60, 0.80):
    print(f"    quoted {q:.2f}  ->  q_ref {base.fair_probability(q, 30.0):.4f}")

q_star = base.baseline_series(prices, [30.0] * len(prices))
print(f"\n    [IN-SAMPLE - NOT EVIDENCE] The baseline above was fitted on these same prices and")
print(f"    outcomes, so the following demonstrates only that the transformation runs.")
print(f"    A forecaster judged against raw q scores skill "
      f"{skill_score(prices, outcomes, prices):+.4f} (trivially zero).")
print(f"    The SAME forecaster judged against q_ref scores "
      f"{skill_score(prices, outcomes, q_star):+.4f}.")
print("    The real test is PROTOCOL Gate 1: fit on prior events, freeze, score unseen events,")
print("    and delete the transformation if it does not beat raw q out of sample.")


section(3, "CALIBRATION VS ACCURACY  (direction only - see SPEC on the 2025 corrigendum)")
cal = IsotonicCalibrator().fit(prices, outcomes)
calibrated = [cal.predict(p) for p in prices]
print(f"raw (compressed)  Brier {brier_score(prices, outcomes):.4f}")
print(f"isotonic-fixed    Brier {brier_score(calibrated, outcomes):.4f}")
print("Same information, same ordering. Only the calibration changed.")


section(4, "MULTIPLE-TESTING DEFLATION AND INDEPENDENT INFORMATION")
for n in (2, 7, 50, 1000):
    print(f"  after {n:>4} configurations, expected max Sharpe under a TRUE Sharpe of 0: "
          f"{expected_max_sharpe(n):.3f}")
print(f"\n  observed Sharpe 1.0, 7 trials, 504 obs -> DSR {deflated_sharpe_ratio(1.0, 7, 504):.3f}"
      "   (not evidence)")
print(f"  minimum backtest length for 7 trials at Sharpe 1.0: {min_backtest_length(7):.2f} years")
print("\n  Rows are not observations:")
print(f"    500 contracts across 5 elections -> effective n "
      f"{effective_sample_size([100] * 5):.1f}")
print(f"    500 contracts across 500 events  -> effective n "
      f"{effective_sample_size([1] * 500):.1f}")
ok, detail = sufficient_evidence([100] * 5, required_effective_n=50.0)
print(f"    verdict: {detail}")


section(5, "IS THE EDGE A BUSINESS?  (published Polymarket arbitrage, priced)")
# Cheng et al. 2026: 173 NBA games, 290 combinatorial episodes, 101 bps median,
# 76.9% capped near 14.8 shares. NBA regular season = 1,230 games.
arb = StrategyEconomics(
    name="polymarket-nba-combinatorial (Cheng et al. 2026)",
    edge_per_contract=0.0101,
    fillable_contracts=14.8,
    opportunities_per_year=(290 / 173) * 1230,
    capital_required=5_000.0,
    annual_fixed_cost=2_000.0,
    hit_rate=0.5,
)
capacity_play = StrategyEconomics(
    name="hypothetical 2% edge with real capacity",
    edge_per_contract=0.02,
    fillable_contracts=25_000.0,
    opportunities_per_year=40.0,
    capital_required=100_000.0,
    annual_fixed_cost=2_000.0,
)
for s in rank_strategies([arb, capacity_play]):
    print(f"  {s.summary()}")
print(f"\n  The best-documented Polymarket arbitrage grosses "
      f"${arb.gross_annual_value:,.0f}/yr before engineering.")
print("  Four lines of arithmetic that would have saved a month of executor work.")


section(6, "ABSTENTION RATE  (a forecaster with a uniform 3-point edge)")
traded = total = 0
for mid_bp in range(10, 91, 5):
    for days in (1, 7, 30, 90):
        mid = mid_bp / 100.0
        stake = size_position(
            p=min(mid + 0.03, 1.0), mid=mid, costs=costs, limits=limits,
            days_to_resolution=days, p_stderr=0.02,
        )
        total += 1
        traded += stake.side is not Side.ABSTAIN
print(f"  {traded}/{total} markets sized; {100 * (1 - traded / total):.1f}% abstained.")
print("  A uniform 3-point edge is not an edge. This is the intended behaviour.")

print(f"\n{RULE}")
strong = size_position(p=0.62, mid=0.50, costs=costs, limits=limits,
                       days_to_resolution=14.0, p_stderr=0.02)
print("A genuinely large edge, for contrast (p=0.62 vs mid=0.50, 14d, stderr 0.02):")
print("  " + strong.explain().replace("\n", "\n  "))
print(RULE)
