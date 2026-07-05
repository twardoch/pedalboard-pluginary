#!/usr/bin/env bash
# this_file: build.sh
# Lint, type-check, test, and build the distribution locally.

cd "$(dirname "$0")" || exit 1
set -e

echo "==> Ruff lint"
uvx ruff check src tests

echo "==> Ruff format check"
uvx ruff format --check src tests

echo "==> Tests"
uvx hatch test

echo "==> Build sdist + wheel"
uvx hatch build

echo "==> Done. Artifacts in dist/"
