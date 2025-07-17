#!/usr/bin/env bash
# this_file: scripts/release.sh

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

# Get the version from command line argument or prompt
VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 1.2.0"
    exit 1
fi

# Validate version format (basic semver check)
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
    print_error "Invalid version format. Use semantic versioning (e.g., 1.2.0)"
    exit 1
fi

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    print_error "Not in a git repository"
    exit 1
fi

# Check if working directory is clean
if ! git diff-index --quiet HEAD --; then
    print_error "Working directory is not clean. Please commit or stash changes first."
    git status
    exit 1
fi

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    print_warning "Not on main branch (currently on $CURRENT_BRANCH)"
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Release cancelled"
        exit 1
    fi
fi

# Check if tag already exists
if git tag | grep -q "^v$VERSION$"; then
    print_error "Tag v$VERSION already exists"
    exit 1
fi

print_step "🚀 Starting release process for version $VERSION"

# Update CHANGELOG.md
print_step "📝 Please update CHANGELOG.md with the new release notes"
read -p "Press Enter when CHANGELOG.md is updated..."

# Run full build and test
print_step "🔨 Running full build and test..."
./build.sh

# Create git tag
print_step "🏷️ Creating git tag v$VERSION"
git tag -a "v$VERSION" -m "Release version $VERSION"

# Show what will be pushed
print_step "📋 Changes to be pushed:"
git log --oneline HEAD~5..HEAD
echo ""
echo "Tag: v$VERSION"

# Confirm before pushing
print_warning "This will push the tag to GitHub, which will trigger the release workflow"
read -p "Do you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_error "Release cancelled"
    # Remove the tag we just created
    git tag -d "v$VERSION"
    exit 1
fi

# Push tag to trigger release
print_step "📤 Pushing tag to GitHub..."
git push origin "v$VERSION"

print_success "Release process completed!"
print_step "📋 Next steps:"
echo "  • Monitor GitHub Actions for release workflow"
echo "  • Check GitHub releases page for created release"
echo "  • Verify PyPI upload (if configured)"
echo "  • Update documentation if needed"

# Open GitHub releases page
if command -v gh &> /dev/null; then
    print_step "🌐 Opening GitHub releases page..."
    gh release view "v$VERSION" --web || echo "Release may not be created yet. Check GitHub Actions."
else
    echo "  • Install 'gh' CLI to automatically open GitHub releases"
fi