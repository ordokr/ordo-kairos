"""Delta-neutral funding carry: what the trade earns, and the breach that pays for it.

``docs/PROTOCOL.md`` Class F. A carry position holds spot long against a perpetual short and
collects the funding longs pay shorts.

**It is not arbitrage.** Schmeling et al. trace crypto carry to trend-chasing leveraged demand met
by scarce arbitrage capital, and state that taking the other side "is risky due to spikes in margins
and liquidations amid drawdowns". The carry is **paid compensation for bearing crash risk** — the
negatively-skewed structure Brunnermeier et al. documented in FX: smooth accumulation, violent
unwind.

The asymmetry that decides the trade
------------------------------------

A short perpetual loses when the price **rises**. So the risk is an upward move — a squeeze — and
during a squeeze funding also spikes *positive*, which means **the carry pays most at exactly the
moment the position is most likely to be liquidated**. An estimator that sums funding without
modelling the breach measures the premium and ignores the risk it is paid for.

What this module assumes, stated rather than buried
---------------------------------------------------

**Spot and perp margin are not fungible.** The perp leg is margined on its own; a breach loses that
margin even though the spot leg has gained. The spot gain *is* credited back at the breach price,
which is the **generous** reading — a real liquidation fills worse than the trigger and may sit on a
venue the holder cannot rebalance in time. ``penalty`` carries that gap explicitly.

**Capital is spot notional plus perp margin**, never notional alone. Quoting carry against notional
is the single largest inflation vector in the published figures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

__all__ = ["liquidation_move", "deployed_capital", "CarryResult", "simulate", "naive_carry"]

#: Exchange maintenance margin, as a fraction of notional. Conservative round number.
MAINTENANCE = 0.005


def liquidation_move(leverage: float, maintenance: float = MAINTENANCE) -> float:
    """Adverse (upward) fractional price move that breaches the short perpetual's margin.

    At leverage ``L`` the perp posts ``1/L`` of notional, so a rise of ``1/L`` wipes it; the breach
    comes ``maintenance`` earlier. Ten-times leverage breaches on a **9.5%** move, which crypto
    delivers routinely.
    """
    if leverage < 1.0:
        raise ValueError(f"leverage must be at least 1, got {leverage!r}")
    threshold = 1.0 / leverage - maintenance
    if threshold <= 0.0:
        raise ValueError(
            f"leverage {leverage!r} leaves no margin above maintenance {maintenance!r}"
        )
    return threshold


def deployed_capital(leverage: float) -> float:
    """Capital locked per unit of notional: the spot leg in full, plus the perp's margin."""
    if leverage < 1.0:
        raise ValueError(f"leverage must be at least 1, got {leverage!r}")
    return 1.0 + 1.0 / leverage


@dataclass(frozen=True)
class CarryResult:
    pnl: float
    capital: float
    liquidated: bool
    periods_held: int

    @property
    def return_on_capital(self) -> float:
        return self.pnl / self.capital if self.capital > 0 else float("nan")


def simulate(fundings: Sequence[float], returns: Sequence[float], *, leverage: float,
             taker_fee: float, maintenance: float = MAINTENANCE,
             penalty: float = 0.0) -> CarryResult:
    """Walk a funding and price path, and stop at the breach if one comes.

    ``returns`` are per-period fractional price changes. While margin survives, the hedge nets price
    moves out and P&L is funding less four crossings. On a breach the perp margin is lost, the spot
    is credited at the breach price, ``penalty`` is charged for filling worse than the trigger, and
    **the carry stops** — which is usually the larger loss, because the position must be re-entered
    at four more crossings or abandoned.
    """
    if taker_fee < 0.0 or penalty < 0.0:
        raise ValueError("fees and penalties must be non-negative")
    threshold = liquidation_move(leverage, maintenance)
    margin = 1.0 / leverage
    capital = deployed_capital(leverage)

    pnl = -2.0 * taker_fee          # entry: buy spot, short perp
    cumulative = 0.0
    for i, (f, r) in enumerate(zip(fundings, returns)):
        cumulative += r
        pnl += f                    # funding accrues on one unit of notional
        if cumulative >= threshold:
            # Perp margin gone; spot credited **at the threshold, not at the overshot price**.
            #
            # Crediting `cumulative` here was a defect that failed Gate F's null gate: a discrete
            # period can jump far past the trigger, and the model then paid the whole overshoot on
            # the spot leg while losing only the fixed margin — manufacturing a profit out of a
            # liquidation. Exchanges liquidate continuously; nobody keeps the overshoot. The residue
            # is therefore exactly maintenance + penalty + one crossing, and the larger loss is the
            # carry never earned after this period (CORRECTIONS.md Pass 32).
            pnl += threshold - margin - penalty - taker_fee
            return CarryResult(pnl, capital, True, i + 1)
    pnl -= 2.0 * taker_fee          # exit: cover perp, sell spot
    return CarryResult(pnl, capital, False, len(list(fundings)))


def naive_carry(fundings: Sequence[float], *, taker_fee: float) -> float:
    """**The exhibit.** Funding summed, four crossings charged, breach ignored.

    This is what a carry backtest over a calm window reports, and it reports the identical number on
    a path that liquidates — because it never looks at the price. Retained because the size of its
    failure is the argument for Gate F.
    """
    return sum(fundings) - 4.0 * taker_fee
