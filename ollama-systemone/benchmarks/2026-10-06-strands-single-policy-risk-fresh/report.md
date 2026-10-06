# Strands Decider 2B v21 — single-policy 1% risk fresh validation

## Result

**FAIL**

The predeclared Strands policy did not satisfy the requested accepted-risk guarantee on the untouched fresh holdout.

```text
provider = strands-decider-2b-v21
checkpoint = StrandsAgents/strands-decider-2B-hobson-v21
threshold = 0.50
maximum accepted risk = 1%
confidence level = 95%
candidate count = 1
```

## Repository validation

```text
Ran 81 tests in 0.192s
OK
```

## Fresh benchmark

Run ID:

```text
20261006-145352
```

Raw result:

```text
346 / 350 correct
accuracy = 98.8571%
errors = 4
```

Latency:

```text
mean = 3642.047ms
p50  = 3541.741ms
p90  = 3827.330ms
p95  = 4227.894ms
p99  = 5212.714ms
```

Class accuracy:

```text
debug           50/50 = 100%
deterministic   50/50 = 100%
documentation   50/50 = 100%
implementation  47/50 = 94%
planning        50/50 = 100%
research        49/50 = 98%
review          50/50 = 100%
```

Raw confusion:

```text
implementation -> planning: 3
research       -> planning: 1
```

## Frozen threshold 0.50

```text
accepted = 325 / 350
coverage = 92.8571%
accepted errors = 2
accepted accuracy = 99.3846%
empirical accepted risk = 0.6154%
```

The empirical point estimate is below 1%, but the statistical gate is not based on the point estimate.

## Canonical risk-control result

```text
Risk control: model=strands-decider-2b-v21
decisions=350
candidates=1
max_risk=0.0100
confidence=0.9500
correction=bonferroni
family alpha=0.05
pointwise alpha=0.05
zero-error sample requirement=299
```

Candidate:

```text
threshold  coverage  accepted  errors  empirical_risk  upper_risk_bound
0.50       0.9286    325       2       0.0062          0.0192
```

Canonical decision:

```text
No threshold satisfies the requested simultaneous risk bound and minimum coverage.
```

Because candidate count is one, Bonferroni leaves pointwise alpha equal to family alpha. It is numerically equivalent here to a single-policy 95% bound.

## Why this is a failure

The required gate is:

```text
one-sided exact 95% upper accepted-risk bound <= 1%
```

Observed:

```text
upper bound = 1.92%
```

Therefore:

```text
1.92% > 1.00%
FAIL
```

## Development vs fresh evidence

Development set:

```text
threshold .50
accepted = 344 / 350
coverage = 98.286%
accepted errors = 0
```

Fresh holdout:

```text
threshold .50
accepted = 325 / 350
coverage = 92.857%
accepted errors = 2
```

The fresh holdout falsifies the development hypothesis that threshold 0.50 reliably isolates Strands errors while maintaining a 1% accepted-risk guarantee.

## Interpretation

Strands is still attractive on latency:

```text
Strands p50 ≈ 3.54s
Nimble steady-state median ≈ 15.2s
approximate speedup ≈ 4.3x
```

But the speed advantage does not compensate for failure of the predeclared quality/risk requirement.

This is specifically a **risk-control failure**, not a latency failure.

## Decision

- **Nimble threshold 0.80 remains the validated local quality reference.**
- **Strands threshold 0.50 is not a validated replacement.**
- Do not raise the Strands threshold on this holdout and call the result fresh validation.
- Any revised Strands policy must treat this dataset as development evidence and use another untouched holdout.
- Laya remains rejected for routing quality.

## Next-step implication

Further Strands work is optional rather than required.

A revised higher threshold may trade local coverage for lower accepted risk, but it must be developed on already-consumed evidence and then validated on a new holdout.

Alternatively, the next investigation can move to a hosted fast decision model such as Cloudflare Clef-Flash, which targets a different latency/cost layer.
