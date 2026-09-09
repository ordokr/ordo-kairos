"""Cross-venue event identity, and the null worlds that must precede any pairing scan.

``docs/PROTOCOL.md`` Gate C registers the false-positive generator for cross-venue Class B as
**semantic non-fungibility**: two markets that *look* identical and resolve differently. It is the
exact analogue of leg-set truncation, which Gate B measured as carrying the entire intra-venue
defence. So no pairing pipeline touches real paired data until it can correctly find **nothing** in
worlds built to contain no true pair (AXIOMS A7).

**The circularity this module is built to avoid.** ``docs/CORRECTIONS.md`` Pass 11 recorded Gate B's
positive control as circular: ``inject_arbitrage`` bisected on ``effective_yes_cost``, the scanner's
own formula, so detecting it was guaranteed by construction rather than measured. The identical
trap here would be to hand the matcher a structured ``EventIdentity`` on both sides and have it
compare fields — that tests dataclass equality and nothing else.

So the layers are kept apart, and the separation is the whole design:

* :class:`EventIdentity` is **ground truth**. Only the world generators and the oracle ever see it.
* :func:`publish` renders an identity the way a venue publishes it — a title, a rules paragraph and
  a close timestamp — with venue-specific phrasing, date format, threshold format and verb
  inflection.
* :func:`parse_market` must **recover** the evidence from that published surface.
* :func:`same_event`, the instrument under test, sees only :class:`RawMarket`.

The positive control is what makes this bite: the same event is phrased *differently* on the two
venues, so a matcher that memorises one template loses power immediately.

**What this gate does not establish, stated up front.**

1. **Coverage of real venue phrasing.** The text distribution here is ours. This falsifies the
   matcher's *logic*; it cannot falsify its coverage of titles neither venue has yet been asked for.
   That check needs fetched titles and is a separate, later measurement.
2. **That published metadata carries the evidence at all.** The oracle ceiling is computed on ground
   truth, so it proves a world *contains* a mismatch — not that the mismatch is recoverable from
   what a venue actually publishes. On real data those two failures look identical from inside the
   matcher and must be told apart by hand.
3. **Source-string normalisation.** Two venues may name the same arbiter differently ("the primary
   spot index" vs a vendor's product name). Here they do not. In reality this costs **power, not
   false pairs** — an unmatched synonym refuses a true pair — which is the safe direction, but it
   means the measured power here is an upper bound on the real thing.
"""

from __future__ import annotations

import difflib
import random
import re
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

__all__ = [
    "EventIdentity",
    "RawMarket",
    "ParsedIdentity",
    "PairVerdict",
    "Pair",
    "publish",
    "parse_market",
    "scope_tokens",
    "detect_negation",
    "compare_identities",
    "same_event",
    "same_event_naive",
    "same_event_oracle",
    "title_similarity",
    "NULL_WORLDS",
    "CONTROL_WORLD",
    "WORLDS",
    "build_pair",
]


# ---------------------------------------------------------------------------
# Ground truth and published surface
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventIdentity:
    """What a market **is**. Never visible to the matcher — only to the worlds and the oracle.

    The fields are the pairing evidence Gate C froze — resolution date, threshold, resolution
    source, scope (``subject`` + ``claim``) and side polarity — **plus the settlement instant**.

    ``settlement_time`` is not in the registered five. That omission is a defect in the
    registration, found by building against it: Gate C registers a *settlement-time mismatch* null
    world, and a matcher restricted to the five listed fields cannot refuse it, because two markets
    settling the same day at different clock times agree on every one of them. Recorded in
    ``docs/CORRECTIONS.md`` Pass 18 rather than silently widened.
    """

    subject: str
    claim: str
    threshold: float | None
    resolution_date: str  # YYYY-MM-DD
    settlement_time: str  # HH:MM, UTC
    source: str
    negated: bool = False
    #: ``"deadline"`` or ``"instant"``. Registered as the seventh piece of evidence in Gate C2: the
    #: two carry the same timestamp and different payoffs, so an extractor that returns the instant
    #: and drops this would manufacture the non-fungibility the gate exists to catch.
    modality: str = "instant"


@dataclass(frozen=True)
class RawMarket:
    """What a venue publishes, and **all** the matcher is allowed to see."""

    venue: str
    market_id: str
    title: str
    rules: str
    close_iso: str


