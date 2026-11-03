#!/usr/bin/env bash
# Compatibility wrapper for the Python-based AWS secret loader.
exec python3 "$(dirname "$0")/get-env.py" "$@"
