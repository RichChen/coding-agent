---
id: repo_result_convention
name: Repo Result convention
version: 0.2.0
purpose: Align error handling with repo-wide Result-based conventions.
pattern: Replace raises/booleans with Result success/failure objects.
required_evidence:
  - repo_convention
  - expected_files
edit_recipe:
  - Find raise/boolean shortcuts in API layers
  - Return Result.ok / Result.err consistently
  - Update tests to assert Result semantics
anti_patterns:
  - rename only
applies_when:
  - repo_convention
  - result
  - convention
not_applicable_when:
  - rename only
required_context:
  - expected_files
verifier: tests_pass
---
1. Identify API paths that violate Result conventions.
2. Refactor to structured Result returns.
3. Verify tests expect Result-based errors.
