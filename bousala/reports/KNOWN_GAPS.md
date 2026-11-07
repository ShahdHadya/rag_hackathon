# Verified state and known gaps

- Native PostgreSQL 18 and pgvector 0.8.7 installed and connected locally; initial Alembic migration executed.
- Seven academic PDFs ingested (50 pages), 57 unique course/group codes, 168 course/track rows and 34 transcribed prerequisite rules. Input corpus is intentionally excluded from the public code snapshot.
- Real ingest-twice integration test passed without duplicate chunks. The executed full suite at that point reported 15 passing tests. Later regression tests add JSON-key-order and scope-boundary coverage; see local test output for the final count.
- React TypeScript production build passed. Arabic RTL and English LTR replies were visually inspected. The degree-category JSON-key-order bug was fixed using explicit keys.
- Source-reviewed development retrieval source/page hits: 10/12; unsupported-query refusals after fixes: 3/3. These are small development-set measurements, not general accuracy claims.
- Untouched held-out evaluation was still running when the code-only publishing snapshot was prepared. No held-out metrics are invented. Local reports include per-case answers, denominators, exclusions, failed cases and measured latency when the run completes.
- General policy RAG was exercised against real sources: summer add/drop cited compiled page 15; standard course-load question cited page 7. Completeness/faithfulness still requires human review; one answer omitted the upper end of the 15–17 range.
- Policy source is a user-assembled compilation collected 2026-11-07, often reflecting pages dated 2020. Applicability is uncertain; citations carry visible cautions. This is not registration authorization.
- The supplied held-out bank includes a future What-If help case and a missing image reference; both are excluded rather than fabricated. Exact held-out questions are not ingested as evidence or served from cache.
- Automated structural citation/numeric checks do not prove semantic entailment. OCR is absent. Complex/rotated tables and wrapped course titles need review. Approximate token/paragraph splitting and the small hybrid retrieval implementation need broader evaluation.
- No student profile, login/admin portal, transcript upload, planner, What-If UI, gradebook, saved degree plans or personalized eligibility certification is implemented.
- This phase's `/api/chat` is a validated JSON response; it is not a live browser token stream. The independent parent Streamlit starter retains its token-streaming path.
- Only generic allowlisted deterministic course lookups can be cached; policy/personalized/unsupported/held-out responses are not globally cached. Question events retain hashes rather than raw personal questions.
