# Pre-commit Hooks Setup

This project uses pre-commit hooks to ensure code quality and automatic site generation.

## Installation

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks (run once)
pre-commit install

# Verify installation
pre-commit run --all-files
```

## What Hooks Do

### 1. Generate Site from TESTING.md
- **Trigger**: When `docs/TESTING.md` is modified
- **Action**: Runs `generate_site.py` to update `docs/index.html`
- **Benefit**: Single source of truth, automatic site updates

### 2. Lint Python Files
- **Trigger**: When any `.py` file is modified
- **Action**: Runs `make lint` for syntax checking
- **Benefit**: Prevents syntax errors in commits

### 3. Security Scan
- **Trigger**: When any `.py` file is modified
- **Action**: Runs `make security-scan` with bandit
- **Benefit**: Security vulnerability detection

## Workflow

```bash
# Developer workflow
vim docs/TESTING.md  # Update coverage numbers
git add docs/TESTING.md
git commit -m "Update coverage to 62%"
# → Pre-commit hooks run automatically
# → generate_site.py updates docs/index.html
# → Both files committed together
```

## Override Hooks (if needed)

```bash
# Skip all hooks
git commit --no-verify -m "Emergency fix"

# Skip specific hook
SKIP=generate-site git commit -m "Skip site generation"
```

## Troubleshooting

### Hook fails
```bash
# Run hooks manually to debug
pre-commit run generate-site

# Fix issues, then retry commit
git add .
git commit -m "Fixed pre-commit issues"
```

### Hook not found
```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install
```

## Benefits

- ✅ **Zero GitHub Actions overhead** - runs locally
- ✅ **Instant feedback** - developer sees results immediately  
- ✅ **Atomic commits** - both files committed together
- ✅ **No race conditions** - single operation
- ✅ **Developer control** - can override if needed
