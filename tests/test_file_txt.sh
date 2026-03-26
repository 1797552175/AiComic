#!/bin/sh
set -eu

file_path="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)/file.txt"
first_line="$(sed -n '1p' "$file_path")"

if [ "$first_line" != "// test success" ]; then
  printf 'unexpected first line: %s\n' "$first_line" >&2
  exit 1
fi

printf 'file.txt first line is correct\n'
