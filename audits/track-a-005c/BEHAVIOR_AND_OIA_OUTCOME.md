# Track A 005c behavior and OIA outcome

The unchanged exact gate returned
`maintenance_revised_separator_selected_pre_step2`.

- All 8 maintenance-normalized candidates replayed exact P0 and reproduced the
  exact common settled P1 with `RUNNING` after calibration `ACTION6`.
- Complete post-P1 traces over the 14 frozen words yielded 3 behavioral classes.
  Frozen first representatives were `R0001`, `R0005`, and `R0006`; the other
  five candidates were behavioral duplicates of `R0001` at this boundary.
- All 3 representatives passed every word under two repetitions for each of
  `PYTHONHASHSEED` 0, 1, 5, and 10.
- The exact prefix-tree adapter used only settled-frame SHA-256 and normalized
  status. OIA-1 v0.2.1 produced byte-identical reports in four processes.
- The verified minimum-worst-case adaptive policy has depth 1 and selects
  `ACTION7`; its three root observations identify all three candidates.
- The fixed preset minimum is also the one-action sequence `ACTION7`.
- Execution used 456 isolated candidate processes and 4 OIA processes, with no
  model/API call, service/network call, credential, real ARC action,
  private/sealed evaluation, or step-2-or-later payload access.

This result is prospective with respect to step 2, but it concerns candidates
that received the separately frozen missing-import maintenance. It does not
convert them into untouched model outputs, and exact P1 calibration is not a
prediction success. `ACTION7` and this full result must be merged before any
step-2 archival payload may be opened.
