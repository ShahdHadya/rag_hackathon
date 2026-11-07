# Code-only repository snapshot

The running local workspace contains the input corpus, local database configuration and QA traces. They are deliberately excluded from GitHub along with `.venv`, `node_modules`, database files, credentials, PDFs, generated reports and native extension build artifacts.

To run Bousala from a fresh clone, copy `sources/`, `data/`, and `quality/` from the supplied **Bousala_RAG_Only_Starter_Pack** into `bousala/` locally, then follow `bousala/README.md`. These local input directories remain ignored by Git. Source-dependent tests require those original fixtures. Do not replace missing sources with invented policy answers.

Use the existing native PostgreSQL installation with pgvector, local Ollama, and an ignored `bousala/.env`. `.env.example` files contain configuration templates only. Never commit populated `.env` files or passwords. Reserved characters in a database password must be URL-encoded.

The parent Streamlit starter remains available independently. Bousala's minimal FastAPI/React service lives under `bousala/`. No hosting, cloud model or production deployment is configured.
