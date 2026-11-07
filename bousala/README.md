# Bousala | بوصلة

Local academic RAG phase for Bethlehem University's Software Engineering catalog 2024–2025. This is one chat page, not a student-record or registration system. The original Streamlit starter remains at the parent directory, with its own independent index.

## Expansion status (work in progress)

This snapshot includes English-track follow-up resolution, preliminary multi-curriculum database models/migration 002, Simulation PDF inspection tooling and frontend dependencies for the planned UI upgrade. Simulation ingestion, authentication, student profiles and the expanded UI are not implemented yet. Suggested questions remain available in the existing chat.

Existing installations need `python -m alembic upgrade head` from this directory before using the updated source models, then a backend restart. Migration 002 is additive but has not been integration-tested against a live database in this snapshot; back up the dedicated database before applying it. Local credentials, PDFs, extracted reports, storage and database backups are excluded from Git.

```text
7 bundled PDFs + prerequisite CSV → source/page/row registry → chunks + structured courses
                           ↓ local SentenceTransformers embeddings
Native PostgreSQL + pgvector ← exact identifiers + normalized keywords + vector cosine → RRF
                           ↓ deterministic verified lookups / grounded local Qwen
FastAPI JSON API → React/Vite Arabic RTL chat with citations + policy cautions
```

## Native Windows setup (no Docker)

Use the existing Python 3.12 `.venv`. Run commands from this `bousala` directory:

```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe setup_local.py
```

Edit `.env` locally with your PostgreSQL connection; URL-encode reserved characters in the password. Never paste secrets into chat or commit `.env`. Native PostgreSQL 18 runs on localhost:5432; this project uses only the dedicated `bousala` database. No authentication settings are weakened. `python -m app.bootstrap` creates that database if absent, without touching other databases.

Install the official pgvector extension for your PostgreSQL version. The project vendor checkout is official pgvector v0.8.7; building on Windows needs MSVC C++ x64 tools and Windows SDK, then `nmake /F Makefile.win` and an administrator `nmake /F Makefile.win install` with `PGROOT` set to your PostgreSQL installation. See [official pgvector instructions](https://github.com/pgvector/pgvector#windows). Installing the Python `pgvector` package alone does not install the server extension.

After server extension installation:

```powershell
..\.venv\Scripts\python.exe -m app.bootstrap
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.ingest --all
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Ollama is separate and local: `ollama serve`; the already-installed model is `qwen3:1.7b`. No model is silently pulled and there is no cloud fallback. The configured multilingual embedding model uses CPU and caches downloaded weights locally. Its normalized vectors have dimension 384. Index model/dimension mismatches fail closed. A different dimension needs a fresh migrated database/schema, not silently mixed vectors.

In a second terminal:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev -- --port 5173
```

Open [local chat](http://127.0.0.1:5173). Vite proxies API requests to localhost:8000. `npm.cmd run build` type-checks and builds the UI. The production bundle needs an HTTP server/reverse proxy for `/api`; no hosting/deployment is configured.

## Data, provenance and ingestion

Only the seven supplied university PDFs and the supplied prerequisite CSV are academic evidence. FAQ/held-out JSON, implementation prompts and hackathon guides are never embedded as policy. `app.audit` can inspect every source and generate `reports/data_quality_report.json` without a database. There are 50 PDF pages, 168 course-track variants, 57 unique course/group codes and 34 transcribed prerequisite rules. Course credit values 0–4 are preserved. Optional course-list credits must not be summed as mandatory credits; the degree's elective-group requirement comes from its own catalog evidence.

PDF chunks preserve page boundaries and prose paragraph boundaries. Course rows and prerequisite relationships are atomic. The 1300-character prose target approximates 250–500 tokens for catalog English, not universally for Arabic; actual tokenizer counts are stored. No overlap is used across tables/pages; this avoids duplicate rows, with possible recall loss at prose boundaries. Tune and evaluate before changing it. Policy extraction reuses the starter's geometry-based pypdf logical-run ordering; catalog English uses PyMuPDF. OCR is absent; textless pages are flagged. Wrapped titles and other ambiguities are reported, not silently invented.

`--rebuild` reconciles this authoritative corpus transactionally; it does not drop the database. Stable hashes prevent duplicate chunks. Changed sources remove stale chunks, and ingestion invalidates generic answer cache entries. Re-ingestion currently recomputes embeddings; correctness/idempotence is prioritized over incremental speed.

CSV prerequisite citations use original program URL, course code and local CSV row, never a fabricated PDF page. Provenance is `USER_TRANSCRIBED_FROM_OFFICIAL_SITE`; screenshots are not all bundled. The policy compilation is user-assembled, collected 2026-11-07, and may contain policies originating in 2020. Every cited policy carries a recency/applicability caution. Course-plan/prerequisite conflicts, GPA example inconsistencies, old English-code differences and placeholders are documented in the quality report.

## API and privacy

`GET /health` reports database, index, embedding and Ollama readiness separately; all must pass for HTTP 200. `POST /api/chat` accepts `message`, up to six browser-local history turns, optional `english_track`. `/api/faq` exposes seed questions only, never fake frequency/answers. `/api/sources` exposes ingested provenance.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/chat -Method Post -ContentType 'application/json; charset=utf-8' -Body '{"message":"SWER381 prerequisites?"}'
```

Question events store only a hash/category/latency/refusal, not student identities or raw questions. Cache keys include normalized question, track, catalog, source revision and model/config revision. Only generic deterministic lookups are eligible; personalized/history-dependent/policy/unsupported responses are not cached. Held-out evaluation disables cache reads/writes. No transcript upload, login, student profiles, planning interface or eligibility certification exists. Cached answers still require a healthy local Ollama check. General policy generation is bounded and local; JSON API responses finish validation before return. The parent Streamlit application retains its separate token-streaming implementation.

## Tests and evaluation

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m ruff check app tests
..\.venv\Scripts\python.exe -m app.audit
```

For a configured dedicated database, set `$env:BOUSALA_TEST_DB='1'` and rerun tests to execute the real ingest-twice integration test. It reconciles the academic corpus and clears Bousala caches; use only this project's database.

```powershell
..\.venv\Scripts\python.exe -m app.evaluate --dataset quality/fact_cases.json
..\.venv\Scripts\python.exe -m app.evaluate --dataset quality/heldout_evaluation_seed.json
```

The 15 source-reviewed development cases include three negative queries. The supplied held-out set remains separate and is not ingested, served from FAQ, or used as cached answers. Its references are draft gold; the missing image and excluded future What-If case are flagged rather than fabricated. Reports contain real denominators, answers and latencies. Recall@k is source/page-hit recall for the supplied reference; precision is source/page agreement among retrieved chunks. Faithfulness remains a manual rubric, not a claimed automatic gold metric. See `reports/KNOWN_GAPS.md` for actual execution status.

## Attribution / AI disclosure

Codex drafted and tested implementation and documentation. Original PDFs are Bethlehem University material, bundled by the team; prerequisite transcriptions are team-provided and labeled accordingly. No redistribution license for those sources is asserted. PyMuPDF, PostgreSQL/pgvector, SentenceTransformers, Ollama/LangChain, React/Vite and other dependencies retain their upstream licenses; review them before redistribution (including PyMuPDF licensing). No source contents or credentials are sent to paid/cloud providers.
