# Historical v0.2.0 evidence boundary

`OIA-1-v0.2.0-Frozen-Package.zip` is the exact archive previously released:

```text
0c70cd82282f91a2c4a1ec61416fbbabd7ba9566ade8527253384ceb8b28c2d3
```

The files under `external/cpython_codecs/audit_002/` in v0.2.1 remain byte-for-byte identical to their counterparts in that archive, including the frozen protocol, pre-outcome manifest, OIA report, selection record, black-box replay, and the single historical `cp437` outcome.

Audit 002's unchanged `instrument_source_provenance.json` records paths relative to the **v0.2.0 source root**. Those frozen bytes are copied under `historical/v0.2.0/instrument_sources/`. They must not be resolved against the corrected v0.2.1 source tree.

The active v0.2.1 source is separately authenticated by `maintenance/CURRENT_SOURCE_SHA256SUMS`. `maintenance/verify_provenance.py` verifies both roots and fails if they are silently conflated.
