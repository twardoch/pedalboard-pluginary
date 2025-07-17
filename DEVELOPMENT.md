# Development Guide

This document contains information for developers working on Pedalboard Pluginary.

## Table of Contents

- [Development Setup](#development-setup)
- [Building and Testing](#building-and-testing)
- [Release Process](#release-process)
- [Git Tag-based Versioning](#git-tag-based-versioning)
- [CI/CD Pipeline](#cicd-pipeline)
- [Binary Distribution](#binary-distribution)

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git
- Optional: `gh` CLI for GitHub integration

### Setup Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/twardoch/pedalboard-pluginary.git
   cd pedalboard-pluginary
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

### Code Quality Tools

The project uses several code quality tools:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pytest**: Testing with coverage

Run all checks:
```bash
./build.sh
```

## Building and Testing

### Local Build Script

The main build script (`build.sh`) performs:

1. ✅ Code quality checks (black, isort, flake8, mypy)
2. 🧪 Test suite execution with coverage
3. 📦 Package building
4. 🔍 Package validation
5. 🚀 Local installation and testing

```bash
./build.sh
```

### Testing

#### Run All Tests
```bash
./scripts/test.sh
```

#### Run Tests with Options
```bash
./scripts/test.sh --verbose --coverage-html --coverage-fail-under 90
```

#### Run Specific Tests
```bash
./scripts/test.sh --pattern "test_core"
```

#### Test Options
- `--coverage-html`: Generate HTML coverage report
- `--coverage-xml`: Generate XML coverage report
- `--coverage-fail-under N`: Fail if coverage is below N%
- `--verbose`: Verbose test output
- `--parallel`: Run tests in parallel
- `--pattern PATTERN`: Run tests matching pattern

### Manual Testing

Test the CLI manually:
```bash
pbpluginary --help
pbpluginary scan
pbpluginary list
```

## Release Process

### Semantic Versioning

The project uses [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH` (e.g., `1.2.3`)
- `MAJOR.MINOR.PATCH-PRERELEASE` (e.g., `1.2.3-alpha.1`)

### Creating a Release

1. Update `CHANGELOG.md` with release notes
2. Run the release script:
   ```bash
   ./scripts/release.sh 1.2.3
   ```

The release script will:
- ✅ Validate version format
- ✅ Check working directory is clean
- ✅ Run full build and test
- 🏷️ Create and push git tag
- 🚀 Trigger CI/CD pipeline

### Manual Release Steps

If you need to create a release manually:

1. Update CHANGELOG.md
2. Commit changes
3. Create and push tag:
   ```bash
   git tag -a v1.2.3 -m "Release version 1.2.3"
   git push origin v1.2.3
   ```

## Git Tag-based Versioning

The project uses `hatch-vcs` for automatic version detection from git tags:

- **Development builds**: Use commit hash and dirty state
- **Tagged builds**: Use the tag version (e.g., `v1.2.3` → `1.2.3`)
- **Version file**: Auto-generated at `src/pedalboard_pluginary/_version.py`

### Configuration

Versioning is configured in `pyproject.toml`:

```toml
[project]
dynamic = ["version"]

[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/pedalboard_pluginary/_version.py"
```

### Accessing Version at Runtime

```python
from pedalboard_pluginary import __version__
print(f"Version: {__version__}")
```

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) provides:

### Continuous Integration

**Triggered on**: Push to main, pull requests, workflow dispatch

**Jobs**:
1. **Test Matrix**: Tests on Ubuntu, Windows, macOS with Python 3.9-3.12
2. **Code Quality**: Black, isort, flake8, mypy
3. **Coverage**: Codecov integration
4. **Installation Test**: Verify CLI works

### Continuous Deployment

**Triggered on**: Git tags matching `v*`

**Jobs**:
1. **Build Python Package**: Source and wheel distributions
2. **Build Binaries**: Platform-specific executables
3. **Publish to PyPI**: Automatic PyPI release
4. **GitHub Release**: Create release with assets

### Required Secrets

Configure these secrets in GitHub repository settings:

- `PYPI_API_TOKEN`: PyPI API token for publishing
- `GITHUB_TOKEN`: Automatically available

### Optional Secrets

- `CODECOV_TOKEN`: For private repositories

## Binary Distribution

The project builds standalone binaries using PyInstaller:

### Supported Platforms

- **Linux**: `pedalboard-pluginary-linux-x64`
- **Windows**: `pedalboard-pluginary-windows-x64`
- **macOS**: `pedalboard-pluginary-macos-x64`

### Building Binaries Locally

```bash
# Install PyInstaller
pip install pyinstaller

# Build binary
pyinstaller --onefile --name pbpluginary --console src/pedalboard_pluginary/__main__.py

# Test binary
./dist/pbpluginary --help
```

### Binary Configuration

PyInstaller configuration:
- **Entry point**: `src/pedalboard_pluginary/__main__.py`
- **Mode**: Single file (`--onefile`)
- **Console**: Enabled (`--console`)
- **Name**: `pbpluginary` (Unix) or `pbpluginary.exe` (Windows)

### Binary Testing

Binaries are automatically tested in CI:

```bash
# Unix
./dist/pbpluginary --help

# Windows
.\dist\pbpluginary.exe --help
```

## Development Workflow

### Feature Development

1. Create feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```

2. Make changes and test:
   ```bash
   ./build.sh
   ```

3. Commit and push:
   ```bash
   git commit -m "Add my feature"
   git push origin feature/my-feature
   ```

4. Create pull request

### Bug Fixes

1. Create bug fix branch:
   ```bash
   git checkout -b bugfix/issue-123
   ```

2. Fix and test:
   ```bash
   ./build.sh
   ./scripts/test.sh --pattern "test_affected_area"
   ```

3. Commit and push:
   ```bash
   git commit -m "Fix issue #123"
   git push origin bugfix/issue-123
   ```

### Code Quality

Before committing, ensure:

- [ ] All tests pass
- [ ] Code is formatted (black, isort)
- [ ] No linting errors (flake8)
- [ ] Type checks pass (mypy)
- [ ] Coverage is maintained

### Testing Guidelines

- Write tests for new features
- Update tests for changed functionality
- Maintain minimum 80% test coverage
- Use descriptive test names
- Test both success and failure cases

## Troubleshooting

### Common Issues

**Version not detected correctly**:
- Ensure you're in a git repository
- Check that tags are pushed to remote
- Verify `hatch-vcs` is installed

**Build fails on code quality**:
- Run `python -m black src/pedalboard_pluginary tests/`
- Run `python -m isort src/pedalboard_pluginary tests/`
- Fix any flake8 or mypy errors

**Tests fail with import errors**:
- Ensure `PYTHONPATH=src` is set
- Install in development mode: `pip install -e .`

**Binary build fails**:
- Check PyInstaller is installed
- Verify all dependencies are available
- Check console for specific error messages

### Getting Help

- Check [GitHub Issues](https://github.com/twardoch/pedalboard-pluginary/issues)
- Review [README.md](README.md) for usage information
- Check [CHANGELOG.md](CHANGELOG.md) for recent changes