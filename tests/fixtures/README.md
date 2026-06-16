# Golden-file fixtures

These XBRL instances are the regression safety net for the validator. They are
**real, taxonomy-correct instances**, not hand-rolled XML: they were generated
by the `amsf_survey-real_estate` gem's serializer (`AmsfSurvey.to_xbrl`) so they
exercise the actual concepts, contexts, units, and dimensions the bundled
taxonomy defines. Each resolves entirely against the offline cache in `cache/`,
addressed by campaign year (`.../strix/<campaign_year>/strix.xsd`).

## `valid_instance.xbrl`

An **inactive entity** (`aACTIVE = Non`) carrying only the unconditionally
required fields. Validates to a clean verdict: `valid: true`, zero errors.

## `broken_instance.xbrl`

An **active entity** (`aACTIVE = Oui`) that violates the sum-of-children XULE
cross-field rule: `a1101 = 5` while `a1102 + a1103 + a1104 + a1501 + a1802TOLA
= 3 + 2 + 2 + 2 + 1 = 10 > 5`. The validator reports this as error code
`a1101-a1102-a1103-a1104-a1501-a1802TOLA-Sum`. (It also reports the
`aACTIVE = Oui`-requires-field cascade; the test pins the sum rule specifically,
not the full error set.)

## `instance_2026.xbrl`

A well-formed **2026-campaign** inactive-entity submission, referencing
`.../strix/2026/strix.xsd`. It exists to prove the campaign-year cache
addressing and per-campaign XULE ruleset selection work end-to-end: the 2026
DTS resolves offline from `cache/.../strix/2026/`, and the validator selects
`strix_2026_rules.zip` (not the 2025 ruleset).

It does **not** currently validate to a clean verdict: the 2026 XULE ruleset
has runtime errors (`abs(none)`) and spurious conditional firing. That defect
is tracked in `laurentqro/bos#18` and the clean-verdict test for 2026 is a
strict `xfail` until it is fixed gem-side. The 2026 lane's other two tests
(DTS resolves, ruleset executes) pass today.

## Regenerating

The 2025 submissions that produce `valid_instance.xbrl` and
`broken_instance.xbrl` live in the gem at
`amsf_survey-real_estate/spec/integration/arelle_validation_spec.rb` (the
"inactive entity" and "sum-of-children constraint" examples). The 2026
inactive-entity submission for `instance_2026.xbrl` mirrors the 2025 inactive
recipe at `campaign_year: 2026` plus `aNOTACTIVE`. To regenerate, build the
submission and write `AmsfSurvey.to_xbrl(submission, include_empty: false)` to
the path. Regenerate when the taxonomy or the serializer changes; the tests
fail if a regenerated instance no longer matches the pinned behavior.
