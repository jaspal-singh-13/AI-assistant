# AI Assistant Comparison — Makefile
# FR §12: All targets listed here.

.PHONY: run eval promptfoo deploy-hf install lint test docker docker-down help

help:
	@echo "Available targets:"
	@echo "  run         Start the Streamlit app (local)"
	@echo "  eval        Run the full evaluation suite"
	@echo "  promptfoo   Run Promptfoo evaluation (requires npx)"
	@echo "  deploy-hf   Push HF Spaces deployment to HuggingFace Hub"
	@echo "  install     Install all Python dependencies"
	@echo "  lint        Run ruff linter"
	@echo "  test        Run pytest test suite"
	@echo "  docker      Build image and start both services (GPU)"
	@echo "  docker-down Stop and remove containers"

run:
	streamlit run app/streamlit_app.py

eval:
	python evaluation/run_eval.py

promptfoo:
	npx promptfoo eval --config evaluation/promptfoo.yaml

deploy-hf:
	@echo "Pushing HF Spaces deployment..."
	# TODO (Phase 4): huggingface-cli upload deployment/hf_spaces/ <your-space>
	python -c "print('TODO Phase 4 — configure HF Space name in this target')"

install:
	pip install -r requirements.txt

lint:
	ruff check .

test:
	pytest tests/ -v

docker:
	docker compose up --build -d

docker-down:
	docker compose down
