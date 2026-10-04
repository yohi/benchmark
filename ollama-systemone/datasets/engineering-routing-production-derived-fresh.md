# Engineering routing production-derived fresh dataset

## Purpose

This dataset tests the current routing policy against task shapes derived from real engineering interactions rather than synthetic benchmark templates.

It is intended to answer a different question from the earlier datasets:

- golden: can the model solve a small repeatable development set?
- validation: does a selected threshold generalize to a larger synthetic holdout?
- implementation-boundary: does implementation vocabulary attract nearby classes?
- production-derived fresh: does the same policy survive realistic request wording and task mixtures?

## Derivation

The 140 tasks are abstracted from real engineering request patterns across areas such as:

- application and framework development
- CI/CD
- cloud infrastructure
- networking
- AI/model routing
- observability
- repository review and documentation

The dataset does not copy private URLs, account identifiers, secrets, or authentication material. It preserves the engineering intent and request shape, not the original conversation identity.

Metadata records only:

- `source_family`: coarse technical/project family
- `task_shape`: coarse interaction shape
- `derivation=abstracted_from_real_request`
- `language=ja-mixed`

## Language and request shape

The dataset is Japanese-first because that reflects the actual interactive workload. English technical nouns, log fragments, commands, configuration names, and error strings remain mixed into the requests.

The set includes:

- short direct requests
- constraint-heavy requests
- logs/errors followed by a question
- multi-intent requests
- current-information research
- code/config changes
- review-only requests
- planning-only requests
- prose/documentation work
- deterministic transformations

## Distribution

| Label | Cases |
| --- | ---: |
| implementation | 30 |
| debug | 25 |
| review | 20 |
| research | 20 |
| planning | 20 |
| documentation | 15 |
| deterministic | 10 |
| **total** | **140** |

The distribution is intentionally not uniform. It approximates the relative emphasis of the observed engineering workload rather than optimizing class balance.

## Labeling rule

Label the **primary action required to satisfy the immediate request**.

Examples:

- investigate why a failure occurs, without a requested change → `debug`
- investigate and then explicitly fix/change the repository → `implementation`
- compare current official documentation or service behavior → `research`
- evaluate an existing diff/plan without editing it → `review`
- produce an ordered future approach without implementing it → `planning`
- update explanatory prose without product behavior changes → `documentation`
- mechanical extraction/sorting/calculation/command construction → `deterministic`

## Evaluation protocol

The current candidate policy was selected before this dataset:

- model: `nimble`
- threshold: `0.60`

Run:

```bash
uv run systemone-bench \
  --models nimble \
  --dataset datasets/engineering-routing-production-derived-fresh.jsonl \
  --warmup 1 \
  --iterations 1 \
  --cache-reset unload \
  --thresholds 0.55,0.60,0.65,0.70
```

The primary evaluation point is threshold 0.60.

Inspect:

1. accepted accuracy at 0.60
2. local coverage at 0.60
3. per-label accepted accuracy and coverage
4. confusion matrix
5. confidence of every raw error

If the result is used to change the threshold or routing policy, this dataset becomes development evidence. Validate the revised policy on another fresh set.
