# Master Issue Index

94 issues. Sorted by category, then ID. Status is `open` for all (lifecycle managed by the reviewer); "superseded record" in the notes column means the issue exists as a graph record and closes automatically with its superseder.

| ID | Title | Severity | Effort | Breaking | Depends on | Superseded by | Status |
|----|-------|----------|--------|----------|------------|---------------|--------|
| ARCH-001 | Q&A/Arena/RAG services are three copies of one orchestration skeleton | high | L | no | — | — | open |
| ARCH-002 | Dual provider stores; DB one dead but still shapes the codebase | high | M | yes | — | — | open |
| ARCH-003 | WS chat protocol has no single owner; FE/BE drifted | high | M | yes | — | — | open |
| ARCH-004 | API types hand-maintained in three places | medium | M | no | — | — | open |
| ARCH-005 | Two config mechanisms (Settings vs os.environ registries) | medium | S | no | — | — | open |
| ARCH-006 | Session termination has three divergent implementations | high | S | no | — | — | open |
| ARCH-007 | process_user_message is a 380-line generator owning six concerns | medium | M | no | — | — | open |
| ARCH-008 | Ad-hoc raw-SQL migrations in lifespan despite Alembic | medium | S | no | — | — | open |
| DUP-001 | _utcnow()/_iso_now() defined in eight modules | low | XS | no | — | — | open |
| DUP-002 | Registry config-path resolution ×4 (one copy wrong) | medium | S | no | — | — | open |
| DUP-003 | Fail-status boilerplate ×12 across eval services | medium | S | no | — | ARCH-001 | open |
| DUP-004 | Mode dispatch if/elif ×4 | low | XS | no | — | ARCH-001 | open |
| DUP-005 | WS broadcast + dead-connection sweep ×3 | low | XS | no | — | — | open |
| DUP-006 | Judge LLM-call boilerplate ×3 in adapter | medium | S | no | — | — | open |
| DUP-007 | Dataset+items persistence and response assembly ×4 | medium | S | no | — | — | open |
| DUP-008 | api.ts error-fallback block ×5 | low | XS | no | — | — | open |
| DUP-009 | YAML-CRUD router trio | low | M | no | — | — | open |
| DUP-010 | Provider shape declared four times | medium | M | no | ARCH-002 | — | open |
| DUP-011 | YAML/JSON schema extractors are twins | low | XS | no | — | — | open |
| DUP-012 | create_evaluation vs run_and_wait duplication | low | XS | no | — | — | open |
| CONS-001 | .env.example vs Settings drift (LITELLM_MODEL etc.) | medium | S | no | — | — | open |
| CONS-002 | Status/mode raw string literals despite enums | medium | S | no | — | — | open |
| CONS-003 | Blocking file I/O on the event loop | low | S | no | — | — | open |
| CONS-004 | List endpoints: paginated envelope vs bare array | low | S | yes | — | — | open |
| CONS-005 | 422 errors stringify Pydantic error list | low | XS | yes | — | — | open |
| CONS-006 | Log event naming mixes three conventions | trivial | S | no | — | — | open |
| CONS-007 | Defensive getattr on ORM columns | low | XS | no | — | ARCH-002 | open |
| CONS-008 | react-hook-form+zod used by exactly one component | low | M | no | — | — | open |
| BUG-001 | resolve_model_config never raises; dead guards, arena skip inoperative | high | S | no | — | — | open |
| BUG-002 | MCP servers respawned every message; processes orphaned | high | S | no | — | — | open |
| BUG-003 | Malformed YAML entry crashes whole registry load | medium | XS | no | — | — | open |
| BUG-004 | Harness registry computes repo root one level short | medium | XS | no | — | — | open |
| BUG-005 | {{message}} substituted into JSON template without escaping | high | XS | no | — | — | open |
| BUG-006 | Fresh-database startup crash (likely) | high | S | no | — | INFRA-002 | open |
| BUG-007 | POST /providers ignores single_model; value flips on reload | medium | XS | no | — | — | open |
| BUG-008 | REST end-session leaks MCP, skips evaluation completion | medium | XS | no | — | ARCH-006 | open |
| BUG-009 | HttpRAGAdapter client never closed | low | XS | no | — | — | open |
| BUG-010 | Raw exception text persisted into Result.judge_reasoning | medium | XS | no | — | — | open |
| BUG-011 | proxy_env global mutation races under concurrency | medium | M | no | — | — | open |
| BUG-012 | RAG judge hardcodes threshold/temperature | low | XS | no | — | — | open |
| BUG-013 | Judge calls ignore provider proxy/SSL | medium | S | no | — | — | open |
| BUG-014 | Rubric generate/refine never pass API key | medium | XS | no | — | — | open |
| BUG-015 | Rerun keeps stale artifacts | low | XS | no | — | — | open |
| BUG-016 | Concurrent run triggers can double-execute | low | S | no | — | — | open |
| BUG-017 | extract_json_path crashes raw on wrong paths | low | XS | no | — | — | open |
| BUG-018 | Selected evaluator is never used (decorative UI) | high | S | no | — | — | open (conflicts SIMP-002) |
| SEC-001 | Secrets inside evaluation.config leak via API + artifacts | high | M | yes | — | — | open |
| SEC-002 | WS endpoints bypass auth and origin checks | medium | S | no | — | — | open |
| SEC-003 | PgVector identifier injection | medium | XS | no | — | — | open |
| SEC-004 | SSRF-by-design without a stated trust model | medium | S | no | — | — | open |
| SEC-005 | Auth default-off, FE can't auth, 0.0.0.0 binds — undeclared posture | medium | S | no | — | — | open |
| PERF-001 | selectin eager-loads all results on every evaluation query | medium | S | no | — | — | open |
| PERF-002 | Unbounded FE log buffer; re-render per line | low | XS | no | — | — | open |
| PERF-003 | API-key check scans table + commits per request | trivial | XS | no | — | — | open |
| PERF-004 | Rerun deletes results row-by-row | trivial | XS | no | — | — | open |
| SIMP-001 | Delete the environments vertical (stubs/501s/dead infra) | high | M | yes | — | — | open |
| SIMP-002 | Delete evaluator registry machinery + selector UI | high | M | yes | — | — | open (conflicts BUG-018) |
| SIMP-003 | Delete BuiltinHarness | low | XS | no | — | — | open |
| SIMP-004 | Delete clients/ SDK+CLI (or CI-test it) | medium | M | yes | — | — | open (conflicts INFRA-005) |
| SIMP-005 | Trim unused EvaluationAdapter ABC surface | low | XS | no | — | SIMP-002 | open |
| SIMP-006 | Prune deps: asyncssh, misplaced mkdocs-material, form trio | low | S | no | — | — | open |
| SIMP-007 | Delete dead examples/judges YAMLs | low | XS | no | — | — | open |
| TEST-001 | conftest manipulates registry privates; evaluator registry not isolated | low | S | no | — | — | open |
| TEST-002 | Test files pin dead code in place | low | S | no | ARCH-002, SIMP-002, SIMP-003 | — | open |
| TEST-003 | Coverage gaps: boot, lifecycle contract, WS conformance, prod serving | medium | M | no | ARCH-001, ARCH-003, INFRA-001, INFRA-002 | — | open |
| API-001 | FE sends offset/limit; rubrics endpoint reads page/page_size | medium | XS | no | — | — | open |
| API-002 | WS session protocol drift symptom catalog | medium | S | yes | ARCH-003 | — | open |
| API-003 | FE response types lie (replay, import) | low | XS | no | — | ARCH-004 | open |
| API-004 | Phantom 'cancelled' status nothing can set | medium | S | yes | — | — | open |
| API-005 | /judges/presets returns providers with synthetic ids | low | S | yes | — | — | open |
| DATA-001 | Evaluation reference columns lack FKs | medium | S | no | — | — | open |
| DATA-002 | Dataset.tags typed dict, defaulted list | low | XS | no | — | — | open |
| DATA-003 | Naive DateTime columns vs aware values | low | S | no | — | — | open |
| DATA-004 | Legacy Column() for metadata_ | trivial | XS | no | — | — | open |
| DATA-005 | JudgeConfig vs Rubric: two tables, one concept; rubrics unwired | medium | L | yes | — | — | open |
| DATA-006 | Migration chain: 22 revisions, 2 merges, dead-table history — squash | low | S | yes | ARCH-002 | — | open |
| FE-001 | Runs started via /rerun + 200ms sleep race hack | medium | S | no | — | — | open |
| FE-002 | Cancel button only forgets the run client-side | medium | S | no | API-004 | — | open |
| FE-003 | endSession double-fires WS and REST | low | XS | no | — | — | open |
| FE-004 | Four evaluate pages re-implement one state machine | low | M | no | — | — | open |
| FE-005 | Environments page targets all-501 endpoints | low | XS | no | — | SIMP-001 | open |
| FE-006 | Chat message ids are "streaming-undefined" | medium | XS | no | — | ARCH-003 | open |
| INFRA-001 | Production frontend never served | critical | S | no | — | — | open |
| INFRA-002 | No schema creation/migration on startup | high | S | no | — | — | open |
| INFRA-003 | make dev and dev.sh divergent launchers | low | XS | no | — | — | open |
| INFRA-004 | make docs-serve runs uv in a project-less directory | low | XS | no | — | — | open |
| INFRA-005 | clients/ tests never run in CI | medium | XS | no | — | — | open (conflicts SIMP-004) |
| INFRA-006 | providers.yaml.example uses renamed/dropped fields | medium | XS | no | — | — | open |
| INFRA-007 | Backend lint red on main (5 ruff errors in one migration) | low | XS | no | — | — | open |
| INFRA-008 | Frontend build red on main (5 tsc errors in tests); container image cannot build | high | S | no | — | — | open |
| DOC-001 | CLAUDE.md describes a fictional architecture | high | S | no | — | — | open |
| DOC-002 | Setup docs omit migrations; wrong clone URL | medium | XS | no | INFRA-002 | — | open |
| DOC-003 | docs/ pages assert unbuilt capabilities | medium | XS | no | — | SIMP-001 | open |
| DOC-004 | Judge examples teach an unscorable response format | low | XS | no | — | SIMP-007 | open |

