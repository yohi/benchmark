# Strands threshold development after failed fresh validation

## Result

**STOP STRANDS**

The threshold sweep does not identify a practically useful Strands operating point under the predeclared development gate:

```text
accepted-risk target <= 1%
coverage >= 85%
```

## Sweep

Command:

```bash
uv run systemone-risk-control \
  --details results/20261006-145352-provider-details.jsonl \
  --model strands-decider-2b-v21 \
  --thresholds 0.50:0.99:0.01 \
  --max-risk 0.01 \
  --confidence-level 0.95 \
  --output results/20261006-145352-strands-threshold-development.json
```

The tool evaluated 50 candidate thresholds and applied Bonferroni correction:

```text
family alpha = 0.05
pointwise alpha = 0.001
zero-error sample requirement = 688
```

No candidate satisfies the simultaneous bound.

## Why the stop decision does not depend on Bonferroni alone

Because this is development, the sweep itself is intentionally conservative. The engineering decision was therefore checked against the equivalent frozen-single-policy risk behavior as well.

### Threshold 0.68

This is the last threshold at or above the predeclared 85% coverage cutoff:

```text
coverage = 85.43%
accepted = 299
errors = 1
```

Even if 0.68 were frozen as a single policy rather than selected from a 50-threshold family, the one-sided exact 95% upper accepted-risk bound is approximately:

```text
1.577%
```

Therefore:

```text
1.577% > 1%
FAIL
```

### Threshold 0.73

This is the first zero-error threshold:

```text
coverage = 80.00%
accepted = 280
errors = 0
```

It already fails the 85% coverage decision criterion.

Even ignoring that criterion, the single-policy zero-error 95% upper bound with 280 accepted decisions is approximately:

```text
1.064%
```

Therefore it still does not reach the 1% requirement.

## Key observation

The threshold transition is:

```text
0.68:
  coverage 85.43%
  299 accepted
  1 error

0.69-0.72:
  coverage falls below 85%
  still 1 error

0.73:
  first zero-error point
  coverage 80%
  only 280 accepted
```

There is no threshold in the observed development evidence that simultaneously offers:

```text
coverage >= 85%
and
single-policy 95% upper risk <= 1%
```

## Decision

Do not create another Strands fresh holdout.

Strands remains technically interesting because its latency is about 3.5s rather than Nimble's ~15.2s, but the coverage/risk trade-off is not strong enough to justify another validation cycle under the current objective.

Current status:

```text
Nimble .80:
  validated local quality reference

Strands 2B:
  fast
  fresh validation failed
  threshold development cannot retain >=85% coverage under the 1% risk objective
  STOP

Laya:
  rejected for routing quality
```

## Next step

Move to a different layer rather than continue retuning Strands.

The next candidate is a hosted fast decision model, starting with Cloudflare Clef-Flash. The relevant question is whether hosted Clef-Flash can preserve routing quality while reducing latency and keeping expected cost within the free/cheap-cloud budget.
