# Disclaimer

Read this before using anything in this repository.

## This is not investment advice

Ordo Kairos is a research artifact. It reports what an instrument measured on named venues on
stated dates, and the limits of that instrument.

Nothing here is a recommendation to buy, sell, or hold any instrument, a solicitation or offer to
trade anything, an inducement to open an account anywhere, or personalised financial, legal, or tax
advice. No author of this repository is acting as your broker, adviser, or fiduciary. If you need
advice, get it from someone licensed to give it in your jurisdiction.

The measured answer here is **negative** — no tested class cleared its floor. Do not read a negative
result as a safety guarantee for anything adjacent to it. "We could not find an edge" is not "you
cannot lose money."

## Nothing here ever traded

There is no order path, no broker integration, no credential handling, and no live capital in this
project. This is enforced, not asserted: `tests/test_readme_claims.py` fails the build if any source
file acquires order placement, signing, or private-key handling.

## No warranty

Provided **as is**, without warranty of any kind, express or implied, under the terms of
[`LICENSE`](LICENSE) (Apache-2.0, §7–8). The authors accept no liability for any loss arising from
use of this code, these figures, or any decision taken in reliance on them. You run it, you own the
outcome.

Gates hit live public endpoints. Figures move between runs as the underlying universe drifts; the
`docs/*-RESULTS.md` documents record what was measured on the day and are not a live feed.

## Your jurisdiction is your responsibility

Event contracts, prediction markets, and crypto derivatives are regulated differently in every
jurisdiction, and some of the venues discussed here restrict or prohibit access by residents of
particular countries. Whether you may lawfully hold an account at any venue named in this repository
is a question for you and your counsel. This repository does not answer it and is not an invitation
to try.

## Third-party venues, trademarks, and no affiliation

Polymarket, Kalshi, Smarkets, Binance, and any other venue, product, or company named here are
trademarks of their respective owners. They are referred to **nominatively**, for identification
only, because a measurement of a specific venue is not reportable without naming it.

**This project is not affiliated with, sponsored by, endorsed by, partnered with, or authorised by
any of them.** No venue reviewed these findings before publication.

## How to read statements about venues

Every figure about a venue is an observation: what a public endpoint returned on a stated date,
under a stated method, with the method recorded so it can be disputed. Venue mechanics change — one
fee schedule changed inside a day during this work, which is a fact about how fast these markets
move, not an allegation against anyone.

**Nothing in this repository asserts that any venue acted improperly, unlawfully, or in bad faith.**
Where a figure is unfavourable, it describes market microstructure — spread, queue depth, adverse
selection, subsidy design — not conduct. Terms such as *toxic flow*, *adverse selection*, and
*recreational flow* are standard market-microstructure vocabulary describing the information content
of order flow. They are not characterisations of any venue or its customers.

Statements attributed to third-party research are the **cited authors' findings**, reported here
with attribution, and are not independent assertions by this project.

## Data use

The gates read **public, documented, unauthenticated** endpoints. No account, no credentials, no
authentication, no paywall or access-control circumvention, no order placement, and no attempt to
exceed published rate limits.

`docs/ALIGNMENT.json` and `docs/alignment-candidates.json` retain factual market identifiers and
titles — the minimum needed for a third party to reproduce a published figure rather than take it on
trust. They are a dated research sample, not a mirror, a redistribution service, or a substitute for
any venue's own data.

If you run the gates yourself, **you** are the one making those requests, and complying with each
venue's terms of service is your responsibility.

## Corrections

If you believe a figure here is wrong, or that something misrepresents you or your venue, open an
issue. This project maintains [`docs/CORRECTIONS.md`](docs/CORRECTIONS.md) — 39 recorded passes of
its own defects — and the correction process is the point of the project, not an exception to it.
