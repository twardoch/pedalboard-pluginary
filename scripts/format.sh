#!/usr/bin/env bash
# this_file: scripts/format.sh

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

print_step "🎨 Formatting Python code..."

# Format with black
print_step "  Running black..."
python -m black src/pedalboard_pluginary tests/

# Sort imports with isort
print_step "  Running isort..."
python -m isort src/pedalboard_pluginary tests/

print_success "Code formatting complete!"

# Check if there are any changes
if git diff --quiet; then
    print_success "No changes needed - code was already formatted"
else
    print_warning "Code has been formatted. Review changes and commit if needed."
    print_step "📋 Changed files:"
    git diff --name-only
fi