IMAGE ?= rag-mcp:1.0.0

.PHONY: help install dev-install test lint format clean build docker-build docker-push run run-prod

help:
	@echo "RAG MCP Service - Make targets"
	@echo ""
	@echo "Development:"
	@echo "  make install          Install production dependencies"
	@echo "  make dev-install      Install dev + production dependencies"
	@echo "  make kb               Build the knowledge base from data/docs"
	@echo "  make test             Run unit tests with coverage"
	@echo "  make test-integration Run integration tests"
	@echo "  make lint             Run all linters (mypy, pylint, isort)"
	@echo "  make format           Format code (black, isort)"
	@echo ""
	@echo "Deployment:"
	@echo "  make docker-build     Build Docker image"
	@echo "  make docker-push      Push Docker image to registry"
	@echo "  make k8s-deploy       Deploy to Kubernetes"
	@echo ""
	@echo "Operations:"
	@echo "  make run              Run service locally (dev)"
	@echo "  make run-prod         Run service locally (prod config)"
	@echo "  make health-check     Check service health"
	@echo "  make logs             Tail service logs"
	@echo "  make clean            Clean build artifacts"

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements-dev.txt
	pre-commit install

kb:
	python scripts/build_kb.py

test:
	pytest tests/unit/ --cov=src --cov-report=html
test-integration:
	pytest tests/integration/ -v

lint:
	mypy src/
	pylint src/
	isort --check-only src/

format:
	black src/ tests/
	isort src/ tests/

clean:
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/ .mypy_cache/ htmlcov/

build: clean
	python -m build

docker-build:
	docker build -t $(IMAGE) \
		-f deployment/docker/Dockerfile .

docker-push: docker-build
	docker push $(IMAGE)

k8s-deploy:
	kubectl apply -f deployment/k8s/deployment.yaml
	kubectl rollout status deployment/rag-mcp

k8s-delete:
	kubectl delete -f deployment/k8s/deployment.yaml

run:
	export RAG_ENVIRONMENT=development && \
	python -m src.main

run-prod:
	export RAG_ENVIRONMENT=production && \
	export RAG_LOG_LEVEL=INFO && \
	python -m src.main

health-check:
	curl -s http://localhost:8000/health || echo "Service not running"

logs:
	tail -f logs/rag-mcp.log

logs-error:
	tail -f logs/rag-mcp-error.log

.PHONY: help install dev-install test lint format clean build docker-build docker-push run run-prod health-check logs
