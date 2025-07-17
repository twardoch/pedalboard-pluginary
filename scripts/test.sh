#!/usr/bin/env bash
# this_file: scripts/test.sh

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

# Parse command line arguments
COVERAGE_REPORT="term-missing"
COVERAGE_FAIL_UNDER=80
VERBOSE=false
PARALLEL=false
TEST_PATTERN=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage-html)
            COVERAGE_REPORT="html"
            shift
            ;;
        --coverage-xml)
            COVERAGE_REPORT="xml"
            shift
            ;;
        --coverage-fail-under)
            COVERAGE_FAIL_UNDER="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --parallel|-p)
            PARALLEL=true
            shift
            ;;
        --pattern|-k)
            TEST_PATTERN="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --coverage-html          Generate HTML coverage report"
            echo "  --coverage-xml           Generate XML coverage report"
            echo "  --coverage-fail-under N  Fail if coverage is below N% (default: 80)"
            echo "  --verbose, -v            Verbose output"
            echo "  --parallel, -p           Run tests in parallel"
            echo "  --pattern, -k PATTERN    Run tests matching pattern"
            echo "  --help, -h               Show this help"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_step "🧪 Running test suite..."

# Build pytest command
PYTEST_ARGS=("tests/")

if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS+=("-v")
fi

if [ "$PARALLEL" = true ]; then
    PYTEST_ARGS+=("-n" "auto")
fi

if [ -n "$TEST_PATTERN" ]; then
    PYTEST_ARGS+=("-k" "$TEST_PATTERN")
fi

# Add coverage arguments
PYTEST_ARGS+=("--cov=pedalboard_pluginary")
PYTEST_ARGS+=("--cov-report=$COVERAGE_REPORT")
PYTEST_ARGS+=("--cov-fail-under=$COVERAGE_FAIL_UNDER")

# Set PYTHONPATH
export PYTHONPATH=src

print_step "📋 Test configuration:"
echo "  Coverage report: $COVERAGE_REPORT"
echo "  Coverage threshold: $COVERAGE_FAIL_UNDER%"
echo "  Verbose: $VERBOSE"
echo "  Parallel: $PARALLEL"
if [ -n "$TEST_PATTERN" ]; then
    echo "  Pattern: $TEST_PATTERN"
fi

# Run tests
print_step "🔬 Executing tests..."
pytest "${PYTEST_ARGS[@]}"

print_success "All tests passed!"

# Show coverage report location if HTML was generated
if [ "$COVERAGE_REPORT" = "html" ]; then
    print_step "📊 Coverage report generated: htmlcov/index.html"
    if command -v open &> /dev/null; then
        open htmlcov/index.html
    elif command -v xdg-open &> /dev/null; then
        xdg-open htmlcov/index.html
    fi
fi