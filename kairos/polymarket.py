"""Polymarket adapter: resolved markets -> a Gate-1 evaluation dataset.

Gate 1 asks whether ``q_ref`` earns its existence — whether *transforming* the observed market price
predicts outcomes better than the raw price. That question needs no forecaster and no model, only
``(price at decision time, realised outcome, event cluster, horizon, timestamp)``. This module
produces exactly that tuple and nothing else.

**Admission is by measured history density, not nominal horizon.** The feasibility census found a
market that traded for **7 days** against a stated 2029 end date, and found point counts that swing
with the ``fidelity`` parameter (``fidelity=60`` returned 1 point where ``fidelity=1440`` returned 8
on the same market). Admitting on ``endDate`` would silently fill the dataset with markets that have
no usable price path. Every market is therefore admitted on its *observed* history or not at all.

**The decision point is a fixed lead before trading stops**, not a fixed calendar date. Resolution
time is taken from the last observed price rather than ``endDate``, because markets resolve early
and ``endDate`` is frequently years wrong.

Network functions are thin and cached; all admission logic is pure and tested offline.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

__all__ = [
    "Observation",
    "decision_point",
    "admit",
    "resolution_of",
    "cache_dir",
    "fetch_resolved_markets",
    "fetch_history",
    "build_dataset",
]

GAMMA = "https://gamma-api.polymarket.com/markets"
CLOB_HISTORY = "https://clob.polymarket.com/prices-history"
#: The CLOB host 403s the default urllib agent. Found by probing, and a single unheaded probe once
#: nearly recorded "price history unavailable" as a hard blocker.
HEADERS = {"User-Agent": "Mozilla/5.0 (ordo-kairos gate1 adapter)"}
PAGE = 100

#: Daily. Chosen because it returned usable paths where hourly returned single points.
FIDELITY = 1440

#: Resolved markets report near-0/near-1 floats, never exact 0/1. Voids report ``["0","0"]``.
RESOLUTION_TOL = 1e-4


def features_before(history: Sequence[dict], decision_ts: int) -> dict[str, float]:
    """Price-path features using **only** points at or before ``decision_ts``.

    This is the leakage boundary of the whole project. A forecaster is allowed to know the decision
    price and everything that preceded it, and nothing else. The guard is tested directly: appending
    points after ``decision_ts`` must leave every feature unchanged.

    Deliberately price-only. Question text is excluded because it is the channel through which a
    language model's training data re-enters the evaluation.
    """
    pts = sorted(
        (int(p["t"]), float(p["p"]))
        for p in history
        if isinstance(p, dict) and "t" in p and "p" in p and int(p["t"]) <= decision_ts
    )
    if not pts:
        return {}
    prices = [p for _, p in pts]
    age_days = (pts[-1][0] - pts[0][0]) / 86400.0
    diffs = [b - a for a, b in zip(prices, prices[1:])]
    feats: dict[str, float] = {
        "n_before": float(len(pts)),
        "age_days": age_days,
        "mom_1": diffs[-1] if diffs else 0.0,
        "mom_3": (prices[-1] - prices[-4]) if len(prices) >= 4 else (prices[-1] - prices[0]),
        "drift_per_day": ((prices[-1] - prices[0]) / age_days) if age_days > 0 else 0.0,
        "volatility": (
            (sum((d - sum(diffs) / len(diffs)) ** 2 for d in diffs) / len(diffs)) ** 0.5
            if len(diffs) >= 2
            else 0.0
        ),
        "range": max(prices) - min(prices),
    }
    return feats


@dataclass(frozen=True)
class Observation:
    """One admitted market, reduced to what Gates 1 and 2 need.

    Attributes:
        cluster_id: Event identity. negRisk group where present, else the market itself. Contracts
            sharing this resolve together and are one observation's worth of information.
        price: Market price at the decision point — the benchmark to beat.
        outcome: Realised 0/1.
        days_to_resolution: Decision point to last trade. Drives the settlement adjustment.
        n_points: Measured history density. The admission criterion, kept for auditing.
        features: Price-path features computed strictly before the decision point.
    """

    market_id: str
    cluster_id: str
    question: str
    price: float
    outcome: float
    decision_ts: int
    resolution_ts: int
    days_to_resolution: float
    n_points: int
    features: dict[str, float] = field(default_factory=dict)

    def as_row(self) -> dict:
        return {
            "market_id": self.market_id,
            "cluster_id": self.cluster_id,
            "question": self.question,
            "price": self.price,
            "outcome": self.outcome,
            "decision_ts": self.decision_ts,
            "resolution_ts": self.resolution_ts,
            "days_to_resolution": self.days_to_resolution,
            "n_points": self.n_points,
            "features": dict(self.features),
        }


def resolution_of(market: dict) -> float | None:
    """The realised binary outcome, or None if the market did not resolve cleanly."""
    try:
        prices = [float(x) for x in json.loads(market["outcomePrices"])]
    except (KeyError, ValueError, TypeError):
        return None
    if len(prices) != 2 or abs(sum(prices) - 1.0) > RESOLUTION_TOL:
        return None
    if prices[0] > 1.0 - RESOLUTION_TOL:
        return 1.0
    if prices[0] < RESOLUTION_TOL:
        return 0.0
    return None


def decision_point(
    history: Sequence[dict], lead_hours: float
) -> tuple[int, float] | None:
    """Last ``(timestamp, price)`` at least ``lead_hours`` before trading stopped.

    Returns None when no point sits far enough back — which is the correct outcome for a market
    that only ever printed prices inside the lead window. Silently falling back to a later price
    would leak information from closer to resolution.
    """
    if not history or lead_hours < 0:
        return None
    try:
        pts = [(int(p["t"]), float(p["p"])) for p in history]
    except (KeyError, TypeError, ValueError):
        return None
    pts.sort()
    cutoff = pts[-1][0] - lead_hours * 3600
    eligible = [p for p in pts if p[0] <= cutoff]
    return eligible[-1] if eligible else None


def admit(
    market: dict,
    history: Sequence[dict],
    *,
    min_points: int = 5,
    lead_hours: float = 24.0,
    price_band: tuple[float, float] = (0.02, 0.98),
) -> Observation | None:
    """Pure admission. Returns an :class:`Observation` or None, with no side effects.

    Rejects when the market did not resolve cleanly, when measured history is thinner than
    ``min_points``, when no price exists at the required lead, or when the decision price sits
    outside the tradeable band. The band matters: a benchmark evaluated only on 0.99 contracts
    measures the extremes of the log score rather than forecasting skill.
    """
    outcome = resolution_of(market)
    if outcome is None:
        return None
    if len(history) < min_points:
        return None
    dp = decision_point(history, lead_hours)
    if dp is None:
        return None
    ts, price = dp
    lo, hi = price_band
    if not lo <= price <= hi:
        return None

    try:
        resolution_ts = max(int(p["t"]) for p in history)
    except (KeyError, TypeError, ValueError):
        return None
    days = (resolution_ts - ts) / 86400.0
    if days <= 0:
        return None

    mid = str(market.get("id") or market.get("questionID") or "")
    if not mid:
        return None
    cluster = market.get("negRiskMarketID") or f"solo:{mid}"
    return Observation(
        market_id=mid,
        cluster_id=str(cluster),
        question=str(market.get("question", ""))[:120],
        price=price,
        outcome=outcome,
        decision_ts=ts,
        resolution_ts=resolution_ts,
        days_to_resolution=days,
        n_points=len(history),
        features=features_before(history, ts),
    )


# ---------------------------------------------------------------------------
# I/O — deliberately thin, cached, and never writing inside the repository
# ---------------------------------------------------------------------------


#: Set once per process so the temp-fallback warning is printed exactly once, not per fetch.
_WARNED_VOLATILE = False


def cache_dir() -> Path:
    """Where fetched market data is cached.

    ``$ORDO_KAIROS_STATE`` when set, else a system temp directory. Never inside the repository:
    every repo under ``C:/src`` is publish-eligible, and a multi-megabyte scrape has no business in
    one even though this particular data is public.

    .. warning::

       **The temp fallback is not durable, and losing it is not merely a re-fetch.** This machine
       sweeps ``%TEMP%``; one sweep took the cache from 1,683 history files to 199 mid-run. Because
       the Gamma API paginates by descending end date, re-fetching page *n* later returns a
       *different* set of markets as new ones resolve — so a swept cache does not restore the old
       sample, it silently substitutes a new one, and every gate run against those pages becomes
       unreproducible. Set ``ORDO_KAIROS_STATE`` to durable storage outside the repo for any run
       whose dataset needs to be reconstructable.
    """
    global _WARNED_VOLATILE
    env = os.environ.get("ORDO_KAIROS_STATE", "").strip()
    if env:
        base = Path(env)
    else:
        base = Path(tempfile.gettempdir()) / "ordo-kairos-cache"
        if not _WARNED_VOLATILE:
            _WARNED_VOLATILE = True
            print(
                f"WARNING: caching to {base} (temp). This directory is swept on this machine, and "
                f"a swept cache cannot be restored by re-fetching - pagination drifts as markets "
                f"resolve. Set ORDO_KAIROS_STATE for a reproducible dataset.",
                file=sys.stderr,
            )
    base.mkdir(parents=True, exist_ok=True)
    return base


def _get(url: str, timeout: int = 40):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return json.loads(fh.read().decode("utf-8"))


#: Transient upstream failures that deserve a retry. **422 is excluded on purpose**: it is Gamma's
#: honest answer that an offset is past the end, and retrying it would turn a legitimate stop
#: condition into a stall.
_RETRY_CODES = frozenset({429, 500, 502, 503, 504})


def _get_retry(url: str, *, attempts: int = 4, timeout: int = 40, base_pause: float = 1.5):
    """``_get`` with exponential backoff on transient upstream errors.

    A single HTTP 500 killed a 909-event sweep partway through its fourth window. Retrying is the
    fix; **swallowing** is not. A window that cannot be fetched completely is a window with markets
    silently missing from it, which biases an event count in a way nothing downstream could detect,
    so exhausting the retries re-raises rather than returning a short page.
    """
    last: Exception | None = None
    for i in range(attempts):
        try:
            return _get(url, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code not in _RETRY_CODES:
                raise
            last = e
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            last = e
        if i < attempts - 1:
            time.sleep(base_pause * (2**i))
    assert last is not None
    raise last


def fetch_resolved_markets(pages: int, *, pause: float = 0.15) -> list[dict]:
    """Most-recently-resolved markets, newest first. Cached per page."""
    cache = cache_dir() / "markets"
    cache.mkdir(parents=True, exist_ok=True)
    out: list[dict] = []
    for i in range(pages):
        path = cache / f"page_{i:04d}.json"
        if path.exists():
            batch = json.loads(path.read_text(encoding="utf-8"))
        else:
            try:
                batch = _get(
                    f"{GAMMA}?closed=true&limit={PAGE}&offset={i * PAGE}"
                    f"&order=endDate&ascending=false"
                )
            except (urllib.error.URLError, TimeoutError, OSError):
                break
            path.write_text(json.dumps(batch), encoding="utf-8")
            time.sleep(pause)
        if not batch:
            break
        out.extend(batch)
    return out


#: Gamma refuses ``offset`` beyond this with HTTP 422, for every ordering, and silently caps
#: ``limit`` at 100 however large a value is asked for. Measured 2026-09-08, both confirmed against
#: the live API. This is a **pagination** ceiling, not a universe ceiling: the same query restricted
#: to a date window gets its own budget, and quarterly windows over 2021-2026 reach **26,143**
#: resolved markets against the 2,100 offset paging can see.
MAX_OFFSET = 2000


def quarterly_windows(first_year: int = 2021, last_year: int = 2026) -> list[tuple[str, str]]:
    """``(end_date_min, end_date_max)`` pairs, **newest first**, one per calendar quarter.

    Newest-first is the registered collection order for Look 3. Ordering the sweep by date rather
    than by anything measured on the data keeps window choice independent of results: a rule that
    said "take the windows with the most markets" would be selecting on a property of the sample.
    """
    out: list[tuple[str, str]] = []
    for year in range(first_year, last_year + 1):
        for lo, hi in (("01-01", "04-01"), ("04-01", "07-01"),
                       ("07-01", "10-01"), ("10-01", "12-31")):
            hi_date = f"{year}-{hi}" if hi != "12-31" else f"{year + 1}-01-01"
            out.append((f"{year}-{lo}", hi_date))
    out.reverse()
    return out


#: Give up on a window after this many consecutive offsets fail. Two quarters
#: (2025-10..2026-01 and 2026-01..2026-04) return HTTP 500 at *every* offset — a genuine upstream
#: fault, not a blip — and grinding 21 offsets x 4 attempts x backoff through each would stall the
#: sweep for nothing.
MAX_CONSECUTIVE_WINDOW_FAILURES = 6


def fetch_window(
    lo: str, hi: str, *, pause: float = 0.15, max_offset: int = MAX_OFFSET
) -> tuple[list[dict], list[int]]:
    """Resolved markets whose end date falls in ``[lo, hi)``, plus the offsets that could not load.

    Returns ``(markets, failed_offsets)``. **Failures are returned rather than raised or swallowed**,
    and that middle path is the whole point:

    - Raising aborts the sweep over an upstream fault unrelated to the hypothesis. Two full quarters
      are permanently HTTP 500 at every offset.
    - Swallowing makes a broken window look empty. An earlier probe did exactly that — returning
      ``[]`` on error — and three broken quarters were read as "no markets resolved then", a hole in
      the sample's calendar coverage that nothing downstream could have detected.

    A failed offset **advances** rather than ending the window, because ``2025-07-01..2025-10-01``
    fails at offset 0 and then serves every deeper page normally.
    """
    cache = cache_dir() / "windows"
    cache.mkdir(parents=True, exist_ok=True)
    out: list[dict] = []
    failed: list[int] = []
    consecutive = 0
    offset = 0
    while offset <= max_offset:
        path = cache / f"{lo}_{hi}_{offset:05d}.json"
        batch: list[dict] | None = None
        if path.exists():
            try:
                batch = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                batch = None
        if batch is None:
            try:
                batch = _get_retry(
                    f"{GAMMA}?closed=true&limit={PAGE}&offset={offset}"
                    f"&order=endDate&ascending=false"
                    f"&end_date_min={lo}T00:00:00Z&end_date_max={hi}T00:00:00Z"
                )
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
                if isinstance(e, urllib.error.HTTPError) and e.code == 422:
                    break  # past this window's offset budget - the expected stop
                failed.append(offset)
                consecutive += 1
                if consecutive >= MAX_CONSECUTIVE_WINDOW_FAILURES:
                    break
                offset += PAGE
                continue
            path.write_text(json.dumps(batch), encoding="utf-8")
            time.sleep(pause)
        consecutive = 0
        if not batch:
            break
        out.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
    return out, failed


def fetch_history(token_id: str, *, pause: float = 0.1) -> list[dict]:
    """Daily price history for one CLOB token. Cached — **successes only**.

    .. warning::

       **A failed fetch is never written to the cache.** The previous version caught bare
       ``Exception``, set ``hist = []`` and then *cached that*, which turned one transient network
       failure into a permanent, silent exclusion: the market was counted as ``no_history`` in every
       subsequent run, forever, with nothing recording that a fetch had ever failed. An empty cache
       entry is indistinguishable from "this market genuinely has no CLOB history", so the damage is
       not detectable after the fact — only measurable in aggregate. It was measured: **618 of 14,005
       cached histories (4.4%) are empty**, of unknown provenance.

       Not caching a failure costs one re-fetch on the next run and buys the guarantee that an empty
       entry means *measured empty*. That is the whole distinction between a measurement and an
       absence of one (``docs/AXIOMS.md`` A6, G5).
    """
    cache = cache_dir() / "history"
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{token_id[:40]}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    try:
        data = _get_retry(
            f"{CLOB_HISTORY}?market={token_id}&interval=max&fidelity={FIDELITY}", timeout=25
        )
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError,
            json.JSONDecodeError):
        return []  # deliberately NOT cached - the next run retries instead of inheriting a phantom
    hist = data.get("history", []) if isinstance(data, dict) else []
    path.write_text(json.dumps(hist), encoding="utf-8")
    time.sleep(pause)
    return hist


def build_dataset(
    markets: Iterable[dict],
    *,
    min_points: int = 5,
    lead_hours: float = 24.0,
    limit: int | None = None,
    progress=None,
) -> tuple[list[Observation], dict[str, int]]:
    """Fetch history for each market and admit what qualifies.

    Returns the observations and a rejection census, so the admission rate is auditable rather than
    implicit — a dataset assembled by silent filtering is not a measurement.
    """
    obs: list[Observation] = []
    reasons: dict[str, int] = {
        "no_resolution": 0,
        "no_tokens": 0,
        "no_history": 0,
        "thin_history": 0,
        "no_decision_point_or_band": 0,
        "admitted": 0,
    }
    for i, m in enumerate(markets):
        if limit is not None and reasons["admitted"] >= limit:
            break
        if resolution_of(m) is None:
            reasons["no_resolution"] += 1
            continue
        raw = m.get("clobTokenIds")
        if not raw:
            reasons["no_tokens"] += 1
            continue
        try:
            token = json.loads(raw)[0]
        except (json.JSONDecodeError, IndexError, TypeError):
            reasons["no_tokens"] += 1
            continue

        hist = fetch_history(token)
        if not hist:
            reasons["no_history"] += 1
            continue
        if len(hist) < min_points:
            reasons["thin_history"] += 1
            continue

        o = admit(m, hist, min_points=min_points, lead_hours=lead_hours)
        if o is None:
            reasons["no_decision_point_or_band"] += 1
            continue
        obs.append(o)
        reasons["admitted"] += 1
        if progress and reasons["admitted"] % 50 == 0:
            progress(f"admitted {reasons['admitted']} (scanned {i + 1})")

    obs.sort(key=lambda o: o.resolution_ts)
    return obs, reasons
