# Benchmark records

`results/` is intentionally gitignored and is the workspace for raw benchmark output.

Durable benchmark evidence is promoted explicitly into this directory. Each promoted run should contain:

- `manifest.json` — exact command, model, dataset, environment, and source run ID
- `metrics.json` — compact machine-readable metrics needed for later comparison
- `report.md` — English human-readable interpretation, decision, caveats, and next validation target
- `report.ja.md` — Japanese counterpart of the human-readable report

This split keeps transient or exploratory runs out of Git while preserving the evidence behind engineering decisions.

## Recording policy

Promote a run when it materially affects a model, threshold, architecture, or rollout decision.

Do not promote every exploratory run. Prefer one durable record per meaningful experiment or validation milestone.

The Markdown report is not a replacement for machine-readable metrics. It records **why the numbers matter** and what decision was made from them.

If a threshold is later changed using evidence from a validation record, do not keep calling that same dataset an untouched holdout. Use a fresh validation split for the revised policy.

## Recorded milestones

- `2026-10-03-tev1-golden/` — Tev1 4B baseline on the 50-case engineering-routing golden set.
- `2026-10-03-nimble-clef-golden/` — Nimble vs Clef Flash comparison that established Nimble as the stronger local candidate.
- `2026-10-04-tev1-nimble-cascade/` — offline cascade analysis comparing Tev1 → Nimble against single-model baselines.
- `2026-10-04-nimble-validation/` — 210-case holdout validation that supported Nimble threshold 0.60 as the next candidate policy.
- `2026-10-05-nimble-implementation-boundary/` — 125-case adversarial validation that preserved 100% accepted accuracy at threshold 0.60 and exposed no implementation-attractor errors.
- `2026-10-05-nimble-policy-fresh-holdout/` — balanced fresh validation that falsified the class-aware `default=0.60 / planning=0.80` candidate with a high-confidence documentation → implementation error.
- `2026-10-05-nimble-selective-confidence/` — cross-run calibration/selective-classification analysis showing weak absolute confidence calibration but strong error-ranking behavior across four Nimble runs.

The first three entries were backfilled after the recording policy was introduced. Their raw `results/` artifacts remain local and gitignored; the committed manifests, metrics, and reports preserve the observed decision-relevant evidence.
