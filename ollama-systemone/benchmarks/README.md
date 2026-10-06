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
- `2026-10-05-nimble-selective-risk-control/` — exact-binomial selective-risk-control analysis: 1% cannot be certified with the current evidence volume; 1.5% diagnostic selects threshold 0.80 with 88.29% development coverage and zero accepted errors.
- `2026-10-05-nimble-single-policy-risk-fresh/` — 350-case fresh validation of the predeclared Nimble threshold 0.80 policy. Accepted 349/350 with zero accepted errors and a 95% one-sided exact upper risk bound of 0.85%, passing the 1% gate.
- `2026-10-05-nimble-latency-tail-analysis/` — offline request-order analysis showing the 31.88s p99 is strongly prefix-concentrated: first-5 mean is 1.907× the remainder and there are zero >=1.5×-median tail events after request 20.
- `2026-10-05-nimble-warmup-stabilization/` — fixed-workload warmup comparison. Representative-7 did not improve latency; repeat-1 trials were spiky while repeat-2 trials were stable across both profiles, indicating chronological/runtime-state effects dominate warmup profile.
- `2026-10-05-nimble-warmup-process-restart/` — repeated the same warmup study with Ollama service restart before every trial. The repeat-1/repeat-2 p95 gap shrank by ~89.7% for synthetic and ~84.9% for representative, strongly implicating process-local runtime state; sparse outliers remain.
- `2026-10-06-nimble-request-telemetry/` — corrected process-tree telemetry study. Across 140 requests the >=1.25×-median spike count was 0 in every trial; no telemetry metric showed a strong latency correlation, so host tuning is not justified and latency investigation is closed for the current benchmark objective.
- `2026-10-06-multi-provider-development/` — development comparison of Laya Multilingual and Strands Decider 2B v21 on the already-consumed 350-case routing set. Laya was rejected at 41.14% raw accuracy; Strands reached 99.714% raw accuracy and 98.286% coverage with zero accepted errors at threshold 0.50 while cutting p50 latency to 3.51s, so Strands advances to a new fresh holdout.
- `2026-10-06-strands-single-policy-risk-fresh/` — untouched 350-case validation of the predeclared Strands 2B v21 threshold 0.50 policy. Fresh coverage fell to 92.857%, with 2 accepted errors among 325 accepted decisions; the canonical 95% upper risk bound was 1.92%, so the <=1% risk gate failed and Nimble remains the validated local quality reference.
- `2026-10-06-strands-threshold-development/` — post-failure threshold sweep on consumed Strands evidence. Threshold 0.68 retained 85.43% coverage but still had one error and a ~1.58% single-policy upper risk bound; the first zero-error point was threshold 0.73 at only 80% coverage and a ~1.064% upper bound. Strands investigation is stopped and the next candidate moves to hosted Clef-Flash.
- `2026-10-06-cloudflare-clef-flash-development/` — hosted Clef-Flash development run on the consumed 350-case routing set. Raw accuracy was 350/350, p50 latency 187.7ms, and frozen-candidate threshold 0.50 accepted 348/350 with zero errors and a 0.86% one-sided 95% upper risk bound. Clef-Flash advances to a new untouched fresh holdout.

The first three entries were backfilled after the recording policy was introduced. Their raw `results/` artifacts remain local and gitignored; the committed manifests, metrics, and reports preserve the observed decision-relevant evidence.
