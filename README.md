# Pixel FFA Auto-Chess

Deterministic, round-based FFA auto-chess prototype built with Arcade.py.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python main.py
```

## Run Tests

```bash
pytest -q
```

## Data Files

- `data/archetypes.json`
- `data/items.json`

Tune balance in data files without changing combat code.
