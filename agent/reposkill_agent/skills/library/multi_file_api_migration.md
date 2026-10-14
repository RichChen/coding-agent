---
id: multi_file_api_migration
name: Multi-file API migration
version: 0.2.0
purpose: Propagate API signature and convention changes across modules and tests.
pattern: Update API surface then align callers, models, and tests in one pass.
domains:
  - inventory
  - config
  - events
required_evidence:
  - multi_file_api
  - expected_files
edit_recipe:
  - Identify API entry points and dependent modules
  - Update signatures and return conventions together
  - Align tests with new API behavior
anti_patterns:
  - typo only
applies_when:
  - multi_file_api
  - api
  - signature
  - caller
not_applicable_when:
  - typo only
required_context:
  - expected_files
verifier: type_and_tests_pass
---
1. Locate API definition and all dependent modules.
2. Apply coordinated signature and behavior updates.
3. Run targeted tests for the API surface.
