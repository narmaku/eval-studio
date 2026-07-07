#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/release.sh <version>
# Example: ./scripts/release.sh 0.2.0
#
# Bumps version in all locations, commits, tags, and prints the push command.
# The release workflow (.github/workflows/release.yml) handles the rest:
# changelog generation, GitHub Release creation, and container image build.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:?Usage: $0 <version>  (e.g. 0.2.0)}"

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
    echo "ERROR: '$VERSION' is not a valid semver version (expected X.Y.Z)" >&2
    exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "ERROR: Working tree is not clean. Commit or stash changes first." >&2
    exit 1
fi

BRANCH=$(git branch --show-current)
if [[ "$BRANCH" != "main" ]]; then
    echo "WARNING: You are on branch '$BRANCH', not 'main'."
    read -rp "Continue anyway? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || exit 1
fi

echo "Bumping version to $VERSION..."

sed -i "s/^version = \".*\"/version = \"$VERSION\"/" "$SCRIPT_DIR/backend/pyproject.toml"
sed -i "s/app_version: str = \".*\"/app_version: str = \"$VERSION\"/" "$SCRIPT_DIR/backend/app/core/config.py"
sed -i "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" "$SCRIPT_DIR/frontend/package.json"

grep -q "version = \"$VERSION\"" "$SCRIPT_DIR/backend/pyproject.toml" || { echo "FAILED: pyproject.toml"; exit 1; }
grep -q "app_version: str = \"$VERSION\"" "$SCRIPT_DIR/backend/app/core/config.py" || { echo "FAILED: config.py"; exit 1; }
grep -q "\"version\": \"$VERSION\"" "$SCRIPT_DIR/frontend/package.json" || { echo "FAILED: package.json"; exit 1; }

echo "  backend/pyproject.toml   -> $VERSION"
echo "  backend/app/core/config.py -> $VERSION"
echo "  frontend/package.json    -> $VERSION"

git add \
    "$SCRIPT_DIR/backend/pyproject.toml" \
    "$SCRIPT_DIR/backend/app/core/config.py" \
    "$SCRIPT_DIR/frontend/package.json"

if git diff --cached --quiet; then
    echo "  (no changes needed — already at $VERSION)"
else
    git commit -m "chore: release v$VERSION"
fi

git tag -a "v$VERSION" -m "Release v$VERSION"

echo ""
echo "Version $VERSION committed and tagged."
echo ""
echo "To trigger the release workflow, push the tag:"
echo "  git push origin main v$VERSION"
