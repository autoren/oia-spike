# Third-Party Notices

## CPython codec implementations used in Track A audit 002

The external audit executes incremental decoder implementations supplied by the local CPython runtime. Python software and documentation are distributed under the Python Software Foundation License Version 2, with some incorporated components under additional licenses.

- License information: <https://docs.python.org/3/license.html>
- Codec interface documentation: <https://docs.python.org/3/library/codecs.html>

No CPython source files are redistributed in this package. `external/cpython_codecs/audit_002/source_provenance.json` records the exact local source paths, sizes, canonical codec names, and SHA-256 hashes used for the audit.

## Screened but unused public MQTT model family

Automata Wiki and AALpy expose public Mealy-machine benchmark material, including MQTT models. Those model files were not incorporated because their exact source artifacts could not be acquired reproducibly in the execution runtime. The unsuccessful screen is recorded for research provenance in `external/cpython_codecs/audit_002/source_screening.json`.
