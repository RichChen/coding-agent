---
id: config_precedence_merge
name: Config precedence merge
version: 0.2.0
purpose: Fix layered configuration merge order and override semantics.
pattern: Apply explicit overrides after defaults with correct precedence.
domains:
  - config
required_evidence:
  - context_heavy
  - expected_files
edit_recipe:
  - Trace config source layers and merge order
  - Ensure env/file overrides win over defaults
  - Add regression checks for precedence edge cases
anti_patterns:
  - typo only
applies_when:
  - context_heavy
  - config
  - merge
  - precedence
not_applicable_when:
  - typo only
required_context:
  - expected_files
verifier: tests_pass
---
1. Map configuration layers and merge entry points.
2. Fix precedence so explicit overrides apply last.
3. Run merge-order tests.
