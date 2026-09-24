# A5 preparation inputs

`pilot20-source-v1/private/test.parquet` is the pinned upstream SWE-bench Lite test split.
It contains oracle fields and must NEVER be mounted into an agent workspace or indexed for
target-task retrieval. Its provenance and bytes are pinned by
`configs/a5/pilot20-source-lock.json`; `README.upstream.md` is the unchanged source card.

The preparation command exports allowlisted PublicTask JSON separately from private grading
materials. This is a private-side dataset preparation area, not an agent runtime directory.
Do not promote its candidates to reviewed/validated merely because they parse successfully.
No code contained in the benchmark is executed by preparation.
