.PHONY: install install-dev run index-tiles index-fonts download optimize test lint format clean

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

run:
	python -m src.gui

index-tiles:
	python -m src.indexer_smart

index-fonts:
	python -m src.indexer_typo

download:
	python -m src.fast_downloader

optimize:
	python -m src.optimizer

test:
	pytest tests/ -v

lint:
	ruff check src/ && black --check src/

format:
	black src/ && ruff check --fix src/

clean:
	rm -rf __pycache__ data/*.pkl .pytest_cache
