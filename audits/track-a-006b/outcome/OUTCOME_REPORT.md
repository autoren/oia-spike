# Track A 006b reject-aware outcome

## Result

The frozen 64-case held-out diagnostic completed without a generation, cap, or
instrument blocker. Both native policies correctly identified all 256
in-family targets. Every closed policy was exact with worst-case depth 3 or 4;
every reject-aware policy was exact with worst-case depth 3 or 4.

For the 64 held-out targets, each globally behaviorally distinct from the four
bases and two sentinels in its case:

| Native exact policy | Outside detected | False candidate ID | Total outside steps |
|---|---:|---:|---:|
| Closed identity | 16/64 | 48/64 | 168 |
| Two-sentinel reject-aware | 29/64 | 35/64 | 185 |

Reject-aware detection comprised 14 unsupported-output `outside_model` results
and 15 explicit base-eliminated `outside_reject` leaves. The closed policy had
16 `outside_model` results. Thus the frozen reject-aware method increased
detection by 13 cases on this corpus while requiring 17 more realized outside
steps. Across in-family targets it required 777 steps versus 699, while
preserving 256/256 correct identification.

## Paired behavior

The aggregate improvement was not monotonic case by case:

| Closed result | Reject-aware result | Cases |
|---|---|---:|
| false ID | false ID | 28 |
| false ID | unsupported-output detection | 7 |
| false ID | sentinel-leaf rejection | 13 |
| detection | false ID | 7 |
| detection | unsupported-output detection | 7 |
| detection | sentinel-leaf rejection | 2 |

The reject-aware policy therefore rescued 20 closed-policy false IDs but lost 7
closed-policy detections. Sentinels change the optimal intervention path; they
do not simply add a reject branch to an otherwise identical policy.

At the closed policy's per-case maximum horizon, the reject-aware policy
detected 26 outside targets, falsely identified 32, and left 6 unresolved. It
correctly identified 222 of 256 in-family targets and left 34 unresolved, with
no incorrect identification or reject. This is a fixed maximum-depth
diagnostic, not equal realized intervention cost.

## Policy and generation accounting

- Closed depths: 62 cases at depth 3 and 2 at depth 4.
- Reject-aware depths: 45 cases at depth 3 and 19 at depth 4.
- Seventeen cases moved from closed depth 3 to reject-aware depth 4; no case
  exceeded the frozen depth cap.
- Base generation used 66 attempts: 64 accepted and 2 rejected for behavioral
  equivalence.
- Sentinel generation used 65 attempts: 64 accepted and 1 rejected for
  behavioral equivalence.
- All 64 outside targets were accepted on their first attempt.
- Run records: 960.
- Case-manifest SHA-256:
  `a8f56e7b15482d7091d8d6869462027ca050add066404b288c2f490b7454cef6`.
- Record JSONL SHA-256:
  `d99b32fe5c4fd9ad61d048eef52e20eec81a8452f1e558ee1217953da2211af2`.
- Evidence SHA-256:
  `c49fe7cc4212b70c6bba9c050295915209c16c1e3ad4cfb4bbb4244b177541c7`.
- Result SHA-256:
  `9658409934ff31b3ca06cfd82880dab61508cbce17feff38547ed4760fa99feb`.
- A clean independent replay regenerated the result and evidence byte for byte.
- Separate processes under `PYTHONHASHSEED=0` and `PYTHONHASHSEED=42` also
  regenerated both artifacts byte for byte.

## Research implication and boundary

The result supports a narrower but useful direction: a small, independently
generated contrast frontier can improve open-world rejection while preserving
native in-family soundness in this controlled family. It also shows why the
method needs refinement: the contrast set changes the policy path and can lose
previously available novelty detections, and the gain comes with added
interventions.

This is exact evidence for the frozen deterministic corpus only. It does not
establish population-level superiority, semantic novelty, learned ontology
formation, necessary revision, external validation, sealed transfer, real ARC
performance, or Track B evidence. The pending Track A 005e authorization
boundary is unchanged.
