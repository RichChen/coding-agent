---
id: handler_registry_api
name: Handler registry API wiring
version: 0.2.0
purpose: Wire handler modules into the global registry API.
pattern: Register handlers and expose lookup through the registry module.
domains:
  - events
required_evidence:
  - skill_heavy
  - expected_files
edit_recipe:
  - Locate registry and handler modules
  - Register handlers with stable keys
  - Verify lookup resolves registered handlers
anti_patterns:
  - typo only
applies_when:
  - skill_heavy
  - handler
  - registry
  - events
not_applicable_when:
  - typo only
required_context:
  - expected_files
verifier: tests_pass
---
1. Find registry bootstrap and handler definitions.
2. Wire registration calls with correct keys.
3. Run handler registry tests.
