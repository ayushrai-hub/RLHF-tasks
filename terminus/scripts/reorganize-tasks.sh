#!/bin/bash
# Consolidate Terminus task folders, archives, and loose files into a clean layout.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p _incoming/zips _misc/personal _misc/reference _backup/copies reviews tasks

# Tasks that must stay at repo root (not moved into tasks/)
ROOT_TASKS=(stats-plan-resume-skew build-pkg-config-transitive-flag-sanitizer-cpp-json rt-iot2022-drift-multi-class bounded-kv-cache)
is_root_task() {
  local name="$1"
  for t in "${ROOT_TASKS[@]}"; do
    [ "$name" = "$t" ] && return 0
  done
  return 1
}

echo "=== Phase 1: personal / loose files ==="

[ -f "openmemory copy.md" ] && mv "openmemory copy.md" _misc/personal/
[ -f "ECG-Dataset - ECG-Dataset.csv" ] && mv "ECG-Dataset - ECG-Dataset.csv" _misc/personal/

if [ -d harbor-compat ]; then
  if [ -d _misc/harbor-compat ]; then
    rm -rf harbor-compat
  else
    mv harbor-compat _misc/harbor-compat
  fi
fi

if [ -d law-samples ]; then
  if [ -d _misc/reference/law-samples ]; then
    rm -rf law-samples
  else
    mv law-samples _misc/reference/law-samples
  fi
fi

for f in cropped-images*; do
  [ -e "$f" ] || continue
  mv "$f" _misc/personal/
done

for f in _misc/*; do
  [ -e "$f" ] || continue
  base=$(basename "$f")
  case "$base" in
    personal|reference|harbor-compat) continue ;;
  esac
  case "$base" in
    *.pdf|*.jpg|*.jpeg|*.png|*.csv|"openmemory copy.md")
      mv "$f" _misc/personal/
      ;;
  esac
done

for f in *.pdf *.jpg *.jpeg *.png *.xlsx *.csv *.tar.gz; do
  [ -f "$f" ] || continue
  mv "$f" _misc/personal/
done

for f in abcd.py "build_workbook copy.py" build_workbook.py \
         copy_of_kaggle_heart_disease_ml.py "copy_of_kaggle_heart_disease_ml (1).py" \
         kaggle_heart_disease_ml.py; do
  [ -f "$f" ] || continue
  mv "$f" _misc/personal/
done

if [ -d "11+10_tasks" ]; then
  if [ -d _misc/reference/11+10_tasks ]; then
    rm -rf "11+10_tasks"
  else
    mv "11+10_tasks" _misc/reference/11+10_tasks
  fi
  echo "ARCHIVE reference bundle: 11+10_tasks"
fi

if [ -f entire-report.txt ]; then
  cp -f entire-report.txt reviews/entire-report.txt
fi

for f in _other/*entire-report*.txt _other/reports/*.txt _other/reports/*.md; do
  [ -f "$f" ] || continue
  base=$(basename "$f")
  [ -s "$f" ] || continue
  if [ -f "reviews/$base" ] && cmp -s "$f" "reviews/$base" 2>/dev/null; then
    continue
  fi
  cp -f "$f" "reviews/$base"
  echo "SYNC review artifact: $base -> reviews/"
done

mkdir -p _incoming/submissions
for dir in *_submission*/; do
  [ -d "$dir" ] || continue
  name="${dir%/}"
  if [ -f "$name/task.toml" ] || [ -f "$name/instruction.md" ]; then
    continue
  fi
  if [ -d "_incoming/submissions/$name" ]; then
    rm -rf "$name"
  else
    mv "$name" "_incoming/submissions/$name"
  fi
  echo "ARCHIVE submission logs: $name"
done

echo "=== Phase 2: archive obvious copies ==="

for dir in */; do
  name="${dir%/}"
  case "$name" in
    *" copy"|*" 2"|*"sling"|*"tawa"|*"trolly") ;;
    *) continue ;;
  esac
  if [ -f "$name/task.toml" ] || [ -f "$name/instruction.md" ]; then
    echo "ARCHIVE copy: $name"
    rm -rf "_backup/copies/$name"
    mv "$name" "_backup/copies/$name"
  fi
done

merge_task_dir() {
  : # tasks/ is canonical; root duplicates are dropped in phase 3
}

echo "=== Phase 3: consolidate task directories into tasks/ ==="

