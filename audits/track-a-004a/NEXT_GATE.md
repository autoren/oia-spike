# Next gate after Track A 004a

Track A 004a closes the instrument-integration question: unchanged accepted
OIA-1 v0.2.1 can consume the admitted finite candidate behavior and return an
exact, minimum, replay-valid separator. It does not close either a real-outcome
or a prospective-discovery question.

## Recommended direction: a new held-out slice

The scientifically stronger successor is a separately numbered Track A 005a
held-out-frontier protocol. Before inspecting any candidate behavior, it should
freeze:

1. a new environment/slice selection rule and exact P0;
2. fixed candidate programs with complete provenance and hashes;
3. a candidate-independent finite action alphabet and reset semantics;
4. a mechanical adapter compiler and complete validation procedure;
5. accepted OIA v0.2.1, resource caps, deterministic serialization, and all
   allowed failure verdicts; and
6. the ordering rule that OIA's report and selected intervention are recorded
   before any real environment outcome is observed.

Candidate acquisition, adapter construction, and validation should be performed
without rendering candidate traces to the investigator. If trace construction or
prefix consistency fails, the gate should close as an engineering negative rather
than reveal partial behavior and continue under a prospective label.

This design can support a prospective claim that OIA selected a separator before
the real outcome and, with adequate blinding, discovered the separator before
human trace inspection. A real-environment result would still establish only the
bounded correspondence claim specified in that protocol.

## Lower-cost alternative: current-frontier outcome check

A Track A 004b gate could freeze `ACTION2` now and compare the two already-known
predictions with one fresh, version-matching real `ls20-9607627b` outcome. That
would test predictive correspondence and demonstrate the execution handoff, but
it could not convert this frontier into prospective separator discovery.

This alternative requires new explicit authorization for the real ARC action,
environment access, and any credentials. It must first acquire a fresh matching
P0 without post-P0 leakage, record the OIA selection before acting, execute
exactly one authorized action, and preserve the raw observation and checksums.

## Not authorized here

Neither successor is started by Track A 004a. No real ARC action, credential,
model/API call, hosted service, private/sealed evaluation, or Track B procedure is
authorized by this document.
