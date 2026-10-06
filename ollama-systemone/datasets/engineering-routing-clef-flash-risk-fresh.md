# Cloudflare Clef-Flash — single-policy 1% risk fresh holdout

## Purpose

This dataset is a new untouched validation set for the Clef-Flash policy frozen before measurement:

```text
provider = cloudflare-clef-flash
model = clef-flash
endpoint model = @cf/cloudflare/clef-flash
threshold = 0.50
maximum accepted risk = 1%
confidence level = 95%
candidate policies = 1
```

The threshold was selected on development evidence before this dataset existed.

Do not search or retune thresholds on this holdout and continue to call it fresh validation evidence.

## Why 350 cases

For one predeclared policy, a one-sided exact 95% binomial upper bound below 1% requires at least 299 accepted decisions when zero accepted errors are observed.

Development coverage at threshold 0.50 was:

```text
348 / 350 = 99.43%
```

A 350-case holdout therefore provides sufficient sample capacity if fresh coverage remains at least about 85.4%.

This is a sample-size design, not a guarantee that Clef-Flash will pass.

## Dataset design

`engineering-routing-clef-flash-risk-fresh.jsonl` contains 350 cases:

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

The dataset contains 25 engineering scenario families, two variants per routing label in each family.

Scenario families:

- DNSSEC rollover
- mTLS certificate rotation
- OpenAPI schema evolution
- Protocol Buffers evolution
- Prometheus cardinality
- OpenSearch shard allocation
- RabbitMQ quorum queues
- NATS JetStream
- Envoy circuit breaker/outlier detection
- Vault dynamic credentials
- AWS KMS key rotation
- SAML SSO
- SCIM provisioning
- WebSocket backpressure
- HTTP/3 QUIC fallback
- GraphQL DataLoader
- SQLite WAL
- MySQL replica lag
- DynamoDB hot partitions
- CloudFront cache keys
- Route 53 failover
- EKS IRSA
- Argo CD sync waves
- OpenTelemetry Collector
- Linux nftables

Within each scenario family, the technical context remains similar while the requested primary engineering action changes.

This is intended to stress semantic routing boundaries rather than keywords.

## Freshness guarantees

Construction checks:

```text
rows = 350
unique task texts = 350
exact task overlap with prior routing datasets = 0
scenario families = 25
scenario-family overlap with Nimble 350-case holdout = 0
scenario-family overlap with Strands 350-case holdout = 0
```

Repository tests enforce the same constraints.

## Frozen policy metadata

Every row records:

```json
{
  "provider": "cloudflare-clef-flash",
  "model": "clef-flash",
  "endpoint_model": "@cf/cloudflare/clef-flash",
  "threshold": 0.50,
  "max_accepted_risk": 0.01,
  "confidence_level": 0.95,
  "candidate_count": 1,
  "multiple_testing_correction": "none-single-predeclared-policy"
}
```

## Validation protocol

Set the same Cloudflare credentials used for development:

```bash
export CLOUDFLARE_ACCOUNT_ID='...'
export CLOUDFLARE_API_TOKEN='...'
```

Run exactly the frozen provider policy:

```bash
uv run systemone-provider-bench \
  --providers configs/decision-providers.cloudflare.json \
  --only cloudflare-clef-flash \
  --dataset datasets/engineering-routing-clef-flash-risk-fresh.jsonl \
  --warmup 1 \
  --iterations 1 \
  --thresholds 0.50
```

Then evaluate exactly one threshold:

```bash
uv run systemone-risk-control \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model cloudflare-clef-flash \
  --thresholds 0.50 \
  --max-risk 0.01 \
  --confidence-level 0.95 \
  --output results/<RUN_ID>-clef-flash-single-policy-risk.json
```

Optional diagnostic selective analysis:

```bash
uv run systemone-selective \
  --details results/<RUN_ID>-provider-details.jsonl \
  --model cloudflare-clef-flash \
  --bins 10 \
  --output results/<RUN_ID>-clef-flash-selective.json
```

Selective analysis is diagnostic only and must not be used to change the frozen threshold on this holdout.

## Primary gate

```text
one-sided exact 95% upper accepted-risk bound <= 1%
```

Interpretation:

- **PASS** — upper risk bound <= 1%
- **FAIL — accepted risk** — upper bound > 1%
- **INCONCLUSIVE — sample size** — zero accepted errors but too few accepted decisions to place the upper bound at or below 1%

Coverage and latency are secondary.

## Secondary observations

Record:

- raw routing accuracy
- class-level confusion
- p50/p95/p99 client-observed latency
- returned input-token usage
- estimated Neurons/cost
- threshold 0.50 coverage

Do not weaken the primary quality gate because hosted latency or cost is attractive.

## Methodology after the result

If threshold 0.50 passes:

- Clef-Flash becomes a validated hosted decision-layer candidate for this benchmark distribution
- preserve the policy and result as durable evidence
- still distinguish benchmark validation from production distribution shift

If threshold 0.50 fails:

- preserve the failure
- do not retune on this holdout and call the revised result fresh
- any revised Clef-Flash policy requires another untouched holdout
