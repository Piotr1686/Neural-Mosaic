# Contributing to NeuroMosaic

Contributions, issues, and feature requests are welcome. This is a solo project but open to collaboration.

## Development Setup

```bash
git clone https://github.com/Piotr1686/neuromosaic.git
cd neuromosaic
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pre-commit install
```

## Code Style

- Formatter: **black** (`black src/`)
- Linter: **ruff** (`ruff check src/`)
- Type hints encouraged for new functions; not required for existing code
- `pathlib.Path` for all file paths — no raw strings
- `logging.getLogger(__name__)` in all modules

## Testing

```bash
pytest tests/ -v
```

All new features should include at least one test. Run the full suite before opening a PR to make sure nothing regresses.

## Pull Request Process

1. Fork the repo and create a branch: `git checkout -b feature/your-feature-name`
2. Make your changes and add tests
3. Run `make lint` and `make test` — both must pass
4. Open a PR with a clear description of what changed and why
5. Reference any related issues in the PR description

Branch naming: `feature/`, `fix/`, `docs/`, `refactor/`

## Reporting Issues

Please include:

- OS and Python version
- GPU model and CUDA version (if applicable)
- Steps to reproduce
- Expected vs actual behaviour
- Relevant log output or error traceback

Open an issue at: https://github.com/Piotr1686/neuromosaic/issues
