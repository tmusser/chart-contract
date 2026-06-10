# Audit Report

Summary: `PASS=3 WARN=3 FAIL=1`

- **PASS** `contract.claim.present`: Claim is declared for the spec audit.
- **WARN** `contract.source.present`: Spec is missing source/provenance metadata. Suggestion: Add spec['usermeta']['source'] to preserve provenance.
- **WARN** `labels.title.quality`: Spec title is missing or generic. Suggestion: Use a specific title tied to the claim.
- **WARN** `claim.causal_support`: Claim uses causal language without a caveat or causal evidence metadata. Suggestion: Add a caveat or spec['usermeta']['causal_evidence']=True when justified.
- **FAIL** `visual.arc.category_count`: Pie/arc chart uses 7 categories; use a sorted bar chart instead. Suggestion: Switch to a rank chart with bars for easier comparisons.
- **PASS** `readability.color.category_count`: Color encoding category count is readable.
- **PASS** `visual.integrity.decoration`: No decorative chartjunk-like spec fields detected.
