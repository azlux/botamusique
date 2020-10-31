#!/usr/bin/env bash

set -e

git remote set-url origin https://azlux:$GITHUB_API@github.com/azlux/botamusique/
git pull origin master

echo "=> Checking if translations in this commit differ from the server..."

git branch testing-translation master
git checkout testing-translation
$SOURCE_DIR/scripts/sync_translation.py --lang-dir $SOURCE_DIR/lang/ --client $TRADUORA_R_CLIENT --secret $TRADUORA_R_SECRET --fetch

if [ -z "$(git diff)" ]; then
  echo "==> No difference found."
  exit 0
fi

echo "==> Modifications found."
echo "=> Check if the modifications are based on the translations on the server..."

n=1
COMMON_FOUND=false

while [ $n -le 10 ]; do
  echo "==> Comparing server's translations with master~$n ($(git show --oneline --quiet master~$n))"
  CHANGED_LANG_FILE=$(git diff --name-only master~$n | grep "lang/" || true)
  if [ -z "$CHANGED_LANG_FILE" ]; then
    COMMON_FOUND=true
    break
  fi
  let n++
done

if [ ! $COMMON_FOUND ]; then
  echo "==> CONFLICTS: Previous commits doesn't share the same translations with the server."
  echo "    There are unmerged translation updates on the server."
  echo "    Please manually update these changes or wait for the pull request"
  echo "    created by the translation bot get merged."
  exit 1
fi

echo "==> master~$n ($(git show --oneline --quiet master~$n)) shares the same translations with the server."

echo "=> Preparing to push local translation updates to the server..."
git checkout -f master
$SOURCE_DIR/scripts/sync_translation.py --lang-dir $SOURCE_DIR/lang/ --client $TRADUORA_W_CLIENT --secret $TRADUORA_W_SECRET --push
exit 0
