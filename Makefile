.PHONY: install install-dev test lint format recipe clean

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest --tb=short

lint:
	ruff check recipes common
	mypy recipes common --ignore-missing-imports

format:
	black recipes common
	ruff check --fix recipes common

recipe:
ifndef NAME
	@echo "Usage: make recipe NAME=01-tool-use"
	@exit 1
endif
	python -m recipes.$(NAME).recipe

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .ruff_cache .mypy_cache