@dataclass(frozen=True)
class ParsedIdentity:
    """Evidence recovered from a :class:`RawMarket`. ``missing`` is what could not be recovered."""

    scope: frozenset[str]
    threshold: float | None
    instant: str | None
    source: frozenset[str]
    negated: bool
    missing: tuple[str, ...]
    #: ``"deadline"`` (resolves if the event happens *by* the instant) or ``"instant"`` (resolves on
    #: the state *at* it). Same timestamp, different payoff: a barrier and a digital. Gate C2.
    modality: str | None = None
    #: True when a determination instant recovered from prose **agrees** with the venue's structured
    #: timestamp. A venue whose timestamp is sometimes a placeholder needs that second source before
    #: its minute can be trusted; see :func:`kairos.crossvenue.polymarket_descriptor`.
    instant_confirmed: bool = False


@dataclass(frozen=True)
class PairVerdict:
    left_id: str
    right_id: str
    paired: bool
    refusals: tuple[str, ...]

    def explain(self) -> str:
        if self.paired:
            return f"{self.left_id} == {self.right_id}: SAME EVENT"
        return f"{self.left_id} != {self.right_id}: refused ({', '.join(self.refusals)})"


@dataclass(frozen=True)
class Pair:
    """One null-world unit: two published markets and the truth about whether they match."""

    world: str
    left_identity: EventIdentity
    right_identity: EventIdentity
    left: RawMarket
    right: RawMarket
    truly_same: bool


# ---------------------------------------------------------------------------
# Publication — the same identity, phrased as each venue phrases it
# ---------------------------------------------------------------------------

_MONTHS = ("January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December")

#: Title templates, each tagged with whether it needs the claim's base form. "Will Bitcoin *close*
#: above" and "Bitcoin *closes* above" are the same claim inflected differently, which is the
#: cheapest realistic thing a template-matching parser gets wrong.
_POLY_TITLES = (
    ("Will {clause} on {date}?", True),
    ("{clause} on {date}?", False),
)
_KALSHI_TITLES = (
    ("{clause} - {date}", False),
    ("Will {clause} ({date})?", True),
)

#: Rules paragraphs carrying the determination instant **in prose**, the way Polymarket writes it:
#: *"...by December 31, 2026, 11:59 PM ET."* The gate has to exercise this path, because on the real
#: venue it is the only place the settlement minute can be confirmed.
_POLY_RULES = ('This market will resolve to "Yes" if {clause} {phrase}. '
               "The resolution source is {source}.")
_KALSHI_RULES = "Settles YES if {clause} {phrase}. Source: {source}."

#: Eastern Time, computed rather than looked up. Windows Python ships no IANA database and this
#: repo takes no third-party dependencies, so ``zoneinfo`` is unavailable — but a fixed -5 offset is
#: wrong for eight months of the year, and an hour of error is more than enough to make two
#: different events look like one. The post-2007 US rule is small, exact and testable.
_DST_FIRST_YEAR = 2007
_EST = timedelta(hours=-5)
_EDT = timedelta(hours=-4)


def _nth_sunday(year: int, month: int, n: int) -> date:
    first = date(year, month, 1)
    return first.replace(day=1 + (6 - first.weekday()) % 7 + 7 * (n - 1))


def _dst_window(year: int) -> tuple[datetime, datetime]:
    """Local-clock boundaries: second Sunday in March 02:00, first Sunday in November 02:00."""
    start = _nth_sunday(year, 3, 2)
    end = _nth_sunday(year, 11, 1)
    return (datetime(start.year, start.month, start.day, 2),
            datetime(end.year, end.month, end.day, 2))


def _et_to_utc(local: datetime) -> str | None:
    """Eastern wall-clock -> UTC, or ``None`` when the wall-clock reading is not a unique instant.

    Two hours a year are refused rather than guessed. In March 02:00-02:59 **does not exist**; in
    November 01:00-01:59 happens **twice**. Picking one silently would put the instant an hour out,
    and an hour is the size of error that makes a 12pm market look like a 1pm one (AXIOMS A6).
    """
    if local.year < _DST_FIRST_YEAR:
        return None  # the rule before 2007 was different; refuse rather than misdate
    start, end = _dst_window(local.year)
    if local < start:
        offset = _EST
    elif local < start + timedelta(hours=1):
        return None  # nonexistent local time
    elif local < end - timedelta(hours=1):
        offset = _EDT
    elif local < end:
        return None  # ambiguous local time
    else:
        offset = _EST
    return f"{local - offset:%Y-%m-%dT%H:%M}Z"


def _utc_to_et(utc: datetime) -> datetime:
    year = utc.year
    if year < _DST_FIRST_YEAR:
        return utc + _EST
    start, end = _dst_window(year)
    start_utc, end_utc = start - _EST, end - _EDT
    return utc + (_EDT if start_utc <= utc < end_utc else _EST)


