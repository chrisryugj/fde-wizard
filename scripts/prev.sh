#!/bin/zsh
# 사용: scripts/prev.sh head|body view...  → tmp/sheet_<mode>.png (사진 + 각 뷰)
cd "$(dirname "$0")/.."
mkdir -p tmp
mode=$1; shift
blender -b -P scripts/preview.py -- $mode "$@" > tmp/blender_prev.log 2>&1
command grep -E "Traceback|Error" -A3 tmp/blender_prev.log | head -20
files=()
for v in "$@"; do files+=(tmp/prev_${mode}_$v.png); done
.venv/bin/python scripts/sheet.py tmp/sheet_$mode.png 420 $( [ -f ref/photo.jpg ] && echo ref/photo.jpg ) $files
