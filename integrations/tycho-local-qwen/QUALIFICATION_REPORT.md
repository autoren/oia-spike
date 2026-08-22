# Tycho local-Qwen qualification result

## Result

The bounded engineering qualification passed. The pinned Qwen model and vision
projector completed the frozen local text-image-tool transport check and then
ran through Tycho's opened `tr87-cd924810` public-game harness. The qualifying
path used a localhost OpenAI-compatible endpoint and Tycho's network-disabled
Docker sandbox. It made no paid model call, used no registered ARC credential,
opened no private game, generated no world model, ran no OIA policy, and made
no competition submission.

This removes one real engineering blocker: Tycho can use this exact local
multimodal tool-use model without relying on an online inference service.

## Exact accounting

The post-freeze transport check used one call (375 input and 169 output tokens)
and returned the required `report_transport_ok({"status":"ok"})` tool call.

The first two public-harness starts made zero model calls, resets, or actions.
They exposed a configuration mismatch: the upstream smoke profile carries a
`$0.50` paid-provider budget, while Tycho correctly refuses to assign an
unregistered dollar price to a local model. The maintenance freeze disabled
only that dollar guard. The hard two-call and two-tool-step ceilings remained
unchanged.

The maintained public run then used exactly two model calls and two
`run_python` tool steps (31,713 input and 1,554 output tokens). It stopped at
the frozen call limit after 383.91 seconds of game time. One unfinished-level
`ACTION1` environment action was recorded; no level was completed.

## Crucial limitation

The action was not selected by Qwen. Both calls were spent asking for
`run_python`, and the trace labels the recorded action as `default (tool cap)`.
Tycho supplied `ACTION1` when the two-step allowance was exhausted. This is
valid transport-and-harness evidence, but treating it as model policy evidence
would be a category error.

Accordingly, the result does not establish model-selected action execution,
game-solving ability, constructive executable-world-model generation,
ontology or mechanism discovery, prospective separator discovery, private
transfer, competition performance, or any Track B claim.

## What should happen next

The next useful test is a separately frozen action-selection smoke using the
same source, model bytes, public game, and zero-service boundary, but a modest
hard allowance large enough to let the model analyze and then explicitly
choose an environment action. Four model calls and four tool steps is a
reasonable starting hypothesis; it must be frozen before execution and is not
authorized by this result.

That test should precede any constructive world-model or evaluator-held
transfer study. Separately, packaging a roughly 31.6 GB model-plus-projector
for an internet-disabled evaluator is still unqualified: this Mac/LM Studio
run says nothing about Kaggle-compatible serving, accelerator memory headroom,
notebook image size, or submission reliability.

The compact machine-readable record, exact source and result hashes, attempt
accounting, and claim boundary are in
[`QUALIFICATION_RESULT.json`](QUALIFICATION_RESULT.json).
