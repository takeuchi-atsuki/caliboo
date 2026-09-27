#!/bin/bash

# application info
APP_NAME=Caliboo

# directory info
EXE_DIR=$(cd $(dirname $0);pwd)
BASE_DIR=$(cd "${EXE_DIR%/}/../" && pwd)
TEMP_DIR=${EXE_DIR%/}/.temp/
BUILD_DIR=${TEMP_DIR%/}/${APP_NAME}
RELEASE_DIR=${BASE_DIR%/}/release/

# package info
TIMESTAMP=$(date +%Y%m%d)
# VERSION=$(grep -v '^\s*$' "${BASE_DIR%/}/version" | head -n 1)
PACKAGE_FILE_NAME=${TIMESTAMP}_${APP_NAME}.zip

# --------------------
# Utility functions
# --------------------

cpdir() {
  if [ ! -d $2 ]; then
    mkdir -p $2
  fi
  # NOTE: node_modules/.venv/dist/coverage等のビルド生成物・依存物は容量が大きく、
  #       展開先で devel/setup.sh (npm ci / pip install) により再生成できるため同梱しない。
  # NOTE: .claude/settings.local.json は個人の権限設定、scheduled_tasks.lock は
  #       Claude Code の実行時ロックのため同梱しない。
  # NOTE: build.shがdevel/配下にあるため、devel/を取り込む際に自分自身の
  #       作業用一時ディレクトリ(.temp/=TEMP_DIR)を再帰的に含めてしまう。
  #       .temp/を除外して自己参照を防ぐ。
  rsync -av \
    --exclude='.temp/' \
    --exclude='node_modules/' \
    --exclude='.venv/' \
    --exclude='dist/' \
    --exclude='coverage/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache/' \
    --exclude='*.egg-info/' \
    --exclude='.coverage' \
    --exclude='var/' \
    --exclude='tsconfig.tsbuildinfo' \
    --exclude='.vscode/' \
    --exclude='settings.local.json' \
    --exclude='scheduled_tasks.lock' \
    --exclude='.gitignore' \
    --exclude='.editorconfig' \
    --exclude='*.code-workspace' \
    --exclude='*:Zone.Identifier' \
    --exclude='~BROMIUM' \
    $1 $2
}

# --------------------
# Initialize
# --------------------

# cleanup
# NOTE: ${BUILD_DIR}/* のglobでは .claude/ 等のドットディレクトリが消えず、
#       前回ビルドの残骸(除外対象にしたファイル等)がzipへ混入するため、ディレクトリごと作り直す。
rm -rf ${BUILD_DIR}

mkdir -p ${BUILD_DIR}
mkdir -p ${RELEASE_DIR}

# --------------------
# Make package
# --------------------

# include files
echo "# include files"
cpdir ${BASE_DIR%/}/backend/ ${BUILD_DIR%/}/backend/
cpdir ${BASE_DIR%/}/frontend/ ${BUILD_DIR%/}/frontend/
cpdir ${BASE_DIR%/}/docs/ ${BUILD_DIR%/}/docs/
cpdir ${BASE_DIR%/}/devel/ ${BUILD_DIR%/}/devel/
cpdir ${BASE_DIR%/}/.devcontainer/ ${BUILD_DIR%/}/.devcontainer/
cpdir ${BASE_DIR%/}/.claude/ ${BUILD_DIR%/}/.claude/
cp ${BASE_DIR%/}/BACKLOG.md ${BUILD_DIR%/}/BACKLOG.md
echo

# create archive
echo "# create archive"
bash <<- EOS
cd ${BUILD_DIR%/}/../
zip -r ${PACKAGE_FILE_NAME} ${APP_NAME}
mv -f ${PACKAGE_FILE_NAME} ${RELEASE_DIR%/}/
EOS
echo
echo package: ${RELEASE_DIR%/}/${PACKAGE_FILE_NAME}
echo

echo complete!