def _base_form(claim: str) -> str:
    """``"closes above"`` -> ``"close above"``. Crude on purpose; the parser must undo it."""
    head, _, tail = claim.partition(" ")
    if len(head) > 3 and head.endswith("s") and not head.endswith("ss"):
        head = head[:-1]
    return f"{head} {tail}".strip()


def _fmt_date_long(iso: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{_MONTHS[m - 1]} {d}, {y}"


def _fmt_date_short(iso: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{_MONTHS[m - 1][:3]} {d}, {y}"


def _utc_to_et_phrase(iso_date: str, hhmm: str, *, modality: str, abbreviated: bool,
                      keyword: int) -> str:
    """Render a UTC instant the way a venue writes it: an ET wall-clock time in prose.

    The conversion is done through the zone database rather than a fixed offset, because ET is
    UTC-5 or UTC-4 depending on the date and a hardcoded offset silently misdates half the year.
    Crossing midnight is the normal case, not an edge case: 04:59Z is 11:59 PM ET *the previous
    day*, which is exactly how both venues encode an end-of-year deadline.
    """
    hour, minute = (int(x) for x in hhmm.split(":"))
    local = _utc_to_et(datetime(*(int(x) for x in iso_date.split("-")), hour, minute))
    suffix = "AM" if local.hour < 12 else "PM"
    twelve = local.hour % 12 or 12
    month = _MONTHS[local.month - 1]
    stamp = f"{month[:3] if abbreviated else month} {local.day}, {local.year}"
    clock = f"{twelve}:{local.minute:02d} {suffix} ET"
    if modality == "deadline":
        return f"{('by', 'before')[keyword % 2]} {stamp}, {clock}"
    return f"on {stamp} at {clock}"


def _fmt_threshold(value: float, style: int) -> str:
    if style == 1:
        return f"{value:.0f}"
    if style == 2 and value % 1000 == 0:
        return f"${value / 1000:.0f}k"
    return f"${value:,.0f}"


def _clause(ident: EventIdentity, *, base_form: bool, thr_text: str, neg_style: int) -> str:
    verb = _base_form(ident.claim) if (base_form or ident.negated) else ident.claim
    if not ident.negated:
        prefix = ""
    elif base_form:
        prefix = "not "
    else:
        prefix = ("does not ", "fails to ")[neg_style % 2]
    text = f"{ident.subject} {prefix}{verb}"
    return f"{text} {thr_text}" if thr_text else text


def publish(ident: EventIdentity, venue: str, *, seed: int = 0, market_id: str = "",
            structured_close: bool = True) -> RawMarket:
    """Render an identity as ``venue`` would publish it.

    Phrasing, date format, threshold format and verb inflection all vary. Nothing that varies
    carries meaning: a true pair published on both venues differs only in surface, so any refusal
    the matcher makes on a true pair is its own defect and shows up directly as lost power.
    """
    rng = random.Random(seed)
    if venue == "polymarket":
        template, base_form = rng.choice(_POLY_TITLES)
        date_text = _fmt_date_long(ident.resolution_date)
        thr_style = rng.choice((0, 2))
        rules_t = _POLY_RULES
        close = f"{ident.resolution_date}T{ident.settlement_time}:00Z"
    elif venue == "kalshi":
        template, base_form = rng.choice(_KALSHI_TITLES)
        date_text = _fmt_date_short(ident.resolution_date)
        thr_style = rng.choice((1, 0))
        rules_t = _KALSHI_RULES
        close = f"{ident.resolution_date}T{ident.settlement_time}:00+00:00"
    else:
        raise ValueError(f"unknown venue {venue!r}")

    thr_text = "" if ident.threshold is None else _fmt_threshold(ident.threshold, thr_style)
    neg_style = rng.randrange(2)
    title = template.format(
        clause=_clause(ident, base_form=base_form, thr_text=thr_text, neg_style=neg_style),
        date=date_text,
    )
    phrase = _utc_to_et_phrase(ident.resolution_date, ident.settlement_time,
                               modality=ident.modality, abbreviated=(venue == "kalshi"),
                               keyword=rng.randrange(2))
    rules = rules_t.format(
        clause=_clause(ident, base_form=False, thr_text=thr_text, neg_style=neg_style),
        source=ident.source,
        phrase=phrase,
    )
    return RawMarket(venue, market_id or f"{venue[:2]}-{seed}", title,
                     rules, close if structured_close else "")


# ---------------------------------------------------------------------------
# Extraction — recovering the evidence from published text
# ---------------------------------------------------------------------------

_MONTH_ALT = "|".join(m for m in _MONTHS) + "|" + "|".join(m[:3] for m in _MONTHS)

_DATE_PATTERNS = (
    re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b"),
    re.compile(rf"\b(?:{_MONTH_ALT})\.?\s+\d{{1,2}},?\s*(?:19|20)\d{{2}}\b", re.I),
)

_THR_RE = re.compile(r"\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*([kKmM])?\b")
_INSTANT_RE = re.compile(r"(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})")
_SOURCE_RE = re.compile(r"(?:resolution source is|source:|according to)\s*(.+?)\s*\.", re.I)
_NEGATION_RE = re.compile(r"\b(?:not|never|fails to)\b", re.I)
_TOKEN_RE = re.compile(r"[a-z]+")

#: Structural words carrying no scope. Negation markers are here deliberately: polarity is its own
#: piece of evidence, so a negated title and its affirmative twin must produce the **same** scope
#: tokens and be told apart only by :attr:`ParsedIdentity.negated`. Folding negation into the token
#: set would let a polarity inversion masquerade as a scope difference and be refused for the wrong
#: reason, which passes the gate while leaving the sign bug intact (AXIOMS G7).
_STOP = frozenset({
    "will", "the", "a", "an", "on", "at", "in", "of", "be", "is", "are", "does", "do",
    "not", "never", "fails", "fail", "to", "by", "and", "or", "for", "resolves", "yes",
})


def _stem(token: str) -> str:
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _content_tokens(text: str) -> frozenset[str]:
    return frozenset(_stem(t) for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP)


def _strip_dates(text: str, *, known_year: str | None = None) -> str:
    """Remove dates *before* looking for a threshold, so ``31`` is not read as a strike.

    **A bare four-digit number is not stripped as a year.** The first version of this function
    matched ``\\b(?:19|20)\\d{2}\\b``, which deleted any strike in 1900-2099 — and Gate C found the
    consequence: two markets quoted at ``2000`` and ``2050`` both parsed to *no strike*, agreed on
    every other field, and were declared **the same event**. A false pair, which is the failure this
    whole gate exists to prevent, produced by the date handling rather than by the comparison.

    The disambiguation does not need a guess: the venue publishes the close timestamp separately, so
    the resolution year is *known* and only that year is removed, and only where it is not attached
    to a currency symbol, another digit or a k/m suffix. The residual ambiguity — a strike equal to
    its own market's resolution year — can only cost power, never produce a false pair: for two
    markets to both lose their strike this way they must share a resolution date, and sharing a date
    while both strikes equal that year makes the strikes equal too.
    """
    for pattern in _DATE_PATTERNS:
        text = pattern.sub(" ", text)
    if known_year:
        text = re.sub(rf"(?<![\d$,.]){re.escape(known_year)}(?![\d,.]|\s*[kKmM]\b)", " ", text)
    return text


def _extract_threshold(text: str) -> tuple[float | None, str]:
    match = _THR_RE.search(text)
    if match is None:
        return None, text
    try:
        value = float(match.group(1).replace(",", ""))
    except ValueError:  # pragma: no cover - the pattern cannot produce this
        return None, text
    suffix = (match.group(2) or "").lower()
    if suffix == "k":
        value *= 1_000.0
    elif suffix == "m":
        value *= 1_000_000.0
    return value, text[: match.start()] + " " + text[match.end():]


#: A determination instant as a venue writes it in prose. The leading keyword is captured because it
#: carries the **modality**: "by"/"before" is a deadline, "on"/"at" is an instant. Same timestamp,
#: different payoff — dropping the keyword and keeping the time is how an extractor manufactures the
#: exact non-fungibility this gate exists to catch (Gate C2).
_PROSE_INSTANT_RE = re.compile(
    rf"\b(by|before|on|at)\b[^.]{{0,60}}?\b({_MONTH_ALT})\.?\s+(\d{{1,2}}),?\s*((?:19|20)\d{{2}})"
    r"(?:,|\s+at)?\s*(\d{1,2})(?::(\d{2}))?\s*([AaPp])\.?[Mm]\.?\s*(ET|EST|EDT|UTC|GMT)\b",
    re.I,
)

_MONTH_INDEX = {m.lower(): i + 1 for i, m in enumerate(_MONTHS)}
_MONTH_INDEX.update({m[:3].lower(): i + 1 for i, m in enumerate(_MONTHS)})

_DEADLINE_WORDS = frozenset({"by", "before"})


def extract_prose_instant(rules: str) -> tuple[str | None, str | None]:
    """``(utc_instant, modality)`` recovered from a rules paragraph, or ``(None, None)``.

    Zones resolve through the zone database — ``ET`` via ``America/New_York`` — so daylight saving
    is handled by the data rather than a hardcoded offset that is wrong for half the year. Any zone
    outside the recognised set is **unrecoverable rather than assumed** (AXIOMS A6): guessing UTC for
    an unlabelled time would shift the instant by up to five hours, which is precisely the size of
    error that makes two different events look like one.
    """
    match = _PROSE_INSTANT_RE.search(rules or "")
    if match is None:
        return None, None
    keyword, month_name, day, year, hour, minute, meridiem, zone = match.groups()
    month = _MONTH_INDEX.get(month_name.lower())
    if month is None:  # pragma: no cover - the alternation cannot produce this
        return None, None
    hour = int(hour) % 12
    if meridiem.lower() == "p":
        hour += 12
    try:
        local = datetime(int(year), month, int(day), hour, int(minute or 0))
    except ValueError:
        return None, None  # e.g. February 31: a date that does not exist is not a date
    if zone.upper() in ("UTC", "GMT"):
        stamp: str | None = f"{local:%Y-%m-%dT%H:%M}Z"
    else:
        stamp = _et_to_utc(local)
    if stamp is None:
        return None, None
    modality = "deadline" if keyword.lower() in _DEADLINE_WORDS else "instant"
    return stamp, modality


def _extract_instant(close_iso: str) -> str | None:
    match = _INSTANT_RE.search(close_iso or "")
    if match is None:
        return None
    return f"{match.group(1)}T{match.group(2)}:{match.group(3)}Z"


def _extract_source(rules: str) -> frozenset[str]:
    match = _SOURCE_RE.search(rules or "")
    return _content_tokens(match.group(1)) if match else frozenset()


def parse_market(raw: RawMarket) -> ParsedIdentity:
    """Recover the pairing evidence from published text. Order matters and is deliberate.

    The close timestamp is read **first**, because it is the only authoritative statement of the
    resolution year and :func:`_strip_dates` needs it to tell a date apart from a strike. Dates go
    next, so a day-of-month is not read as a strike; the threshold is removed after that, so it does
    not survive into the scope tokens.
    """
    structured = _extract_instant(raw.close_iso)
    prose, modality = extract_prose_instant(raw.rules)
    instant = structured or prose
    stripped = _strip_dates(raw.title, known_year=instant[:4] if instant else None)
    threshold, remainder = _extract_threshold(stripped)
    negated = bool(_NEGATION_RE.search(remainder))
    scope = _content_tokens(remainder)
    source = _extract_source(raw.rules)

    missing: list[str] = []
    if instant is None:
        missing.append("settlement_instant")
    if structured and prose and structured != prose:
        # Two published sources contradicting each other about when the market settles. The one
        # thing that must never happen here is picking a favourite: a resolution rule and a close
        # timestamp that disagree mean the settlement minute is *unknown*, not that one of them is
        # right (AXIOMS A6).
        missing.append("settlement_time")
    if modality is None:
        missing.append("modality")
    if not source:
        missing.append("resolution_source")
    if not scope:
        missing.append("scope")
    return ParsedIdentity(scope, threshold, instant, source, negated, tuple(missing),
                          modality=modality,
                          instant_confirmed=bool(structured and prose and structured == prose))


def scope_tokens(text: str) -> frozenset[str]:
    """Content tokens of a phrase, for a venue adapter that has its own text to normalise.

    Exposed so an adapter reaches the *same* normalisation the gate exercised — stopwords, stemming
    and the deliberate exclusion of negation markers — instead of writing a second one that drifts.
    """
    return _content_tokens(text)


def detect_negation(text: str) -> bool:
    """Whether a phrase asserts the complement. Same rule the gate tested."""
    return bool(_NEGATION_RE.search(text or ""))


# ---------------------------------------------------------------------------
# The matchers
# ---------------------------------------------------------------------------

_THR_TOL = 1e-6


def compare_identities(pa: ParsedIdentity, pb: ParsedIdentity, *, left_id: str = "left",
                       right_id: str = "right") -> PairVerdict:
    """The six comparisons, and the only place they live.

    Split out from :func:`same_event` so a venue adapter that reads a **structured** field — Kalshi
    publishes ``floor_strike`` and ``settlement_sources`` as data, not prose — can reach the same
    comparison without round-tripping through text it would only have to parse back. Extraction
    differs by venue; the comparison must not, because it is the part Gate C's kill-tests proved
    necessary check by check, and a second copy would not inherit that (AXIOMS G8).

    **Fails closed on evidence it could not recover** (A6). A market whose settlement instant or
    resolution source is unavailable is not "probably fine"; it is a market about which the identity
    question has not been answered, and the payoff identity the whole cross-venue thesis rests on is
    exactly as unprovable as an unverified leg set.

    Resolution date and settlement time are reported as **separate** refusals even though both come
    from one timestamp. That is not cosmetic: the settlement-time null world is the only one a
    date-only comparison misses, so keeping the reasons apart is what makes a gate's table show
    *which* check earned the refusal rather than that some check did (G10).
    """
    refusals: list[str] = []
    for parsed, side in ((pa, "left"), (pb, "right")):
        refusals.extend(f"unrecoverable:{side}:{m}" for m in parsed.missing)

    # A field neither side could supply has not been *compared*, so it must not also be reported as
    # *disagreeing*. The first cross-venue run emitted both, and `resolution_source_differs` came
    # back at 100% of 2.28M pairs — 69% of which were really "Polymarket publishes its arbiter as
    # prose and the extractor found none". Worse, a reason that fires on every pair makes the
    # sole-blocker column identically zero, destroying the one diagnostic that names the binding
    # constraint. G10 says report why; reporting a comparison that never happened is not why.
    unavailable = set(pa.missing) | set(pb.missing)

    if pa.instant is not None and pb.instant is not None:
        if pa.instant[:10] != pb.instant[:10]:
            refusals.append("resolution_date_differs")
        elif "settlement_time" not in unavailable and pa.instant != pb.instant:
            refusals.append("settlement_time_differs")

    if "threshold" not in unavailable:
        if (pa.threshold is None) != (pb.threshold is None):
            refusals.append("threshold_presence_differs")
        elif pa.threshold is not None and pb.threshold is not None:
            if abs(pa.threshold - pb.threshold) > _THR_TOL:
                refusals.append("threshold_differs")

    if "resolution_source" not in unavailable and pa.source != pb.source:
        refusals.append("resolution_source_differs")
    if "scope" not in unavailable and pa.scope != pb.scope:
        refusals.append("scope_differs")
    if "modality" not in unavailable and pa.modality != pb.modality:
        refusals.append("modality_differs")
    if pa.negated != pb.negated:
        refusals.append("polarity_differs")

    return PairVerdict(left_id, right_id, not refusals, tuple(refusals))


def same_event(a: RawMarket, b: RawMarket) -> PairVerdict:
    """The instrument Gate C tests: extract from published text, then compare."""
    return compare_identities(parse_market(a), parse_market(b),
                              left_id=a.market_id, right_id=b.market_id)


def title_similarity(a: RawMarket, b: RawMarket) -> float:
    return difflib.SequenceMatcher(None, a.title.lower(), b.title.lower()).ratio()


def same_event_naive(a: RawMarket, b: RawMarket, *, threshold: float = 0.85) -> PairVerdict:
    """**Exhibit, never an instrument.** Pair on title similarity.

    This is the matcher a reasonable person writes first, and Gate C exists partly to measure how
    badly it does. It should do badly in a specific and instructive way: the discriminating evidence
    between a true pair and a near-miss is a handful of characters — one date, one strike, one
    ``not`` — while the surface difference between two venues describing the *same* event is much
    larger than that. Similarity is therefore not weakly informative here; it points the wrong way.
    """
    sim = title_similarity(a, b)
    paired = sim >= threshold
    return PairVerdict(a.market_id, b.market_id, paired,
                       () if paired else ("title_similarity_below_threshold",))


def same_event_oracle(a: EventIdentity, b: EventIdentity) -> PairVerdict:
    """The ceiling: compares ground truth directly, bypassing publication and extraction.

    Used only to verify that a world contains what it claims to. It is **not** an upper bound on
    what any real matcher could achieve, because it never reads the published surface — a mismatch
    the venues do not publish is invisible to every text-based matcher and still scores 1.000 here.
    """
    diffs = [
        name for name, x, y in (
            ("subject", a.subject, b.subject),
            ("claim", a.claim, b.claim),
            ("threshold", a.threshold, b.threshold),
            ("resolution_date", a.resolution_date, b.resolution_date),
            ("settlement_time", a.settlement_time, b.settlement_time),
            ("source", a.source, b.source),
            ("modality", a.modality, b.modality),
            ("polarity", a.negated, b.negated),
        ) if x != y
    ]
    return PairVerdict("truth:left", "truth:right", not diffs,
                       tuple(f"{d}_differs" for d in diffs))


# ---------------------------------------------------------------------------
# Worlds — every pair below is NOT the same event, except the control
# ---------------------------------------------------------------------------

_THRESHOLD_SUBJECTS = ("Bitcoin", "Ethereum", "Solana", "gold", "silver")
_THRESHOLD_CLAIMS = ("closes above", "trades above", "settles above")
#: Strike pool. **2000 is here because the gate found the hazard and the worlds had not.** A
#: year-like strike was reachable only as arithmetic inside ``threshold_mismatch`` (2500 x 0.8), so
#: the control never carried one and could not have detected that such strikes were being deleted.
#: A control that does not contain the hypothesis cannot falsify it (``docs/CORRECTIONS.md`` Pass 3).
_THRESHOLDS = (2000.0, 2500.0, 5000.0, 25000.0, 75000.0, 100000.0)
_PRICE_SOURCES = ("the primary spot index", "the reference exchange rate",
                  "the settlement auction print")

_EVENT_SUBJECTS = ("Candidate Alpha", "Candidate Bravo", "the Northern party", "the Coastal party")
_EVENT_CLAIMS = ("wins the presidential election", "wins the popular vote",
                 "wins a majority of seats", "controls the upper chamber")
_EVENT_SOURCES = ("the official certified count", "the returning officer declaration",
                  "the national canvass board")

_TIMES = ("12:00", "16:00", "21:00", "23:59")
_DATES = ("2026-11-03", "2026-12-31", "2027-01-20", "2027-03-31", "2027-06-30", "2027-11-02")


def _random_identity(seed: int, *, kind: str = "any") -> EventIdentity:
    rng = random.Random(seed)
    if kind == "any":
        kind = rng.choice(("threshold", "event"))
    if kind == "threshold":
        subject = rng.choice(_THRESHOLD_SUBJECTS)
        claim = rng.choice(_THRESHOLD_CLAIMS)
        threshold: float | None = rng.choice(_THRESHOLDS)
        source = rng.choice(_PRICE_SOURCES)
    else:
        subject = rng.choice(_EVENT_SUBJECTS)
        claim = rng.choice(_EVENT_CLAIMS)
        threshold = None
        source = rng.choice(_EVENT_SOURCES)
    # A quarter of identities are themselves negations, so the control also tests that NOT-X pairs
    # with NOT-X. A matcher that only ever sees affirmative markets never exercises polarity.
    return EventIdentity(subject, claim, threshold, rng.choice(_DATES), rng.choice(_TIMES),
                         source, negated=rng.random() < 0.25,
                         modality=rng.choice(("deadline", "instant")))


def _shift_date(iso: str, days: int) -> str:
    return (date.fromisoformat(iso) + timedelta(days=days)).isoformat()


def _pair(world: str, left: EventIdentity, right: EventIdentity, seed: int,
          truly_same: bool) -> Pair:
    return Pair(
        world=world,
        left_identity=left,
        right_identity=right,
        left=publish(left, "polymarket", seed=seed * 3 + 1, market_id=f"pm-{seed}"),
        right=publish(right, "kalshi", seed=seed * 3 + 2, market_id=f"kx-{seed}"),
        truly_same=truly_same,
    )


def _other(pool: tuple, current, rng: random.Random):
    """Draw from ``pool`` excluding ``current`` — a mismatch world must contain a mismatch."""
    alternatives = [x for x in pool if x != current]
    if not alternatives:  # pragma: no cover - every pool here has at least two members
        raise ValueError("pool has no alternative to draw")
    return rng.choice(alternatives)


def identical(seed: int) -> Pair:
    """**Positive control.** The same event, phrased as each venue phrases it."""
    ident = _random_identity(seed)
    return _pair("identical", ident, ident, seed, truly_same=True)


def horizon_mismatch(seed: int) -> Pair:
    left = _random_identity(seed)
    rng = random.Random(seed ^ 0x5A)
    right = replace(left, resolution_date=_shift_date(left.resolution_date,
                                                      rng.choice((31, 59, 90, 181))))
    return _pair("horizon_mismatch", left, right, seed, truly_same=False)


def threshold_mismatch(seed: int) -> Pair:
    left = _random_identity(seed, kind="threshold")
    rng = random.Random(seed ^ 0x5B)
    assert left.threshold is not None
    right = replace(left, threshold=left.threshold * rng.choice((0.8, 1.2, 1.5)))
    return _pair("threshold_mismatch", left, right, seed, truly_same=False)


def scope_mismatch(seed: int) -> Pair:
    left = _random_identity(seed)
    rng = random.Random(seed ^ 0x5C)
    pool = _THRESHOLD_CLAIMS if left.threshold is not None else _EVENT_CLAIMS
    return _pair("scope_mismatch", left, replace(left, claim=_other(pool, left.claim, rng)),
                 seed, truly_same=False)


def source_mismatch(seed: int) -> Pair:
    left = _random_identity(seed)
    rng = random.Random(seed ^ 0x5D)
    pool = _PRICE_SOURCES if left.threshold is not None else _EVENT_SOURCES
    return _pair("source_mismatch", left, replace(left, source=_other(pool, left.source, rng)),
                 seed, truly_same=False)


def settlement_time_mismatch(seed: int) -> Pair:
    """Same day, different clock time. The discriminating null.

    Every other mismatch here is visible to a crude check. This one agrees on all five pieces of
    evidence Gate C froze, and is refused only by comparing the settlement *instant*.
    """
    left = _random_identity(seed)
    rng = random.Random(seed ^ 0x5E)
    right = replace(left, settlement_time=_other(_TIMES, left.settlement_time, rng))
    return _pair("settlement_time_mismatch", left, right, seed, truly_same=False)


def negation_pair(seed: int) -> Pair:
    """X on one venue, NOT-X on the other. Complements, not identities — pairing them inverts a
    sign, which is worse than a missed trade because it converts a hedge into a double position."""
    left = _random_identity(seed)
    return _pair("negation_pair", left, replace(left, negated=not left.negated), seed,
                 truly_same=False)


def random_pairing(seed: int) -> Pair:
    """Unrelated markets: the floor case.

    Resampled until the two are genuinely different, because a coincidental collision from small
    draw pools is a *true* pair that happens to live in this world, not an instance of it.
    """
    left = _random_identity(seed)
    right = _random_identity(seed + 7919)
    for bump in range(1, 40):
        if not same_event_oracle(left, right).paired:
            break
        right = _random_identity(seed + 7919 + bump * 104_729)
    return _pair("random_pairing", left, right, seed, truly_same=False)



def modality_mismatch(seed: int) -> Pair:
    """*"by T"* against *"at T"*: a barrier and a digital, sharing a timestamp.

    Registered in Gate C2 as the seventh piece of evidence. This world agrees on **all six**
    previously registered fields, so it is the discriminating null for the prose extractor exactly
    as the settlement-time world was for the structured one.
    """
    left = _random_identity(seed)
    other = "instant" if left.modality == "deadline" else "deadline"
    return _pair("modality_mismatch", left, replace(left, modality=other), seed, truly_same=False)


def prose_contradiction(seed: int) -> Pair:
    """The rules text states a time the close timestamp contradicts.

    Not a mismatch *between* venues but a mismatch *within* one, and it must refuse: a pipeline that
    trusts either source alone passes this world by accident while remaining wrong about which
    instant it is trading. Built by publishing the right-hand market from one identity and then
    overwriting its structured timestamp with another one's.
    """
    left = _random_identity(seed)
    rng = random.Random(seed ^ 0x5F)
    pair = _pair("prose_contradiction", left, left, seed, truly_same=False)
    skewed = _other(_TIMES, left.settlement_time, rng)
    corrupted = RawMarket(pair.right.venue, pair.right.market_id, pair.right.title,
                          pair.right.rules, f"{left.resolution_date}T{skewed}:00+00:00")
    return Pair("prose_contradiction", left, replace(left, settlement_time=skewed),
                pair.left, corrupted, truly_same=False)


#: The registered null worlds, in registration order: Gate C's seven plus Gate C2's two.
NULL_WORLDS = (
    ("horizon_mismatch", horizon_mismatch),
    ("threshold_mismatch", threshold_mismatch),
    ("scope_mismatch", scope_mismatch),
    ("source_mismatch", source_mismatch),
    ("settlement_time_mismatch", settlement_time_mismatch),
    ("negation_pair", negation_pair),
    ("random_pairing", random_pairing),
    ("modality_mismatch", modality_mismatch),
    ("prose_contradiction", prose_contradiction),
)

CONTROL_WORLD = ("identical", identical)

WORLDS = (CONTROL_WORLD,) + NULL_WORLDS


def build_pair(world: str, seed: int) -> Pair:
    for name, builder in WORLDS:
        if name == world:
            return builder(seed)
    raise KeyError(f"unknown world {world!r}")
