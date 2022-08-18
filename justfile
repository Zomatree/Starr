run:
    python launch.py config.toml

venv:
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
