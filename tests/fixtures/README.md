# Golden-file fixtures (2025 campaign)

These XBRL instances are the regression safety net for the validator. They are
**real, taxonomy-correct instances**, not hand-rolled XML: they were generated
by the `amsf_survey-real_estate` gem's serializer (`AmsfSurvey.to_xbrl`) so they
exercise the actual concepts, contexts, units, and dimensions the bundled
taxonomy defines. Both reference `http://amsf.mc/fr/taxonomy/strix/2025/strix.xsd`
and resolve entirely against the offline cache in `cache/`.

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

## Regenerating

The submissions that produce these instances live in the gem at
`amsf_survey-real_estate/spec/integration/arelle_validation_spec.rb` (the
"inactive entity" and "sum-of-children constraint" examples). To regenerate,
build those submissions and write `AmsfSurvey.to_xbrl(submission,
include_empty: false)` to these paths. Regenerate when the 2025 taxonomy or the
serializer changes; the test will fail if a regenerated instance no longer
matches the pinned verdict.
