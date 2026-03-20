#!/bin/bash
# OpenClaw Twins - 版本号升级脚本

set -e

VERSION_FILE="VERSION"
CURRENT_VERSION=$(cat $VERSION_FILE)

usage() {
    echo "Usage: $0 [patch|minor|major]"
    echo "Current version: $CURRENT_VERSION"
    exit 1
}

if [ $# -ne 1 ]; then
    usage
fi

BUMP_TYPE=$1

# 解析当前版本
MAJOR=$(echo $CURRENT_VERSION | cut -d. -f1)
MINOR=$(echo $CURRENT_VERSION | cut -d. -f2)
PATCH=$(echo $CURRENT_VERSION | cut -d. -f3)

# 计算新版本
case $BUMP_TYPE in
    patch)
        PATCH=$((PATCH + 1))
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    *)
        usage
        ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
NEW_TAG="v$NEW_VERSION"

echo "🔄 Bumping version: $CURRENT_VERSION → $NEW_VERSION"

# 更新 VERSION 文件
echo $NEW_VERSION > $VERSION_FILE
echo "✅ Updated $VERSION_FILE"

# 更新 CHANGELOG
echo "## [$NEW_VERSION] - $(date +%Y-%m-%d)" >> CHANGELOG.md
echo "" >> CHANGELOG.md
echo "### Changes" >> CHANGELOG.md
echo "- " >> CHANGELOG.md
echo "" >> CHANGELOG.md
echo "✅ Updated CHANGELOG.md"

echo ""
echo "Next steps:"
echo "  1. Review and complete CHANGELOG.md"
echo "  2. git add VERSION CHANGELOG.md"
echo "  3. git commit -m \"chore: bump version to $NEW_TAG\""
echo "  4. git tag $NEW_TAG"
echo "  5. git push origin main --tags"
