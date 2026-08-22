# Track A 006c sequential-fusion outcome

## Result

The frozen 64-case held-out diagnostic completed without a generation, cap, or
instrument blocker. Closed identity, reject-aware identity, and sequential
fusion each correctly identified all 256 in-family targets.

| Method | Outside detected | False candidate ID | Outside steps | Outside resets |
|---|---:|---:|---:|---:|
| Closed identity | 17/64 | 47/64 | 160 | 0 |
| Reject-aware | 34/64 | 30/64 | 177 | 0 |
| Sequential fusion | 43/64 | 21/64 | 289 | 47 |

Sequential fusion preserved all 17 closed-policy detections by stopping before
confirmation. Among the 47 targets identified by the closed policy, the second
run added 20 detections from reject-aware novelty and 6 from disagreement
between candidate identities. The remaining 21 outside targets produced the
same false candidate identity in both runs.

The result confirms the intended composition property on this held-out corpus:
closed novelty was not traded away when the sentinel policy changed its path.
It does not eliminate open-world aliasing; agreement between two policies is
still only evidence relative to their shared finite construction.

## Intervention and reset cost

For in-family targets, sequential fusion used 1,471 intervention steps and 256
resets, exactly composing the 700 closed-policy and 771 reject-aware steps. For
outside targets, conditional stopping used 289 steps and 47 resets. Executing
both standalone policies on every outside target would use 337 steps and 64
resets, so early closed detection avoided 48 reject-aware steps and 17 resets.

The reset is not counted as an intervention step. It is separately recorded and
is a substantive applicability requirement: the second run assumes the same
target is restored exactly to its initial state. This study provides no evidence
for adapters whose resets are unavailable or unreliable.

## Paired accounting

| Closed result | Reject-aware result | Same ID | Fusion result | Cases |
|---|---|---:|---|---:|
| false ID | false ID | yes | false ID | 21 |
| false ID | false ID | no | disagreement detection | 6 |
| false ID | unsupported-output detection | no | reject detection | 8 |
| false ID | sentinel-leaf rejection | no | reject detection | 12 |
| detection | false ID | no | preserved closed detection | 3 |
| detection | unsupported-output detection | yes | preserved closed detection | 7 |
| detection | sentinel-leaf rejection | yes | preserved closed detection | 7 |

## Reproducibility

- All 64 base sets, sentinel sets, and outside targets were accepted on their
  first generation attempt; there were no generation rejections.
- Closed depths: 60 cases at depth 3 and 4 at depth 4.
- Reject-aware depths: 47 cases at depth 3 and 17 at depth 4.
- Run records: 960.
- Case-manifest SHA-256:
  `06e29472c77c5f1d0542b6eeb6843bb0a802d8198fdc43bb4cfd8e9a389c7bc7`.
- Record JSONL SHA-256:
  `b28feda465b923979821297524d174a916684d741bd298f9062df6b83776e90f`.
- Evidence SHA-256:
  `bbe1df7f1925a1db503fde0909984c0372eb6e997b70c175127c5d21742f5111`.
- Result SHA-256:
  `84764a578a26864ff45ecea2e86d4ae16f7d24ad365a809f3c15a83979a941f3`.
- An independent replay and separate processes under `PYTHONHASHSEED=0` and
  `PYTHONHASHSEED=42` regenerated both artifacts byte for byte.

## Research direction and boundary

The productive direction is now clearer: use compositional, independently
initialized probes and conservative agreement rules when reliable reset and
extra interventions are acceptable. The next substantive question is no longer
whether random sentinels can help, but how to choose contrast probes and stopping
rules under an explicit intervention/reset budget—and whether the pattern
transfers to a genuinely external executable frontier.

This remains exact evidence for one deterministic synthetic corpus. It does not
establish population-level superiority, learned ontology formation, necessary
revision, semantic novelty, external validation, sealed transfer, real ARC
performance, or Track B evidence. Track A 005e remains unexecuted pending
explicit authorization.
