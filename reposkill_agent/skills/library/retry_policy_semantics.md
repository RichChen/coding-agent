---
id: retry_policy_semantics
name: Retry policy semantics
version: 0.2.0
purpose: Align retry policy bounds with documented max-attempt semantics.
pattern: Fix off-by-one and zero-attempt edge cases in retry policy.
domains:
  - events
required_evidence:
  - repo_convention
  - expected_files
edit_recipe:
  - Read retry policy implementation and docs
  - Fix max-attempts and zero-edge semantics
  - Validate with policy-specific tests
anti_patterns:
  - rename only
applies_when:
  - repo_convention
  - retry
  - policy
  - events
not_applicable_when:
  - rename only
required_context:
  - expected_files
verifier: tests_pass
---
1. Inspect retry policy implementation against documented semantics.
2. Patch boundary conditions including zero attempts.
3. Run retry policy tests.
