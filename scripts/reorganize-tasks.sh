#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p _incoming/zips _misc/personal _misc/reference reviews tasks

# Consolidate loose personal files in _misc/
for f in _misc/*; do
  [ -e "$f" ] || continue
  base=$(basename "$f")
  case "$base" in
    personal|reference|harbor-compat) continue ;;
  esac
  case "$base" in
    *.pdf|*.jpg|*.jpeg|*.png|"openmemory copy.md")
      mv "$f" _misc/personal/
      ;;
  esac
done

# Move harbor-compat reference material out of root
if [ -d harbor-compat ] && [ ! -e _misc/harbor-compat ]; then
  mv harbor-compat _misc/harbor-compat
fi

# Move root task dirs into tasks/ or remove duplicates
for dir in */; do
  name="${dir%/}"
  case "$name" in
    docs|scripts|tasks|templates|jobs|_backup|_incoming|_misc|reviews|.cursor|.venv) continue ;;
  esac
  if [ -f "$name/task.toml" ] || [ -f "$name/instruction.md" ] || [ -d "$name/steps" ]; then
    if [ -d "tasks/$name" ]; then
      echo "REMOVE root duplicate: $name"
      rm -rf "$name"
    else
      echo "MOVE to tasks/: $name"
      mv "$name" "tasks/$name"
    fi
  fi
done

# Loose files at root
for f in *.pdf *.jpg *.jpeg *.png *.tar.gz; do
  [ -f "$f" ] || continue
  mv "$f" _misc/personal/
done
[ -f entire-report.txt ] && mv entire-report.txt reviews/perl-marine-inquiry-cli-entire-report.txt

extract_task_zip() {
  local zippath="$1"
  local zipfile base task_name dest
  zipfile=$(basename "$zippath")
  base="${zipfile%.zip}"

  case "$base" in
    "3a528f89-6e97-4907-a1ba-bf24238cfc77_submission_2026-06-19T10_51_41.462Z (1)")
      task_name="exec-profile-cap-bound-drift"
      ;;
    *)
      task_name="$base"
      ;;
  esac
  task_name="${task_name%"${task_name##*[![:space:]]}"}"
  dest="tasks/$task_name"

  if [ "$base" = "law-samples" ]; then
    if [ ! -d _misc/reference/law-samples ]; then
      echo "EXTRACT reference: law-samples.zip"
      unzip -oq "$zippath" -d _misc/reference/
      rm -rf _misc/reference/__MACOSX 2>/dev/null || true
    fi
    rm -rf law-samples 2>/dev/null || true
    return 0
  fi

  if [ -d "$dest" ] && { [ -f "$dest/task.toml" ] || [ -f "$dest/steps/milestone_1/instruction.md" ]; }; then
    echo "SKIP (exists): $zipfile -> $dest"
    return 0
  fi

  echo "EXTRACT: $zipfile -> $dest"
  mkdir -p "$dest"
  unzip -oq "$zippath" -d "$dest"
}

shopt -s nullglob
for zip in _incoming/zips/*.zip; do
  extract_task_zip "$zip"
done

rm -rf "tasks/quest-capsule-decoder " law-samples 2>/dev/null || true
mv *.zip _incoming/zips/ 2>/dev/null || true

echo ""
echo "=== ROOT ==="
ls -1

echo ""
echo "=== TASKS ($(ls -1 tasks | wc -l | tr -d ' ')) ==="
ls -1 tasks | sort

echo ""
echo "=== ARCHIVED ZIPS: $(ls -1 _incoming/zips | wc -l | tr -d ' ') ==="
