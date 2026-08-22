# Track A 003b acquisition path-alias erratum

The first authorized acquisition pass on workflow run `32535331074` successfully downloaded and verified the pinned Zenodo archive, but selected zero candidate files.

Cause: the frozen semantic run labels were written as:

- `ewma_sv_v1.6_gpt-5.6-sol_max_run1`
- `ewma_sv_v1.6_gpt-5.6-sol_xhigh_run1`

The archive inventory uses the following directory aliases for those same two released result blocks:

- `runs_additional/ewma_v1.6_sv_gpt-5.6-sol_max_run1/ls20`
- `runs_additional/ewma_v1.6_sv_gpt-5.6-sol_xhigh_run1/ls20`

The correction changes only archive path resolution. It does not change the selected learner version, model, effort blocks, public environment, opened prefix, admission rule, behavioral boundary, or claim boundary. The zero-selection pass and its artifact remain preserved as acquisition evidence.
