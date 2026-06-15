# Quick Wins — ≤1h each, zero hard dependencies, batchable into one PR

Each item is fully specified in its issue file; this list is the Phase-0 batch. None depends on a structural decision; none conflicts with later phases (where a consolidation will later subsume the area, the point fix is still worth landing now and is noted).

## Backend correctness (do first — user-visible)
1. **BUG-004** — `harnesses/registry.py:102`: `parents[3]` instead of three `.parent`s; harness config discovery works again. *(Subsumed later by DUP-002/ARCH-005 — still land now.)*
2. **BUG-003** — wrap `_parse_item` in try/except in `registry_base.load_from_yaml`; a YAML typo no longer takes the backend down.
3. **BUG-005 + BUG-017** — JSON-escape `{{message}}` substitution; wrap `extract_json_path` errors into ValueError. Custom providers survive real-world inputs.
4. **BUG-007** — pass `payload.single_model` through in `create_provider`; always serialize the flag.
5. **BUG-010** — `sanitize_error_for_client(r)` instead of `str(r)` in the three error-Result constructions.
6. **BUG-012** — thread `judge_config` into `evaluate_rag`; drop hardcoded 0.7/temperature.
7. **BUG-014** — pass `provider.api_key` into rubric generate/refine.
8. **BUG-015 + PERF-004** — rerun/delete clean up artifacts; bulk `delete()` for results.
9. **BUG-009** — `try/finally: await rag_adapter.close()` in the RAG run.

## Config/infra truthfulness
10. **INFRA-006** — rewrite `providers.yaml.example` with `default_model`, drop `purpose`.
11. **CONS-001** — fix `.env.example` (`DEFAULT_MODEL`, delete LITELLM_MODEL/API_BASE lines + vapor section) + the `provider_utils.py:50` docstring. *(Final registry-path var names may shift with ARCH-005; the deletion half is safe now.)*
12. **INFRA-003** — make `make dev` delegate to `dev.sh` (env-export divergence gone).
13. **INFRA-004** — point docs targets at a real project (`uv run mkdocs -f ../docs/mkdocs.yml` interim).
14. **DOC-002 (URL half)** — fix the `github.com/eval-studio/eval-studio` clone URLs. *(The migration-step half waits for INFRA-002.)*
15. **DOC-001 (interim patch)** — minimum honest edit: WS route name, LITELLM_MODEL paragraph, prune the fictional files from the tree. *(Full rewrite scheduled Phase 4.)*

## Small cleanups
16. **DUP-001** — single `utcnow()`/`iso_now()`; delete 9 local copies.
17. **DUP-005** — one `_broadcast()` helper in progress.py.
18. **DATA-002 + DATA-004** — `tags: Mapped[list|None]`; `mapped_column("metadata", …)`.
19. **PERF-002** — cap the FE log buffer at 500.
20. **API-001** — `listRubrics` sends `page`/`page_size`.
21. **SIMP-003** — delete BuiltinHarness + factory branch. *(Its test deletions ride along — the TEST-002 dependency applies to the production-code deletion being done here, in the same change.)*
22. **SIMP-007** — delete `examples/judges/` (+ DOC-004 closes).
23. **CONS-006** — rename the ~12 outlier log event names.
24. **INFRA-007** — `ruff check --fix . && ruff format .` (one migration file); lint green again; optionally fix `script.py.mako`.
25. **INFRA-008** — fix the 5 tsc errors in store test fixtures + add a `tsc -b --noEmit` CI step; `npm run build` (and therefore the container image) works again. *Do this one first — it unblocks every docker-based verification below.*

Estimated total: ~2 focused days, net deletion positive, zero breaking API changes (everything breaking is deferred to Phase ≥1).

## Explicitly NOT quick wins (look tempting, aren't)
- **BUG-001** (resolve_model_config raise) — small diff but changes failure semantics in three services; belongs with Phase 3 or inside ARCH-001.
- **SEC-003** (pgvector identifier validation) — XS effort but deserves the SEC posture PR context.
- **FE-003** (drop WS end path) — must wait for ARCH-006, else it reintroduces the MCP leak as the only behavior.
