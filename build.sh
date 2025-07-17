#!/usr/bin/env bash
# this_file: build.sh

set -e # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    print_error "Not in a git repository"
    exit 1
fi

print_step "🧹 Cleaning up previous builds..."
rm -rf build/ dist/ *.egg-info .eggs/ .pytest_cache/ .coverage .tox/ .mypy_cache/

print_step "📋 Environment information..."
echo "Python version: $(python --version)"
echo "Current directory: $(pwd)"
echo "Git branch: $(git branch --show-current)"
echo "Git commit: $(git rev-parse --short HEAD)"

# Check if we have a git tag
if git describe --tags --exact-match HEAD > /dev/null 2>&1; then
    TAG=$(git describe --tags --exact-match HEAD)
    print_success "Building from tag: $TAG"
else
    print_warning "Not building from a tag, using version from git history"
fi

print_step "🔍 Running code quality checks..."

# Check code formatting with black
print_step "  Checking code formatting..."
if ! python -m black --check src/pedalboard_pluginary tests/; then
    print_error "Code formatting check failed. Run 'python -m black src/pedalboard_pluginary tests/' to fix."
    exit 1
fi

# Check import sorting with isort
print_step "  Checking import sorting..."
if ! python -m isort --check-only src/pedalboard_pluginary tests/; then
    print_error "Import sorting check failed. Run 'python -m isort src/pedalboard_pluginary tests/' to fix."
    exit 1
fi

# Run flake8 linting
print_step "  Running flake8 linting..."
if ! python -m flake8 src/pedalboard_pluginary tests/; then
    print_error "Linting failed"
    exit 1
fi

# Run mypy type checking
print_step "  Running type checks with mypy..."
if ! python -m mypy src/pedalboard_pluginary; then
    print_error "Type checking failed"
    exit 1
fi

print_success "Code quality checks passed"

print_step "🧪 Running tests..."
PYTHONPATH=src pytest tests/ -v --cov=pedalboard_pluginary --cov-report=term-missing --cov-report=html --cov-fail-under=80

print_success "Tests passed"

print_step "📦 Building package..."
python -m build

print_success "Package built successfully"

print_step "🔍 Checking package contents..."
python -m twine check dist/*

print_success "Package check passed"

print_step "🚀 Installing locally..."
pip install -e .

print_step "✅ Testing installation..."
if ! pbpluginary --help > /dev/null 2>&1; then
    print_error "Installation test failed - pbpluginary command not working"
    exit 1
fi

print_success "Installation test passed"

print_step "📊 Package information..."
echo "Built packages:"
ls -la dist/
echo ""
echo "Package size:"
du -h dist/*

print_success "Build and installation complete!"

# Show next steps
print_step "📋 Next steps:"
echo "  • Run tests: pytest"
echo "  • Create release: ./scripts/release.sh"
echo "  • Upload to PyPI: twine upload dist/*"