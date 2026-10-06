# Clef-Flash Q4_K_M llama.cpp smoke benchmark

## Result

The local Q4_K_M path is functional, but the first untuned CPU smoke run is still multi-second.

```text
run_id = 20261006-161951
requests = 3
decisions = 6
raw accuracy = 5/6 = 83.33%

warmup = 3862.7ms
mean = 6094.8ms
p50 = 6141.5ms
p95 = 6207.2ms
```

The only routing error was:

```text
expected = other
predicted = technical
confidence = 0.744406
```

This is the same class boundary that was difficult in the hosted smoke run, but the confidence value is different, confirming that quantized/local confidence calibration must be treated independently.

## Interpretation

The Q4_K_M runtime substantially reduces the previously observed local Clef latency, but the untuned smoke p50 remains above the interactive target.

Because System One returns zero output tokens, prompt/batch processing is the primary CPU path. Before deciding whether to stop, run one explicit CPU-thread configuration using llama.cpp `-t` and `-tb`.

Recommended final tuning check:

```bash
llama serve \
  -m ~/.cache/clef-flash-q4/Clef-Flash-Q4_K_M.gguf \
  --no-mmproj \
  --host 127.0.0.1 \
  --port 8081 \
  -t 24 \
  -tb 24
```

Then repeat the same smoke benchmark once.

Decision rule for this investigation:

- if p50 remains above 3 seconds, stop the local interactive Clef path and do not spend ~350 requests on the full development set
- if p50 falls materially below 3 seconds while quality is unchanged, continue to the 350-case development comparison
- sub-1-second p50 would be required for a serious local interactive candidate

This tuning check is performance-only; it does not change the model or decision policy.


## Thread tuning check

A single explicit CPU tuning check was run with:

```text
-t 24
-tb 24
```

Run:

```text
20261006-162301
```

Observed:

```text
raw accuracy = 5/6 = 83.33%
warmup = 11580.1ms
mean = 10564.6ms
p50 = 10682.9ms
p95 = 10907.6ms
RPS = 0.095
```

Compared with the untuned smoke:

```text
untuned p50 = 6141.5ms
24-thread p50 = 10682.9ms
regression = +4541.4ms
ratio = 1.74x slower
```

The routing outputs and confidence values were unchanged.

## Final decision

**STOP the local interactive Clef-Flash Q4_K_M investigation.**

Reason:

- untuned p50 = 6.14s
- explicit 24-thread tuning p50 = 10.68s
- both are well above the predeclared 3s stop boundary
- the tuning check made performance materially worse
- hosted Clef-Flash remains ~183ms p50 on development evidence and already passed the fresh 1% accepted-risk gate

Do not spend ~350 additional requests on the full local development set. The expected operational conclusion will not change enough to justify the CPU time.

The local Q4 model remains useful only as a research/offline fallback candidate where multi-second latency is acceptable.
