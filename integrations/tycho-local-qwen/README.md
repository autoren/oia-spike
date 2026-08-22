# Tycho local-Qwen qualification

This integration freezes one opened engineering check for a genuinely useful
fallback: running Tycho through a fully local multimodal tool-use model. The
official ARC-AGI-3 Kaggle evaluator keeps its hidden games externally
custodied, but competition notebooks have internet disabled. Tycho already
supports an OpenAI-compatible local endpoint, so local-model compatibility is
the concrete execution question.

The exact Tycho source and Qwen model/projector bytes are pinned in
[`QUALIFICATION_PROTOCOL.json`](QUALIFICATION_PROTOCOL.json). One exploratory
transport call occurred before the freeze only to determine whether this route
was technically plausible. It is recorded but is not qualification evidence.

After this protocol is committed, it authorizes exactly:

- one repeated local text, image, and structured-tool transport call; and
- the upstream `configs/smoke/minimal.yaml` path on one opened public `tr87`
  game, with at most two model calls, two tool steps, two committed actions,
  and one initial reset.

The ARC toolkit may anonymously acquire the current public game source and
then executes it locally in normal mode. No registered credential, paid model
service, private game, competition submission, executable world-model
generation, or OIA run is allowed.

A pass would establish local inference and opened harness plumbing only. It
would not show that Qwen can construct or revise a useful world model, solve a
game, transfer to private games, or improve decisions. Any constructive public
smoke or externally scored evaluation needs its own later freeze.

The first two harness starts stopped before any model call, reset, or action.
The clean attempt established that the upstream `$0.50` paid-provider cost
guard refuses an unpriced local model. This is not a model or environment
failure. [`QUALIFICATION_MAINTENANCE.json`](QUALIFICATION_MAINTENANCE.json)
freezes the sole correction before retry: set the dollar cap to zero while
retaining the exact two-call and two-tool-step ceilings.

Verify the frozen protocol with:

```bash
python scripts/verify_tycho_local_qwen_qualification.py
```

The post-freeze transport driver is
`scripts/run_tycho_local_qwen_transport_smoke.py`. It rejects any non-local
endpoint, changed model identifier, non-placeholder API key, or registered
OpenAI, Anthropic, or ARC credential before importing Tycho or making the one
model call.

The maintained qualification is now complete. The local transport and opened
Tycho harness passed within the frozen limits, but the model used both public
game calls for `run_python`; Tycho therefore supplied the one recorded action
as `default (tool cap)`. See [`QUALIFICATION_REPORT.md`](QUALIFICATION_REPORT.md)
and [`QUALIFICATION_RESULT.json`](QUALIFICATION_RESULT.json). This qualifies
local plumbing only, not model-selected action execution. A larger bounded
action-selection smoke requires a new prospective freeze.
