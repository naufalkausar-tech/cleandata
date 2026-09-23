#!/bin/bash
set -e
cd "$(dirname "$0")"

CRED=$(printf "protocol=https\nhost=github.com\n\n" | git credential fill)
TOKEN=$(echo "$CRED" | grep '^password=' | cut -d= -f2-)
USER=$(echo "$CRED" | grep '^username=' | cut -d= -f2-)

if [ -z "$TOKEN" ] || [ -z "$USER" ]; then
  echo "ERROR: no cached GitHub credential found" >&2
  exit 1
fi

echo "Creating repo for user: $USER"

HTTP_CODE=$(curl -s -o /tmp/create_repo_response.json -w "%{http_code}" \
  -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/user/repos \
  -d '{"name":"cleandata","description":"Clean messy CSV/Excel data: fix types, drop duplicates, flag outliers, and get a reproducible audit report.","private":false,"has_issues":true}')

echo "GitHub API response code: $HTTP_CODE"
cat /tmp/create_repo_response.json

if [ "$HTTP_CODE" != "201" ]; then
  echo "Repo creation did not return 201 - check response above (may already exist, which is OK)."
fi

git init -q
git checkout -q -b main 2>/dev/null || git checkout -q main
git add -A
git commit -q -m "cleandata: CSV/Excel cleaning CLI + library

Trims whitespace, converts numeric/date-like strings, drops exact
duplicates, flags outliers (IQR, not removed), and reports missing
values - with a reproducible markdown audit report. 10/10 tests
passing." || echo "(nothing to commit, already committed)"

git remote remove origin 2>/dev/null || true
git remote add origin "https://$USER@github.com/$USER/cleandata.git"

git push -u origin main

echo "DONE: https://github.com/$USER/cleandata"