move_task_into_tasks() {
  local src="$1"
  local name
  name=$(basename "$src")
  is_root_task "$name" && return 0
  local dest="tasks/$name"
  if [ -d "$dest" ]; then
    echo "DROP duplicate (tasks/ is canonical): $name"
    rm -rf "$src"
  else
    mv "$src" "$dest"
    echo "MOVED to tasks/: $name"
  fi
}

if [ -d _other/review-tasks ]; then
  for dir in _other/review-tasks/*/; do
    [ -d "$dir" ] || continue
    move_task_into_tasks "${dir%/}"
  done
  rmdir _other/review-tasks 2>/dev/null || true
fi

for dir in */; do
  name="${dir%/}"
  case "$name" in
    docs|scripts|tasks|templates|jobs|_backup|_incoming|_misc|_other|reviews|.cursor|.venv|harbor-compat|law-samples) continue ;;
  esac
  is_root_task "$name" && continue

  is_task=false
  if [ -f "$name/task.toml" ] || [ -f "$name/instruction.md" ] || [ -d "$name/steps" ]; then
    is_task=true
  fi
  [ "$is_task" = true ] || continue

  move_task_into_tasks "$name"
done

extract_task_zip() {
  local zippath="$1"
  local zipfile base task_name dest
  zipfile=$(basename "$zippath")
  base="${zipfile%.zip}"
  base="${base%"${base##*[![:space:]]}"}"

  case "$base" in
    "3a528f89-6e97-4907-a1ba-bf24238cfc77_submission_2026-06-19T10_51_41.462Z (1)")
      task_name="exec-profile-cap-bound-drift"
      ;;
    *)
      task_name="$base"
      ;;
  esac
  dest="tasks/$task_name"

  if [ "$base" = "law-samples" ]; then
    if [ ! -d _misc/reference/law-samples ]; then
      echo "EXTRACT reference: law-samples.zip"
      unzip -oq "$zippath" -d _misc/reference/
      rm -rf _misc/reference/__MACOSX 2>/dev/null || true
    fi
    return 0
  fi

  case "$base" in
    cropped-images*|ECG-Dataset*) return 0 ;;
  esac

  if [ -d "$dest" ] && { [ -f "$dest/task.toml" ] || [ -f "$dest/steps/milestone_1/instruction.md" ]; }; then
    echo "SKIP (exists): $zipfile -> $dest"
    return 0
  fi

  echo "EXTRACT: $zipfile -> $dest"
  mkdir -p "$dest"
  unzip -oq "$zippath" -d "$dest"
}

echo "=== Phase 4: archives ==="

shopt -s nullglob
for zip in *.zip; do
  [ -f "$zip" ] || continue
  base=$(basename "$zip")
  dest="_incoming/zips/$base"
  if [ -f "$dest" ]; then
    rm -f "$zip"
    continue
  fi
  mv "$zip" "$dest"
done

for zip in _incoming/zips/*.zip; do
  extract_task_zip "$zip"
  [ -f "$zip" ] && rm -f "$zip"
done

echo "=== Phase 4b: extract any remaining zips + validate tasks/ ==="
python3 "$ROOT/scripts/extract-all-task-zips.py"

rm -rf "tasks/quest-capsule-decoder " 2>/dev/null || true
[ -d tasks/law-samples ] && mv tasks/law-samples _misc/reference/law-samples 2>/dev/null || true

for dir in tasks/*_submission*/; do
  [ -d "$dir" ] || continue
  name=$(basename "$dir")
  if [ -f "$dir/task.toml" ] || [ -f "$dir/instruction.md" ]; then
    continue
  fi
  mkdir -p _incoming/submissions
  if [ -d "_incoming/submissions/$name" ]; then
    rm -rf "$dir"
  else
    mv "$dir" "_incoming/submissions/$name"
  fi
  echo "MOVE submission wrapper out of tasks/: $name"
done

echo "=== Phase 5: task index ==="
python3 "$ROOT/scripts/generate-tasks-index.py"

echo ""
echo "=== ROOT (tooling + docs + pinned root tasks) ==="
ls -1

echo ""
echo "=== ROOT TASKS (stay at repo root) ==="
for t in "${ROOT_TASKS[@]}"; do
  [ -d "$t" ] && echo "$t"
done

echo ""
echo "=== TASKS ($(ls -1 tasks 2>/dev/null | wc -l | tr -d ' ')) ==="
ls -1 tasks | sort

echo ""
echo "=== ARCHIVED ZIPS: $(ls -1 _incoming/zips 2>/dev/null | wc -l | tr -d ' ') ==="
