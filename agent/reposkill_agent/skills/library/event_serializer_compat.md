---
id: event_serializer_compat
name: Event serializer compatibility
version: 0.2.0
purpose: Maintain backward-compatible event serialization across versions.
pattern: Support legacy payload keys while emitting versioned output.
domains:
  - events
required_evidence:
  - multi_file_api
  - expected_files
edit_recipe:
  - Inspect serializer version branches
  - Preserve legacy keys on deserialize
  - Update pipeline callers for compat paths
anti_patterns:
  - rename only
applies_when:
  - multi_file_api
  - serialization
  - deserialize
  - events
not_applicable_when:
  - rename only
required_context:
  - expected_files
verifier: tests_pass
---
1. Read serializer version handling and payload schema.
2. Patch deserialize/serialize for backward compatibility.
3. Run serialization regression tests.
