# System One Decision Model Final Evaluation — 2026-10-06

## Executive Summary

The Engineering Routing decision-model search is complete.

Selected candidate:

```text
Cloudflare hosted Clef-Flash
threshold = 0.50
```

It is the only evaluated candidate that simultaneously achieved:

1. 100% raw accuracy on an untouched fresh holdout
2. a one-sided exact 95% accepted-risk upper bound <= 1% for one predeclared policy
3. sub-second median latency suitable for interactive routing

Recommended architecture:

```text
Tier 0: deterministic rule / exact local logic
    ↓ unresolved
Tier 1: Cloudflare hosted Clef-Flash
        confidence >= 0.50 → accept
    ↓ confidence < 0.50 / unavailable / quota exhausted
Tier 2+: existing stronger fallback LLM
```

Nimble remains the validated local quality reference but is excluded from the normal synchronous path because of ~15s median latency. Local Clef-Flash Q4_K_M is also stopped for interactive use.

## Final comparison

| Candidate | Evidence | Raw quality | Frozen-policy result | p50 | Status |
| --- | --- | ---: | --- | ---: | --- |
| Nimble .80 | Fresh 350 | 350/350 | 349 accepted, 0 errors, 95% upper risk **0.85%** | **15.22s** | Validated local reference |
| Laya Multilingual | Development 350 | **41.14%** | Confidence gating cannot rescue quality | **0.359s** | Reject |
| Strands Decider 2B v21 .50 | Fresh 350 | 346/350 | 325 accepted, 2 errors, upper risk **1.92%** | **3.542s** | Fresh gate FAIL / STOP |
| Cloudflare hosted Clef-Flash .50 | Fresh 350 | **350/350** | 332 accepted, 0 errors, upper risk **0.90%** | **0.183s** | **ADOPT** |
| Clef-Flash Q4_K_M / llama.cpp | Smoke only | 5/6 | Full quality validation intentionally skipped | **6.14s**, tuned **10.68s** | Interactive STOP |

## Hosted Clef-Flash validation

Frozen before measurement:

```text
provider = cloudflare-clef-flash
model = clef-flash
threshold = 0.50
max accepted risk = 1%
confidence = 95%
candidate count = 1
```

Fresh 350-case result:

```text
raw accuracy = 350/350
accepted = 332/350
coverage = 94.857%
accepted errors = 0
95% one-sided exact upper risk = 0.90%
result = PASS

p50 = 183.269ms
p95 = 611.721ms
```

This is the selected interactive decision layer.

## Cost and usage

Fresh run:

```text
350 requests
153,187 input tokens
0 output tokens
```

Cloudflare Workers AI pricing checked on 2026-10-06:

```text
@cf/cloudflare/clef-flash
$0.090 / 1M input tokens
8,182 Neurons / 1M input tokens
10,000 free Neurons/day
```

Fresh-run equivalent:

```text
~$0.0138 token-price equivalent
~1,253 Neurons
~3.58 Neurons/request
~2,790 similar requests/day within the daily free allocation
```

The request/day figure is only a rough extrapolation from this benchmark request shape.

Official references:

- https://developers.cloudflare.com/workers-ai/platform/pricing/
- https://developers.cloudflare.com/changelog/post/2026-10-01-clef-workers-ai/

## Why the search ends

- Nimble passes quality but is too slow for interactive routing.
- Laya is fast but fails routing quality.
- Strands is faster than Nimble but fails the fresh accepted-risk gate.
- Local Clef Q4 remains multi-second and explicit CPU thread tuning made it worse.
- Hosted Clef-Flash passes the fresh statistical quality gate while delivering ~183ms median latency.

The current objective therefore has a clear winner. Additional model search has low expected value unless requirements, provider economics, or model availability materially change.

## Final architecture

```text
Request
  ├─ exact deterministic decision available
  │    └─ accept locally
  │
  └─ semantic routing required
       └─ Hosted Clef-Flash .50
            ├─ confidence >= .50 → accept
            └─ confidence < .50 / error / timeout / quota → stronger fallback LLM
```

Nimble is retained for offline audit, regression comparison, and cloud-independent reference work rather than the normal synchronous path.

## Production guardrails

- always escalate below confidence 0.50
- fail to the stronger fallback on provider/network/schema errors
- record routing label, confidence, latency, and fallback reason
- revalidate if workload distribution changes materially
- revalidate after meaningful provider/model/confidence-semantic changes
- never retune on a holdout and continue to call it fresh evidence

## Final status

```text
MODEL SEARCH: CLOSED

ADOPT:
  Cloudflare hosted Clef-Flash .50

KEEP AS REFERENCE:
  Nimble .80

STOP:
  Strands Decider 2B v21
  Laya Multilingual
  Local Clef-Flash Q4_K_M for interactive routing

NEXT:
  production cascade implementation
  telemetry / fallback / rollout design
```

## Evidence

- `benchmarks/2026-10-05-nimble-single-policy-risk-fresh/`
- `benchmarks/2026-10-06-multi-provider-development/`
- `benchmarks/2026-10-06-strands-single-policy-risk-fresh/`
- `benchmarks/2026-10-06-strands-threshold-development/`
- `benchmarks/2026-10-06-cloudflare-clef-flash-development/`
- `benchmarks/2026-10-06-cloudflare-clef-flash-single-policy-risk-fresh/`
- `benchmarks/2026-10-06-clef-flash-llamacpp-q4-smoke/`
