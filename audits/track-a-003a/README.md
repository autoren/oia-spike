# OIA-1 Track A 003a opened acquisition audit

Gate verdict: `resource_authorization_required`.

This directory is separate from and does not modify or repackage OIA-1 v0.2.1.

Verify:

```bash
sha256sum -c OIA-1-Track-A-003a-SHA256SUMS.txt
python -m json.tool OIA-1-Track-A-003a-Frozen-Protocol.json >/dev/null
python -m json.tool OIA-1-Track-A-003a-Attempt-Provenance-Registry.json >/dev/null
python -m json.tool OIA-1-Track-A-003a-Source-Pins.json >/dev/null
```
