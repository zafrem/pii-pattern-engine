# Examples

Runnable examples that use the library end-to-end.

## `detect.py` — detection with the Aho-Corasick pre-filter

A minimal reference engine: load patterns → **Aho-Corasick pre-filter** → run only
the candidate regexes → verify → resolve overlaps → report.

```bash
python examples/detect.py
```

It prints three things:

1. **Aho-Corasick spotlight** — builds a small automaton and shows a single
   linear pass finding several keywords at once.
2. **Detection on sample texts** — for each text, how many of the ~200 patterns
   the pre-filter kept as candidates (and how many it skipped), then the
   high-signal findings.
3. **Equivalence + benchmark** — proves the prefiltered findings are *identical*
   to running every regex, and times both.

The engine itself (`Detector`) is importable and is exercised by
[`tests/test_examples.py`](../tests/test_examples.py), whose headline test is the
brute-force-vs-pre-filter **equivalence** check across a range of inputs — the
empirical proof that the pre-filter only changes speed, never results.

See [../INTEGRATION.md](../INTEGRATION.md) for the full pipeline and the contracts
a production engine must honor, and [../prefilter/README.md](../prefilter/README.md)
for the pre-filter design.
