#!/usr/bin/env bash
set -euo pipefail

uv lock
uv export --locked --format requirements-txt --no-emit-project -o requirements.txt