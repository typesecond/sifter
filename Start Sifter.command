#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv-sifter/bin/python ]; then
    echo "Install Sifter first; see README.md."
    read -r answer
    exit 1
fi
exec .venv-sifter/bin/python -m sifter gui
