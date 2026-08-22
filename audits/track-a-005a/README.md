# OIA-1 Track A 005a

Track A 005a starts a genuinely held-out successor to the retrospective 004a
result. Its first sub-gate selects one new game using only the headers of the
exact public archive already pinned during 003b.

Before this freeze, the archive member names were indexed. That revealed five run
roots, 25 four-character game roots per run, and complete level-1 P0 path triplets
for every run/game pair. No archive member payload, P0 bytes, candidate program,
trace, reasoning log, metadata content, or score was read.

`SOURCE_UNIVERSE_PROTOCOL.frozen.json` fixes the eligibility and hash-ranking
rule before it is executed. `ls20` is excluded because it is already opened. The
source-selection script reads tar headers only and fails closed on an identity,
path-safety, universe, or P0-path inconsistency.

Archived candidate programs are intentionally excluded from the prospective
route because they may encode post-P0 observations. After selection, the planned
route is to require one identical P0 across all five runs and generate fresh
fixed executable hypotheses locally from P0 only. The exact local model, weights,
runtime, prompts, seeds, repair policy, and caps must be frozen in a later gate
before inference.

This gate authorizes neither candidate/model/OIA execution nor a real ARC action.
It uses no credentials, hosted service, private/sealed material, or Track B
procedure.

## Source-selection result

After the freeze was merged, the header-only rule selected `su15` from 24
eligible games. `SOURCE_UNIVERSE_SELECTION.json` records the complete canonical
game universe, selection-token ranking, five exact P0 member-path triplets, and
zero payload access. P0 extraction remains a later step and did not occur during
selection.

`P0_EXTRACTION_PROTOCOL.frozen.json` defines the next narrow read: the three
level-1 reset files for `su15` in each of the five runs, and nothing else. It
requires all five copies of each file to be byte-identical before creating a
canonical P0.

## P0 result

The merged extractor subsequently read exactly 15 authorized payloads. All five
copies of each `su15` reset file were byte-identical, so the canonical 64×64 P0
is committed under [`p0/`](p0/). It exposes only actions `6` and `7`, carries a
`RESET` action input, and has `step_index` zero. No candidate, later observation,
trace, score, model, OIA, or real ARC action was accessed.

`CANDIDATE_GENERATION_PROTOCOL.frozen.json` defines the fresh hypothesis gate.
It pins the complete local Qwen3.8-27B 4-bit snapshot, MLX runtime, P0-only prompt,
eight distinct epistemic stances, greedy decoding, static acceptance contract,
and zero-repair rule. Candidate source is packaged opaquely and is not imported
or executed during generation.

## Candidate-generation result

The single frozen offline pass made eight local-model calls and recorded 8,158
output tokens. `C0006` (`discrete_mode_machine`) and `C0008`
(`skeptical_countermodel`) passed static admission; the other six responses were
rejected for failing the exact delimiter contract. No repair call was made.

The two accepted sources are committed only inside the deterministic opaque
`candidate-generation/CANDIDATE_PACKAGE.zip`. The package passed path, ordering,
timestamp, mode, identity, byte-hash, and static-AST checks. It has not been
imported or behaviorally executed. Thus the result establishes fresh P0-only
candidate-generation feasibility, not a behaviorally non-equivalent frontier.
An isolated runner and behavioral-admission protocol must be frozen and merged
before opening or executing either candidate.
