#!/usr/bin/env bash
# this_file: build.sh

set -e # Exit on error

echo "🧹 Cleaning up previous builds..."
rm -rf build/ dist/ *.egg-info .eggs/ .pytest_cache/ .coverage .tox/ .mypy_cache/

echo "🔍 Running type checks with mypy..."
python -m mypy src/pedalboard_pluginary

echo "�� Running tests..."
PYTHONPATH=src pytest tests/ -p no:flake8 -p no:briefcase

echo "📦 Building package..."
python -m build

echo "🚀 Installing locally..."
pip install -e .

echo "✨ Build and installation complete!"
