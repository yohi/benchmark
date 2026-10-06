# Strands Decider 2B v21 — single-policy 1% risk fresh holdout

## Purpose

This dataset is a new untouched validation set for one policy frozen before measurement:

```text
provider = strands-decider-2b-v21
checkpoint = StrandsAgents/strands-decider-2B-hobson-v21
confidence threshold = 0.50
maximum accepted risk = 1%
confidence level = 95%
candidate policies = 1
```

The threshold was selected on the earlier 350-case development comparison. This holdout must not be used to search or retune the threshold.

The validation question is:

> Does the predeclared Strands threshold 0.50 keep accepted risk at or below 1% on new evidence?

## Why 350 cases

For a single predeclared policy with no threshold search, a one-sided exact 95% binomial upper bound below 1% requires at least 299 accepted decisions when zero accepted errors are observed.

Development coverage at threshold 0.50 was approximately 98.3%.

A 350-case holdout therefore has enough capacity to exceed 299 accepted decisions if coverage generalizes to at least about 85.4%.

This is a sample-size design constraint, not a promise of success.

## Dataset design

`engineering-routing-strands-risk-fresh.jsonl` contains 350 cases:

| Label | Cases |
| --- | ---: |
| implementation | 50 |
| debug | 50 |
| review | 50 |
| research | 50 |
| planning | 50 |
| documentation | 50 |
| deterministic | 50 |
| **total** | **350** |

The dataset uses 25 new engineering scenario families. Every family contributes two variants for each of the seven routing actions.

Scenario families:

- Kubernetes HPA
- Terraform remote state
- RDS failover
- S3 multipart upload
- SQS DLQ redrive
- Kafka consumer rebalance
- gRPC deadline propagation
- Nginx reverse proxy behavior
- OIDC refresh-token rotation
- WebAuthn/passkeys
- systemd socket activation
- Tailscale ACL/grants
- Docker BuildKit cache mounts
- Celery retry/acknowledgement
- PostgreSQL logical replication
- Cloudflare D1 migrations
- Cloudflare R2 lifecycle
- API Gateway authorizer cache
- AWS IAM permission boundaries
- Amazon Bedrock model routing
- Vercel/Next.js cache revalidation
- Next.js Server Actions
- Supabase RLS
- GitHub repository rulesets
- Linux cgroup v2 controls

The technical context stays similar inside each family while the requested primary action changes. This stresses the routing boundary instead of merely testing keyword recognition.

## Freshness checks

The dataset has:

```text
350 rows
350 unique task texts
25 scenario families
0 exact task overlap with all prior routing datasets
0 scenario-family overlap with the previous Nimble 350-case risk holdout
```

The repository tests enforce these constraints.

## Frozen policy metadata

Every row records:

```json
{
  "provider": "strands-decider-2b-v21",
  "model": "strands-decider-2b-v21",
  "checkpoint": "StrandsAgents/strands-decider-2B-hobson-v21",
  "threshold": 0.50,
  "max_accepted_risk": 0.01,
  "confidence_level": 0.95,
  "candidate_count": 1,
  "multiple_testing_correction": "none-single-predeclared-policy"
}
```

Do not change these values after seeing model output and continue to call this dataset fresh validation evidence.

## Evaluation protocol

Start the Strands server with the same checkpoint/runtime used in development.

Then run:

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.local.json \
  --only strands-decider-2b-v21 \
  --dataset datasets/engineering-routing-strands-risk-fresh.jsonl \
  --warmup 1 \
  --iterations 1 \
  --thresholds 0.50
```

Evaluate exactly one frozen policy:

```bash
uv run systemone-risk-control \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model strands-decider-2b-v21 \
  --thresholds 0.50 \
  --max-risk 0.01 \
  --confidence-level 0.95 \
  --output results/<RUN_ID>-strands-single-policy-risk.json
```

Optionally inspect selective-confidence behavior without changing the policy:

```bash
uv run systemone-selective \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model strands-decider-2b-v21 \
  --bins 10 \
  --output results/<RUN_ID>-strands-selective.json
```

The selective analysis is diagnostic only. It must not be used to modify threshold 0.50 on this holdout.

## Pass / fail

Primary gate:

```text
one-sided exact upper accepted-risk bound <= 1%
```

Interpretation:

- **PASS** — upper risk bound <= 1%
- **FAIL — accepted risk** — observed accepted errors or the bound exceeds 1%
- **INCONCLUSIVE — sample size** — zero accepted errors but fewer accepted decisions than needed for the 1% bound

Coverage and latency are secondary.

## After the result

If the policy passes, Strands becomes a validated local replacement candidate for the current engineering-routing benchmark objective.

If it fails, preserve the result as validation evidence. Do not retune threshold 0.50 on this holdout and call it fresh again.
