# AI Assistant Comparison — Makefile
# FR §12: All targets listed here.

.PHONY: run dev serve modal-deploy eval eval-light promptfoo deploy-hf install install-cloud lint test docker docker-down help

help:
	@echo "Available targets:"
	@echo "  run           Start the Streamlit app"
	@echo "  dev           Run Streamlit locally without Docker (no model server; uses CPU fallback or OSS_SERVE_URL)"
	@echo "  serve         Start the local FastAPI model server only (GPU)"
	@echo "  modal-deploy  Deploy OSS model to Modal (vLLM on A10G)"
	@echo "  eval          Run the full evaluation suite"
	@echo "  eval-light    Run a quick 9-prompt smoke-test evaluation"
	@echo "  promptfoo     Run Promptfoo evaluation (requires npx)"
	@echo "  deploy-hf     Push HF Spaces deployment to HuggingFace Hub"
	@echo "  install       Install all Python dependencies + spaCy model"
	@echo "  install-cloud Install slim Streamlit Cloud requirements (no GPU/eval stack)"
	@echo "  lint          Run ruff linter"
	@echo "  test          Run pytest test suite"
	@echo "  docker        Build image and start both services (GPU)"
	@echo "  docker-down   Stop and remove containers"

run:
	python -m streamlit run app/streamlit_app.py

dev:
	python -m streamlit run app/streamlit_app.py --server.runOnSave true

serve:
	python serve/model_server.py

modal-deploy:
	modal deploy serve/modal_server.py

eval:
	python evaluation/run_eval.py

eval-light:
	python evaluation/run_eval.py --light

promptfoo:
	npx promptfoo eval --config evaluation/promptfoo.yaml

deploy-hf:
	huggingface-cli upload deployment/hf_spaces/ $(HF_SPACE) --repo-type space

install:
	pip install -r requirements-local.txt
	python -m spacy download en_core_web_lg

install-cloud:
	pip install -r requirements.txt

lint:
	ruff check .

test:
	pytest tests/ -v

docker:
	docker compose up --build -d

docker-down:
	docker compose down
