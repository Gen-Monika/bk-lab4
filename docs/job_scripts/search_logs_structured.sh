#!/usr/bin/env bash
set -euo pipefail

SEARCH_PATH="${search_path:-/project}"
SUFFIX="${suffix:-log}"
TMP_FILE="$(mktemp)"

cleanup() {
    rm -f "$TMP_FILE"
}
trap cleanup EXIT

json_escape() {
    sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' ' '
}

if [ ! -d "$SEARCH_PATH" ]; then
    ESCAPED_PATH="$(printf '%s' "$SEARCH_PATH" | json_escape)"
    ESCAPED_SUFFIX="$(printf '%s' "$SUFFIX" | json_escape)"
    printf 'BK_JOB_RESULT={"bk_file_list":"","bk_file_cnt":0,"bk_file_total_size":0,"search_path":"%s","suffix":"%s","message":"search path not found"}\n' "$ESCAPED_PATH" "$ESCAPED_SUFFIX"
    exit 0
fi

find "$SEARCH_PATH" -type f -name "*.${SUFFIX}" -print > "$TMP_FILE"

FILE_COUNT="$(wc -l < "$TMP_FILE" | tr -d ' ')"
TOTAL_SIZE="$(
    while IFS= read -r file_path; do
        if [ -f "$file_path" ]; then
            wc -c < "$file_path"
        fi
    done < "$TMP_FILE" | awk '{sum += $1} END {print sum + 0}'
)"
FILE_LIST="$(paste -sd, "$TMP_FILE" | json_escape)"
ESCAPED_PATH="$(printf '%s' "$SEARCH_PATH" | json_escape)"
ESCAPED_SUFFIX="$(printf '%s' "$SUFFIX" | json_escape)"

printf 'BK_JOB_RESULT={"bk_file_list":"%s","bk_file_cnt":%s,"bk_file_total_size":%s,"search_path":"%s","suffix":"%s","message":"completed"}\n' \
    "$FILE_LIST" "$FILE_COUNT" "$TOTAL_SIZE" "$ESCAPED_PATH" "$ESCAPED_SUFFIX"
