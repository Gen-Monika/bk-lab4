#!/usr/bin/env bash
set -euo pipefail

SEARCH_PATH="${search_path:-${1:-/project}}"
SUFFIX="${suffix:-${2:-log}}"
BACKUP_PATH="${backup_path:-${3:-}}"
TMP_FILE="$(mktemp)"

cleanup() {
    rm -f "$TMP_FILE"
}
trap cleanup EXIT

json_escape() {
    sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' ' '
}

normalize_placeholder() {
    case "$1" in
        ""|\$\{search_path\}|\$\{suffix\}|\$\{backup_path\}|\{\{search_path\}\}|\{\{suffix\}\}|\{\{backup_path\}\})
            printf ''
            ;;
        *)
            printf '%s' "$1"
            ;;
    esac
}

SEARCH_PATH="$(normalize_placeholder "$SEARCH_PATH")"
SUFFIX="$(normalize_placeholder "$SUFFIX")"
BACKUP_PATH="$(normalize_placeholder "$BACKUP_PATH")"
SEARCH_PATH="${SEARCH_PATH:-/project}"
SUFFIX="${SUFFIX:-log}"

if [ -d "$SEARCH_PATH" ]; then
    find "$SEARCH_PATH" -type f -name "*.${SUFFIX}" -print > "$TMP_FILE"
else
    : > "$TMP_FILE"
fi

FILE_COUNT="$(wc -l < "$TMP_FILE" | tr -d ' ')"
TOTAL_SIZE="$(
    while IFS= read -r file_path; do
        if [ -f "$file_path" ]; then
            wc -c < "$file_path"
        fi
    done < "$TMP_FILE" | awk '{sum += $1} END {print sum + 0}'
)"

ACTION="search"
ARCHIVE_PATH=""
if [ -n "$BACKUP_PATH" ]; then
    ACTION="backup"
    mkdir -p "$BACKUP_PATH"
    if [ "$FILE_COUNT" -gt 0 ]; then
        ARCHIVE_PATH="${BACKUP_PATH%/}/logs-$(date +%Y%m%d%H%M%S).tar.gz"
        tar -czf "$ARCHIVE_PATH" -T "$TMP_FILE"
    fi
fi

MESSAGE="completed"
if [ ! -d "$SEARCH_PATH" ]; then
    MESSAGE="search path not found"
fi

FILE_LIST="$(paste -sd, "$TMP_FILE" | json_escape)"
ESCAPED_ACTION="$(printf '%s' "$ACTION" | json_escape)"
ESCAPED_SEARCH_PATH="$(printf '%s' "$SEARCH_PATH" | json_escape)"
ESCAPED_SUFFIX="$(printf '%s' "$SUFFIX" | json_escape)"
ESCAPED_BACKUP_PATH="$(printf '%s' "$BACKUP_PATH" | json_escape)"
ESCAPED_ARCHIVE_PATH="$(printf '%s' "$ARCHIVE_PATH" | json_escape)"
ESCAPED_MESSAGE="$(printf '%s' "$MESSAGE" | json_escape)"

printf 'BK_JOB_RESULT={"action":"%s","bk_file_list":"%s","bk_file_cnt":%s,"bk_file_total_size":%s,"search_path":"%s","suffix":"%s","backup_path":"%s","backup_archive":"%s","message":"%s"}\n' \
    "$ESCAPED_ACTION" "$FILE_LIST" "$FILE_COUNT" "$TOTAL_SIZE" "$ESCAPED_SEARCH_PATH" "$ESCAPED_SUFFIX" "$ESCAPED_BACKUP_PATH" "$ESCAPED_ARCHIVE_PATH" "$ESCAPED_MESSAGE"
