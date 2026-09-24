---
id: rename_symbol_across_files
name: Rename symbol across files
version: 0.2.0
purpose: Safely rename a symbol and all call sites in the repo.
pattern: Rename definition and all references consistently across modules.
required_evidence:
  - rename
  - expected_files
edit_recipe:
  - Find symbol definition and references
  - Rename in source and tests together
  - Search for stale symbol names
anti_patterns:
  - import error only
applies_when:
  - rename
  - symbol
  - caller
not_applicable_when:
  - import error only
required_context:
  - expected_files
verifier: no_stale_symbol_references
---
1. Identify definition and all references.
2. Apply consistent rename in source and tests.
3. Run tests and search for stale symbol names.
