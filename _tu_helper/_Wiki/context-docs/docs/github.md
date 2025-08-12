==========================
## readme
==========================
GitHub - Репозиторий - README
--------------------------------------------
Шаблон минимального README.

```markdown
# Project Name
Short description.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage
```bash
python app.py
```
```
## actions-ci
GitHub - CI - Actions
Пример workflow для Python.

```yaml
name: CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest -q
```
