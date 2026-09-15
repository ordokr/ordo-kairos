"""What a maker keeps per fill: the realized half-spread.

``docs/PROTOCOL.md`` Gate M. Gate M.0 established that there is a market to compete in; this is the
layer that answers whether an entrant would win it, which is the question the whole Class M
hypothesis turns on.

The statistic
-------------

::

    R(k) = mean over trades of  D_t x (p_t - p_{t+k})

`D_t` is trade direction and `p` the traded price. `R(k)` is what a maker who took the other side of
each trade still holds after the price has moved for `k` minutes.

**It already nets gross capture against adverse selection**, which is why nothing here separates
bounce from information. In a pure-bounce world — constant true value, trades landing randomly on
bid or ask — a maker genuinely earns the half-spread, and `R(k) = +s/2` at every horizon is the
correct answer rather than a bias to be corrected. Under informed flow the price moves *with* the
trade, `R` falls, and it goes negative exactly when informed flow takes more than the spread pays.

Adverse selection is then the decomposition ``quoted_half_spread - R(k)``, reported rather than
estimated directly.

Two things this rests on, both registered rather than discovered later
---------------------------------------------------------------------

**Direction is inferred, not read.** The public feed's own side flag matches on-chain truth about
**59%** of the time (Dubach 2026, ``AXIOMS`` D6), so it is refuted as a source. On-chain
``OrderFilled`` is ground truth and needs an RPC and log decoding, which is out of proportion for a
gate that can be refuted more cheaply. The tick test infers direction from the price series alone,
is a published method, and its error mode is known.

**Traded prices stand in for unpublished midquotes.** Polymarket does not publish historical quotes.
Under uninformed flow ``E[p_{t+k}] = m_{t+k}``, so the traded price is an unbiased stand-in; under
informed flow the difference is the very thing being measured.

The first version of this module measured *signed impact* instead, and was replaced before it ever
ran: the bounce term in that estimator does not decay with the horizon — it is a constant ``-s/2``
offset arising from ``p_t`` sitting on one side of the spread — and it points in the direction that
flatters the maker. See the Gate M amendment in ``docs/PROTOCOL.md``.
"""

from __future__ import annotations

import random
from typing import Sequence

__all__ = ["tick_sign", "realized_half_spread", "realized_half_spread_ci", "term_structure",
           "bootstrap_ci",
           "contributions"]

#: Contiguous observations per bootstrap block. `R`'s per-trade contributions are serially
#: correlated -- consecutive trades share the same price path -- so an IID resample would understate
#: the interval. A block bootstrap is what AXIOMS C4 requires and what every other inference in this
#: repository uses.
BLOCK = 50


def tick_sign(prices: Sequence[float]) -> tuple[int, ...]:
    """Trade direction by the tick test: ``+1`` buyer-initiated, ``-1`` seller-initiated, ``0`` none.

    An unchanged price carries the previous direction forward, which is the standard rule — a trade
    at the same price is not a trade with no side. Leading unchanged prices have nothing to carry
    and stay ``0``; the first observation has no predecessor and is always ``0``. Callers must skip
    zeros rather than treat them as a side.
    """
    out: list[int] = []
    last = 0
    for i, p in enumerate(prices):
        if i == 0:
            out.append(0)
            continue
        if p > prices[i - 1]:
            last = 1
        elif p < prices[i - 1]:
            last = -1
        out.append(last)
    return tuple(out)


def contributions(prices: Sequence[float], horizon: int) -> list[float]:
    """The per-trade terms ``D_t x (p_t - p_{t+k})`` whose mean is ``R(k)``."""
    if horizon <= 0:
        raise ValueError(f"horizon must be positive, got {horizon!r}")
    signs = tick_sign(prices)
    return [d * (prices[t] - prices[t + horizon])
            for t, d in enumerate(signs)
            if d != 0 and t + horizon < len(prices)]


def realized_half_spread_ci(prices: Sequence[float], horizon: int, *, seed: int = 0,
                            draws: int = 400, alpha: float = 0.05
                            ) -> tuple[float, float] | None:
    """Block-bootstrap confidence interval for ``R(horizon)``, or ``None`` if nothing is measurable.

    **Gate M's null gate failed on a point estimate, and the diagnosis was inference rather than
    bias.** The medians were correct in every world, but single replications landed on the wrong side
    of zero 20-27% of the time in genuinely losing worlds, and 47.5% in a world whose true value *is*
    zero. A point estimate forced a two-way verdict on a noisy quantity; the interval supplies the
    third state the repository already insists on everywhere else — **no verdict** (`kairos.validity`,
    AXIOMS A1).

    The registration called this gate "a deterministic comparison of two measured price quantities,
    not a significance test". That was wrong: ``R`` is a sample mean of serially correlated
    observations.
    """
    return bootstrap_ci(contributions(prices, horizon), seed=seed, draws=draws, alpha=alpha)


def bootstrap_ci(obs: Sequence[float], *, seed: int = 0, draws: int = 400,
                 alpha: float = 0.05) -> tuple[float, float] | None:
    """Block-bootstrap interval for the mean of ``obs``, or ``None`` if there are too few.

    Separate from :func:`realized_half_spread_ci` because the real measurement **pools
    contributions across markets** — no single market carries the ~100,000 observations the null
    gate measured as the detection threshold — and the pooled set is what gets resampled.
    """
    if len(obs) < 2 * BLOCK:
        return None
    rng = random.Random(seed)
    n_blocks = max(1, len(obs) // BLOCK)
    # Prefix sums so a block's total is O(1) rather than O(BLOCK). The resample is identical -
    # moving blocks of length BLOCK drawn with replacement - and this is what makes an adequately
    # powered replication count affordable at all.
    prefix = [0.0] * (len(obs) + 1)
    for i, x in enumerate(obs):
        prefix[i + 1] = prefix[i] + x
    last_start = len(obs) - BLOCK
    scale = 1.0 / (n_blocks * BLOCK)
    means: list[float] = []
    for _ in range(draws):
        total = 0.0
        for _ in range(n_blocks):
            s = rng.randint(0, last_start)
            total += prefix[s + BLOCK] - prefix[s]
        means.append(total * scale)
    means.sort()
    lo = means[int(alpha / 2 * len(means))]
    hi = means[min(len(means) - 1, int((1 - alpha / 2) * len(means)))]
    return lo, hi


def realized_half_spread(prices: Sequence[float], horizon: int) -> float | None:
    """``R(horizon)``, or ``None`` when the series supports no measurement at all.

    ``None`` rather than ``0.0`` is load-bearing: zero reads as "measured, and there is nothing
    there", which is a finding. A series too short for the horizon, or one with no directional
    trades in it, has produced no measurement (``AXIOMS`` A1, G5).
    """
    if horizon <= 0:
        raise ValueError(f"horizon must be positive, got {horizon!r}")
    signs = tick_sign(prices)
    total, n = 0.0, 0
    for t, d in enumerate(signs):
        if d == 0 or t + horizon >= len(prices):
            continue
        total += d * (prices[t] - prices[t + horizon])
        n += 1
    return total / n if n else None


def term_structure(prices: Sequence[float], horizons: Sequence[int]) -> dict[int, float | None]:
    """``R`` at each horizon.

    The shape is the diagnostic: **flat in ``k`` means uninformed flow**, and declining in ``k``
    means the fills are informed and the horizon decides how much that costs. It does *not* separate
    bounce from information — `R` has already done that — which is a correction to this gate's
    original registration.
    """
    return {k: realized_half_spread(prices, k) for k in horizons}
