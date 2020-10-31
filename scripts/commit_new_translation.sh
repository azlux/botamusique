#!/usr/bin/env bash

git remote set-url origin https://azlux:$GITHUB_API@github.com/azlux/botamusique/

echo "=> Fetching for bot-traduora branch..."
if git fetch origin bot-traduora; then
  echo "==> bot-traduora branch exists"
  git branch bot-traduora FETCH_HEAD
  CREATE_PR=false
else
  echo "==> bot-traduora branch doesn't exist, create one"
  git branch bot-traduora
  CREATE_PR=true
fi
git checkout bot-traduora

echo "=> Fetching updates from the server..."

$SOURCE_DIR/scripts/sync_translation.py --lang-dir $SOURCE_DIR/lang/ --client $TRADUORA_R_CLIENT --secret $TRADUORA_R_SECRET --fetch
git add lang/*
git status

if $PUSH; then
   echo "=> Pushing updates to bot-traduora branch..."
  if GIT_COMMITTER_NAME='Traduora Bot' GIT_COMMITTER_EMAIL='noreply@azlux.fr' git commit -m 'Bot: Update translation' --author "Traduora Bot <noreply@azlux.fr>"; then
    git push origin bot-traduora
    sleep 2
    if $CREATE_PR; then GITHUB_USER="azlux" GITHUB_TOKEN="$GITHUB_API"  hub pull-request -m "Bot: TRADUORA Update"; fi
    exit 0
  fi
   echo "==> There's nothing to push."
   exit 0
fi
