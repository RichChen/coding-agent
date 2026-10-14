---
id: inventory_tax_api
name: Inventory tax API alignment
version: 0.1.0
purpose: Align pricing APIs with regional tax profiles and Result return convention.
pattern: Extend calculate_total/pricing helpers with tax_profile parameter and Result[T].
domains:
  - inventory
required_evidence:
  - multi_file_api
  - inventory
  - expected_files
edit_recipe:
  - Inspect pricing.py and models.py for tax/Result conventions
  - Add tax_profile parameter where tests call calculate_total(..., tax_profile=...)
  - Return Result with .ok/.value matching test assertions
anti_patterns:
  - rename only
applies_when:
  - tax
  - pricing
  - inventory
  - multi_file_api
not_applicable_when:
  - rename only
required_context:
  - expected_files
verifier: tests_pass
---
1. Read pricing helpers and test expectations for tax_profile usage.
2. Patch calculate_total signature and tax application logic.
3. Ensure Result return type matches repo convention.
