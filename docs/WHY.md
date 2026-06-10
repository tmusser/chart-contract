# Why

AI-generated charts are often plausible before they are well specified. A chart can look polished while still hiding missing provenance, ambiguous units, implied filters, or causal overreach.

`chart-contract` puts a lightweight contract layer in front of the render step. The chart should declare its claim, data contract, visual intent, provenance, caveats, and the rules used to audit it.

This matters because charts are reasoning artifacts, not decorations. If the analytical contract is weak, a clean render does not make the argument trustworthy.
