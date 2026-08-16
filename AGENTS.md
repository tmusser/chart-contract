# AGENTS.md

- Preserve the v0.1 scope in `artifacts/SPEC.md`.
- Do not add UI, dashboards, or extra chart types without updating `artifacts/SPEC.md`.
- Prefer deterministic audit rules over vague judgment.
- Keep warnings explainable.
- Do not claim causality unless evidence supports it.
- Do not mutate or fetch external data.
- Do not silently truncate quantitative scales or normalize values. For external Vega-Lite specs, require explicit `usermeta.user_requested_scale_override=true` or `usermeta.user_requested_normalization=true` before those transformations can pass the policy audit.
- Treat user-request metadata as a declaration, not proof that the user actually requested the transformation.
- A truncated quantitative bar baseline remains a visual-integrity failure even when user-request metadata is present.
- Update `artifacts/VERIFY.md` after changes.
- Update `artifacts/HANDOFF.md` before ending a session.
