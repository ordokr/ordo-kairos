# Gate N.0 — New-listing dynamics: is there room in a book nobody has quoted?

Run 2026-09-14 · `python gaten.py --pages 20 --books 120` · registration in
[`PROTOCOL.md`](PROTOCOL.md) Class N, written before the runner existed and before any spread-by-age
figure was computed.

> **VERDICT: REFUTED ON CAPACITY.** Markets under 24 hours old carry **0.11%** of flow against a
> registered floor of **5%**.
>
> **Every structural precondition of the hypothesis is true — and the opportunity is still empty.**
> Young markets are quoted **16x wider**, **93.7%** have no two-sided book at all, and the touch
> queue is **84x thinner**. Nobody trades there.

---

## 1. The hypothesis, and why it was worth testing

Every maker result in this repository is bounded by two constraints, and both belong to *established*
markets: one-tick pinning (77.4% of Polymarket flow, 73.4% of Kalshi) and queue position (Gate 3.0).
A market listed ten minutes ago has neither — no queue to be behind, no incumbent quote to fail to
improve. This was the only remaining hypothesis that attacked the binding constraint instead of
varying something around it.

## 2. By age bucket

Buckets frozen in the registration before any data was seen.

| bucket | markets | **no book** | 24h flow | **flow %** | median half-spread | median hrs to resolve |
|---|---:|---:|---:|---:|---:|---:|
| **<6h** | 2,010 | **95.9%** | $30,895 | **0.1%** | **0.080000** | 25h |
| **6–24h** | 129 | 58.9% | $684 | **0.0%** | 0.010000 | 22h |
| 1–7d | 646 | 73.7% | $2,833,570 | 9.8% | 0.005000 | 61h |
| 7–30d | 780 | 53.8% | $1,410,429 | 4.9% | 0.005000 | 108h |
| **>30d** | 1,659 | 16.6% | **$24,549,281** | **85.2%** | 0.005000 | 2,595h |

## 3. The two registered primaries

**A — spread.** Young median half-spread **0.080** against mature **0.005**: sixteen times wider.
83.6% of young flow is quoted wider than the mature median, 95% CI **[48.7%, 97.6%]** — which
technically straddles 50%, so even this half would not have passed cleanly on its own.

**B — capacity.** Markets under 24h old carry **0.11%** of flow against the registered **5%** floor.
This is the branch the registered rule checks first, and it fires by a factor of forty-five.

**C — empty books.** 93.7% of young markets have no two-sided quote, against 16.6% of mature ones.

**Queue depth**, bounded subsample of 120 split evenly across buckets:

| bucket | n | median touch size |
|---|---:|---:|
| <6h | 39 | **75** |
| 6–24h | 36 | **36** |
| >30d | 40 | **6,284** |

## 4. What this actually shows

**The mechanism is real. Every part of it.** New markets are wider, emptier, and thinner-queued than
mature ones, by large margins and in the predicted direction. A first maker there really would set
the spread and really would own the queue.

**And it does not matter, because there is no flow.** 85.2% of the venue's trading happens in markets
more than thirty days old, where the spread is one tick and the queue is 6,284 deep. The wide window
exists and closes before anyone arrives to trade in it.

This is the cleanest demonstration in the repository that **a mechanism is not an opportunity**. Nine
prior classes failed because the economics were thin or the counterparty was informed. This one fails
with the economics intact and the counterparty absent.

## 5. The confound, quantified as registered

Age and time-to-resolution correlate **+0.331** across 5,100 markets, and the bucket medians show why:
young markets resolve in **25 hours**, mature ones in **2,595**. Polymarket's constant listing is
dominated by short-dated intraday contracts — crypto up/down, daily sports — which are wide *because
they are about to resolve and nobody has priced them yet*, not because newness confers an edge.

The confound was named in the registration before the run and is not controlled away: controlling it
would be a search over specifications (A8, C7), and Gate 0b already established that this
repository's stratified machinery loses power.

## 6. Against the pre-committed expectation

| registered before the run | measured | |
|---|---|---|
| Young markets **will** be wider and emptier — "close to mechanical, and not the interesting half" | 16x wider, 93.7% empty | **correct** |
| They carry a **small share of flow**, so the gate **refutes on capacity** | 0.11% vs a 5% floor | **correct** |

First gate in four where the pre-committed expectation held in both directions. The three before it
(K.0, SM.0, and this one's spread half) all had expectations that were directionally wrong.

## 7. What this does not cover

- **Adverse selection on new listings**, which is plausibly *worse* — the first trades against a
  fresh market are the best-informed ones. Unmeasured, and it cuts against the hypothesis.
- **Inventory risk** with no other maker in the book to exit to.
- **The race to be first.** This measures the state of young books, not whether a maker could reach
  them before anyone else.
- **One cross-sectional snapshot** of surviving open markets (Pass 34.6). Markets young *now* are a
  different sample from markets young last week.
- **F3 stands.** Nothing traded, quoted, or touched capital.

## 8. Class N closes

The registered consequence of refutation on capacity is that Class N closes. It does, and with it the
last hypothesis in this repository that attacked the binding constraint rather than working around it.
