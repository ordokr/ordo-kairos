"""Polymarket's published liquidity-rewards scoring rule.

``docs/PROTOCOL.md`` Class R. Classes A, B, C and M all tested hypotheses whose counterparty was an
**informed trader**, and all four lost to it — Class M by a measured 96.1% of the spread. Here the
counterparty is the **venue**, which pays by published rule rather than by opinion.

The rule, from the venue's own documentation::

    S(v, s) = ((v - s) / v)^2 * b        v = max spread, s = distance from midpoint, b = size
    Q_one   = scored bids on m + scored asks on m'
    Q_two   = scored asks on m + scored bids on m'
    Q_min   = max(min(Q_one,Q_two), max(Q_one/c, Q_two/c))   midpoint in [0.10,0.90], c = 3.0
    Q_min   = min(Q_one, Q_two)                              outside it: two-sided required
    Q_final = Q_epoch / sum(Q_epoch)_n                        proportional share of the daily pool

**Reading the primary source inverted this class's own premise.** The candidate that produced the
registration was "quote at the max-spread edge to earn rewards while minimising fills". The score is
``((v-s)/v)^2`` — **zero at the edge**, maximal at the midpoint. Rewards pay quadratically more for
the tighter quote, which is also the position of maximum adverse selection, and that tension is the
entire gate. It was invisible in the second-hand summary the candidate was generated against.

.. warning::

   **``rewardsMaxSpread`` is published in CENTS** (``4.5``, ``6.5``), while every price in this
   repository is in dollars. Callers convert; these functions take price units throughout and will
   silently produce a hundred-fold wrong score if handed the raw field.
"""

from __future__ import annotations

__all__ = ["order_score", "q_min", "book_score", "share_of_pool", "maker_rebate",
           "holding_reward"]

#: One-sided quoting is credited at 1/c of a balanced book, in the normal midpoint range.
ONE_SIDED_DIVISOR = 3.0

#: Outside this band the venue withdraws the one-sided allowance entirely.
TWO_SIDED_BAND = (0.10, 0.90)


def order_score(max_spread: float, distance: float, size: float) -> float:
    """``S(v, s) = ((v - s) / v)^2 * b``, or ``0.0`` outside the qualifying band.

    Quadratic, so the midpoint is worth four times the quarter-spread and the edge is worth nothing.
    """
    if max_spread <= 0.0:
        raise ValueError(f"max_spread must be positive, got {max_spread!r}")
    if distance < 0.0 or distance > max_spread:
        return 0.0
    return ((max_spread - distance) / max_spread) ** 2 * size


def q_min(q_one: float, q_two: float, *, midpoint: float) -> float:
    """Combine the two book sides per the venue's rule.

    Balanced quoting scores the weaker side; a one-sided book is credited at ``1/c`` — but only in
    the normal midpoint range. Near the extremes the allowance is withdrawn and a single-sided maker
    scores **zero**, which is why a longshot cannot be farmed with a one-way quote.
    """
    lo, hi = TWO_SIDED_BAND
    if midpoint < lo or midpoint > hi:
        return min(q_one, q_two)
    return max(min(q_one, q_two), max(q_one / ONE_SIDED_DIVISOR, q_two / ONE_SIDED_DIVISOR))


def book_score(book, *, midpoint: float, max_spread: float, min_size: float) -> float:
    """Total score of everything already resting inside the qualifying band — the competition.

    Read off the **real book** with the venue's own formula rather than parameterised, because this
    is the one term in Gate R that could have been fudged into any answer.
    """
    total = 0.0
    for level in tuple(book.bids) + tuple(book.asks):
        if level.size < min_size:
            continue  # below the market's minimum qualifying size: does not score at all
        total += order_score(max_spread, abs(midpoint - level.price), level.size)
    return total


def share_of_pool(own_score: float, competitor_score: float) -> float:
    """``Q_final = own / (own + competitors)``.

    Zero own-score earns zero, even against an empty book — the edge-quote case. A pool is not
    handed to a maker who did not qualify for it.
    """
    if own_score <= 0.0:
        return 0.0
    denom = own_score + max(0.0, competitor_score)
    return own_score / denom if denom > 0.0 else 0.0


# ---------------------------------------------------------------------------
# The other two programmes: maker rebates and holding rewards
# ---------------------------------------------------------------------------


def maker_rebate(fee_rate: float, rebate_rate: float, price: float) -> float:
    """Rebate per contract you were the **maker** for.

    The venue charges takers ``fee = C x feeRate x p x (1-p)`` and redistributes ``rebateRate`` of
    it to makers. The pool is ``rebateRate x total fees`` and a maker's share is
    ``own_fee_equivalent / total_fee_equivalent``, so the two scale together and the per-contract
    rebate is simply ``rebateRate x fee`` — **independent of how many other makers are present.**

    That independence is the structural difference from liquidity rewards, which normalise against
    every entrant and which Gate R measured as a congestion game. It is also why this term dwarfs
    the spread: at ``p = 0.5`` in a politics market the rebate is ``0.0025`` per contract against a
    **measured** spread retention of ``0.00039`` (Gate M).

    A fee-free category (geopolitics) pays **nothing** — excluded by arithmetic, not by choice.
    """
    if fee_rate < 0.0 or rebate_rate < 0.0:
        raise ValueError("fee and rebate rates must be non-negative")
    p = _require_price(price)
    return rebate_rate * fee_rate * p * (1.0 - p)


def holding_reward(position_value: float, annual_rate: float, days: float) -> float:
    """Holding-reward accrual on a position held for ``days``.

    Paid for **merely holding** an eligible position — no quote, no fill, no spread. Sampled hourly
    and paid daily at an annualised rate the venue sets.

    .. warning::

       **This is a treasury-funded subsidy, not a market edge.** The venue states the rate is
       variable and at its discretion, so a figure resting on it carries a single-decision failure
       mode that no measurement can hedge. At 3.25% it does not clear the 6% this repository already
       charges for locked collateral, so it cannot stand alone — it can only stack.
    """
    if position_value < 0.0 or annual_rate < 0.0 or days < 0.0:
        raise ValueError("position value, rate and days must be non-negative")
    return position_value * annual_rate * days / 365.0


def _require_price(value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"price must lie in [0, 1], got {value!r}")
    return value
