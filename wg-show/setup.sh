#!/bin/bash

source .env
# uv init
# uv venv
# uv pip install -r requirements.txt
source "$WG_SHOW_DIR/.venv/bin/activate"

# Run in background and redirect output
"$WG_SHOW_DIR/.venv/bin/uvicorn" main:app --host 0.0.0.0 --port 9173 --reload --app-dir "$WG_SHOW_DIR"
