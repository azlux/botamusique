#!/usr/bin/env bash

git remote set-url origin https://azlux:$GITHUB_API@github.com/azlux/botamusique/

if git fetch origin bot-traduora; then
  git branch bot-traduora FETCH_HEAD
  CREATE_PR=false
else
  git branch bot-traduora
  CREATE_PR=true
fi
git checkout bot-traduora
$SOURCE_DIR/scripts/sync_translation.py --lang_dir $SOURCE_DIR/lang/ --client $TRADUORA_R_CLIENT --secret $TRADUORA_R_SECRET --fetch
git add lang/*
git status

if GIT_COMMITTER_NAME='Traduora Bot' GIT_COMMITTER_EMAIL='noreply@azlux.fr' git commit -m 'Bot: Update translation' --author "Traduora Bot <noreply@azlux.fr>"; then
  git push origin bot-traduora
  sleep 2
  if $CREATE_PR; then GITHUB_USER="azlux" GITHUB_TOKEN="$GITHUB_API"  hub pull-request -m "Bot: TRADUORA Update"; fi
fi