## Summary statistics

**By category:** ARCH 8 · DUP 12 · CONS 8 · BUG 18 · SEC 5 · PERF 4 · SIMP 7 · TEST 3 · API 5 · DATA 6 · FE 6 · INFRA 8 · DOC 4 — **94 total** (92 from the static passes + INFRA-007/008 from toolchain execution).

**By severity:** critical 1 · high 15 · medium 38 · low 36 · trivial 4. (Pyramid as expected.)

**Superseded graph-record issues (close automatically with their superseder, no implementation):** 11 — DUP-003, DUP-004, CONS-007, BUG-006, BUG-008, SIMP-005, API-003, FE-005, FE-006, DOC-003, DOC-004. Net issues requiring direct implementation: **83**, minus 2 lost to conflict resolution (BUG-018, INFRA-005 under the recommended resolutions) → **81**.

**Estimated effort by roadmap phase** (XS≈0.5h, S≈2h, M≈1d, L≈3d; superseded/conflict-losers excluded):
- Phase 0 quick wins: 18 issues ≈ 2 days total
- Phase 1 structural: 10 issues ≈ 12–14 days
- Phase 2 consolidation: 15 issues ≈ 7–8 days
- Phase 3 correctness/safety: 21 issues ≈ 7 days
- Phase 4 tests & docs: 8 issues ≈ 4 days
(see ROADMAP.md for assignments)

**Ten highest-leverage issues** (severity × downstream cascade):
0. **INFRA-008** — (late addition) the production image cannot even build; 5 trivial test-fixture fixes + one CI step.
1. **INFRA-001** — critical; production UI does not exist; tiny fix.
2. **ARCH-001** — closes 2, re-scopes ~9, unblocks the lifecycle test; deletes ~600 lines.
3. **SIMP-001** — ~900-line deletion, closes 2, simplifies 3 others.
4. **INFRA-002** — closes BUG-006, unblocks DOC-002/TEST-003; first-run experience.
5. **SIMP-002** — ~1,400-line deletion, closes SIMP-005, resolves the BUG-018 conflict.
6. **ARCH-002** — closes CONS-007, unblocks DUP-010/DATA-006/TEST-002; pure deletion.
7. **ARCH-003** — closes FE-006, unblocks API-002 + conformance testing; fixes live FE defect.
8. **SEC-001** — credentials currently readable via API and artifacts.
9. **DOC-001** — every future agent/contributor session starts from these premises.
10. **DATA-005** — makes the rubric feature (headline capability) actually do something.
