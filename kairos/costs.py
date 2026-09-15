"""What an edge must clear before it is an edge.

Three costs, all of them documented in the literature as edge-killers:

1. **Spread.** You cross the book. Half the quoted spread, every time.
2. **Fees.** Event-contract venues charge a price-dependent fee. Whelan 2023 (Quantitative Finance,
   DOI 10.1080/14697688.2023.2257756) shows this fee structure *manufactures* a favourite-longshot
   bias: post-fee loss rates rise as the contract probability falls. Longshots are structurally
   worse, not just riskier.
3. **The settlement wedge.** Collateral stays locked until oracle settlement, so a near-certain
   dollar is a *delayed* dollar. Gebele et al. 2026 (arXiv 2605.31431) recover an implied
   settlement-discount term structure and find that adjusting for it removes **48-88%** of the
   apparent near-certainty price gradient. Most of the "free money" sitting in 97c contracts is
   the cost of capital lock-up, not mispricing.

Everything here is expressed in **price units per contract**, where a contract pays $1 on
resolution. That makes the decision rule trivial: buying YES is +EV iff `p > effective_yes_cost`.
"""

from __future__ import annotations

from dataclasses import dataclass

DAYS_PER_YEAR = 365.0


class CostError(ValueError):
    """Raised when a price or horizon is outside the domain where costs are defined."""


@dataclass(frozen=True)
class CostModel:
    """All-in transaction and carry costs for one event contract.

    Attributes:
        taker_fee_coeff: Coefficient of the quadratic fee ``coeff * P * (1 - P)`` per contract.
            The default 0.07 is the shape of Kalshi's published trading fee. **Verify against the
            live schedule before binding a venue** - a stale fee coefficient silently inflates
            every measured edge.
        maker_fee_coeff: Same, for resting orders. Often zero.
        half_spread: Half the quoted bid-ask, in price units. What crossing costs you.
        settlement_wedge_annual: Annualised opportunity cost of collateral locked until settlement.
        min_price / max_price: Contracts outside this band are refused outright. Venue tick bounds
            are the floor; the longshot exclusion in SPEC.md 2 is why the default band is tight.
    """

    taker_fee_coeff: float = 0.07
    maker_fee_coeff: float = 0.0
    half_spread: float = 0.005
    settlement_wedge_annual: float = 0.06
    min_price: float = 0.05
    max_price: float = 0.95

    def __post_init__(self) -> None:
        for name in ("taker_fee_coeff", "maker_fee_coeff", "half_spread", "settlement_wedge_annual"):
            if getattr(self, name) < 0.0:
                raise CostError(f"{name} must be non-negative, got {getattr(self, name)!r}")
        if not 0.0 <= self.min_price < self.max_price <= 1.0:
            raise CostError(
                f"require 0 <= min_price < max_price <= 1, got "
                f"({self.min_price!r}, {self.max_price!r})"
            )

    def fee(self, traded_price: float, *, maker: bool = False) -> float:
        """Per-contract fee at ``traded_price``.

        The quadratic ``P * (1 - P)`` peaks at 0.50 and vanishes at the extremes, which is exactly
        why it bites hardest in *relative* terms on longshots: the fee falls linearly in P while the
        payoff you are buying falls like P.
        """
        coeff = self.maker_fee_coeff if maker else self.taker_fee_coeff
        p = _require_price(traded_price, "traded_price")
        return coeff * p * (1.0 - p)

    def carry(self, capital_locked: float, days_to_resolution: float) -> float:
        """Opportunity cost of collateral locked until settlement (Gebele et al. 2026)."""
        if days_to_resolution < 0.0:
            raise CostError(f"days_to_resolution must be non-negative, got {days_to_resolution!r}")
        return capital_locked * self.settlement_wedge_annual * (days_to_resolution / DAYS_PER_YEAR)

    def effective_yes_cost(
        self, mid: float, days_to_resolution: float, *, maker: bool = False
    ) -> float:
        """All-in cost per contract to hold YES to resolution, in price units.

        Buying YES is +EV iff the calibrated probability exceeds this number. Returns a value that
        may exceed 1.0, in which case no probability whatsoever justifies the trade.
        """
        mid = _require_price(mid, "mid")
        traded = mid + (0.0 if maker else self.half_spread)
        base = traded + self.fee(min(traded, 1.0), maker=maker)
        return base + self.carry(base, days_to_resolution)

    def effective_yes_cost_at(self, traded_price: float, days_to_resolution: float) -> float:
        """All-in cost when the traded price is **already known**, e.g. a VWAP off the ask book.

        :meth:`effective_yes_cost` takes a *mid* and adds ``half_spread`` to model crossing the
        book. A price walked off the asks has already crossed, so sending it there charges the
        spread a second time — the same double-count C7 exists for, and worth a separate method
        rather than a ``maker`` flag: ``maker=True`` would suppress the spread but also swap in the
        maker fee, and taking the ask is a taker trade that pays taker fees.
        """
        traded = _require_price(traded_price, "traded_price")
        base = traded + self.fee(traded, maker=False)
        return base + self.carry(base, days_to_resolution)

    def effective_no_cost(
        self, mid: float, days_to_resolution: float, *, maker: bool = False
    ) -> float:
        """All-in cost per contract to hold NO to resolution, in price units.

        Buying NO is +EV iff ``1 - p`` exceeds this number.
        """
        mid = _require_price(mid, "mid")
        return self.effective_yes_cost(1.0 - mid, days_to_resolution, maker=maker)

    def maker_capture(self, quoted_spread: float, traded_price: float) -> float:
        """Price units a **maker** collects per contract, before adverse selection.

        A maker who buys at the bid and sells at the ask collects the whole spread over a two-fill
        round trip, so ``quoted_spread / 2`` per contract of own volume, less the maker fee on the
        fill. This is the one place in the model where the spread is **revenue**: everywhere else it
        is ``half_spread``, charged as the cost of crossing.

        .. warning::

           **An upper bound, and the excluded term is the whole business.** Adverse selection — being
           filled preferentially when the price is about to move against you — is not here, and
           neither is queue position, competition from incumbent makers, or inventory risk. All three
           cut against. Polymarket's published maker rewards cut for. Use this to *refuse* a maker
           hypothesis cheaply (``docs/PROTOCOL.md`` Gate M.0); it can never certify one.
        """
        if quoted_spread < 0.0:
            raise CostError(f"quoted_spread must be non-negative, got {quoted_spread!r}")
        price = _require_price(traded_price, "traded_price")
        return quoted_spread / 2.0 - self.fee(price, maker=True)

    def round_trip_drag(self, mid: float, days_to_resolution: float) -> float:
        """Total cost of taking YES and NO at ``mid`` - the width of the no-trade band.

        If this is >= 1.0 the two sides cannot both be priced sanely and no edge of any size
        survives. It is the single most useful number to print next to a claimed edge.
        """
        return (
            self.effective_yes_cost(mid, days_to_resolution)
            + self.effective_no_cost(mid, days_to_resolution)
            - 1.0
        )

    def price_in_band(self, mid: float) -> bool:
        """Whether ``mid`` is inside the tradeable band (longshot exclusion, SPEC.md 2)."""
        return self.min_price <= mid <= self.max_price


def _require_price(value: float, name: str) -> float:
    if not 0.0 <= value <= 1.0:
        raise CostError(f"{name} must lie in [0, 1], got {value!r}")
    return float(value)


#: Deliberately pessimistic defaults. Understating costs is the most common way a backtest
#: manufactures an edge that does not exist, so the burden of proof runs the other way: lower these
#: only against a venue's published schedule and a measured fill sample.
CONSERVATIVE = CostModel()
