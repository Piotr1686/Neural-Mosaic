# Contributing to Neural-Mosaic

Contributions, issues, and feature requests are welcome. This is a solo project but open to collaboration.

## Reporting Bugs

Please include:

- OS and Python version
- GPU model and CUDA version (if applicable)
- Steps to reproduce
- Expected vs actual behaviour
- Relevant log output or error traceback

Open an issue at: https://github.com/Piotr1686/Neural-Mosaic/issues

## Feature Requests

Open an issue with the `enhancement` label. Describe the use case, not just the feature.

## Development Setup

```bash
git clone https://github.com/Piotr1686/Neural-Mosaic.git
cd Neural-Mosaic
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
python -m src.gui
```

> **GPU acceleration:** Install the matching [PyTorch build](https://pytorch.org/get-started/locally/) for CUDA support before running `pip install -r requirements.txt`.

## Code Style

- PEP 8 — no dedicated formatter/linter configured; standard style expected
- `pathlib.Path` for all file paths — no raw strings
- `logging.getLogger(__name__)` in all modules; `logging.basicConfig` only in entry points
- Type hints encouraged for new functions; not required for existing code

## Testing

```bash
pytest tests/ -v
```

All new features should include at least one test. Run the full suite before opening a PR.

## Pull Request Process

1. Fork the repo and create a branch: `git checkout -b feature/your-feature-name`
2. Make your changes and add tests
3. Run `pytest tests/` — must pass
4. Open a PR with a clear description of what changed and why
5. Reference any related issues in the PR description

Branch naming: `feature/`, `fix/`, `docs/`, `refactor/`
