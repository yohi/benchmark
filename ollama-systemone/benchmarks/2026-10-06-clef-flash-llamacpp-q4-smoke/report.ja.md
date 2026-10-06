# Clef-Flash Q4_K_M llama.cpp Smoke Benchmark

## Result

Local Q4_K_M Pathは正常動作したが、Untuned CPU SmokeではまだMulti-second。

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

唯一のRouting Error:

```text
expected = other
predicted = technical
confidence = 0.744406
```

Hosted Smokeでも同じBoundaryが難しかったが、Confidence値は異なる。したがってQuantized / Local RuntimeのConfidence Calibrationは独立に扱う。

## Interpretation

Q4_K_Mは以前観測したLocal Clefより大幅にLatencyを短縮したが、Untuned Smoke p50はInteractive Targetをまだ超える。

System OneはOutput Token 0なのでPrompt / Batch ProcessingがCPU Pathの中心。Investigationを閉じる前に、llama.cppの `-t` / `-tb` を明示した1回だけのTuning Checkを行う。

推奨:

```bash
llama serve \
  -m ~/.cache/clef-flash-q4/Clef-Flash-Q4_K_M.gguf \
  --no-mmproj \
  --host 127.0.0.1 \
  --port 8081 \
  -t 24 \
  -tb 24
```

その後、同じSmokeを1回再実行。

Decision Rule:

- p50 > 3sのままならLocal Interactive Clef InvestigationをSTOPし、350-case Full Developmentは実行しない
- p50が3s未満へ十分改善しQualityも維持するなら350-case Developmentへ進む
- Serious Local Interactive Candidateにはp50 < 1sを目標とする

このTuning CheckはPerformanceのみで、Model / Decision Policyは変更しない。


## Thread Tuning Check

```text
-t 24
-tb 24
```

で1回だけ明示Tuningを実施。

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

Untunedとの比較:

```text
untuned p50 = 6141.5ms
24-thread p50 = 10682.9ms
regression = +4541.4ms
ratio = 1.74x slower
```

Routing Output / Confidenceは変化なし。

## Final Decision

**Local Interactive Clef-Flash Q4_K_M InvestigationはSTOP。**

理由:

- Untuned p50 = 6.14s
- 24-thread p50 = 10.68s
- どちらも事前Stop Boundaryの3sを大幅超過
- 明示Thread Tuningでさらに悪化
- Hosted Clef-FlashはDevelopmentでp50約183msかつFresh 1% Accepted-risk Gate PASS済み

したがってLocal 350-case Full Developmentを追加実行しない。

Local Q4はMulti-second Latencyを許容できるResearch / Offline Fallback用途に限定して扱う。
