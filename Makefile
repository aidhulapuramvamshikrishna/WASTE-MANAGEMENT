SHELL := /bin/bash

.PHONY: help ml-train ml-zip api web test verify

help:
	@echo "EcoSort build targets:"
	@echo "  make ml-train  - Train the default model in ml/"
	@echo "  make ml-zip    - Package ml/ code into ml.zip for Colab upload"
	@echo "  make api       - Start the FastAPI backend"
	@echo "  make web       - Start the Next.js frontend"
	@echo "  make test      - Run unit & smoke tests across all components"
	@echo "  make verify    - Run full lint, typecheck, build, and tests"

ml-train:
	cd ml && source .venv/bin/activate && python -m wasteml.train --config configs/wastenet.yaml

ml-zip:
	rm -f ml.zip
	zip -r ml.zip ml -x "ml/.venv/*" "ml/artifacts/*" "ml/.ruff_cache/*" "ml/__pycache__/*" "ml/*/__pycache__/*" "ml/*/*/__pycache__/*" "ml/.pytest_cache/*" "ml/*.egg-info/*" "ml/*/*.egg-info/*"
	@echo "Created ml.zip successfully (code only, no .venv or artifacts)"


api:
	cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

web:
	cd frontend && pnpm dev

test:
	cd ml && source .venv/bin/activate && pytest -q
	cd backend && source .venv/bin/activate && pytest -q
	cd frontend && pnpm test:e2e

verify:
	cd ml && source .venv/bin/activate && ruff check . && pytest -q
	cd backend && source .venv/bin/activate && ruff check . && pytest -q
	cd frontend && pnpm lint && pnpm typecheck && pnpm build
