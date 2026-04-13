#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: anthropic.sh <index> [file.json]

Extract all Content blocks from the Nth message (0-indexed),
writing each block as a separate Markdown file into ./content_blocks/.

Options:
  <index>      Message index (0-based)
  [file.json]  JSON file path. If omitted, reads from stdin.

Examples:
  anthropic.sh 0 response.json
  anthropic.sh 3 < response.json
  cat response.json | anthropic.sh 2

Output:
  ./content_blocks/01_text.md
  ./content_blocks/02_text.md
  ./content_blocks/03_tool_use.md
  ...
EOF
}

if [[ $# -lt 1 ]]; then
    usage
    exit 1
fi

if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    usage
    exit 0
fi

INDEX="$1"
INPUT="${2:-/dev/stdin}"

if [[ ! -f "$INPUT" && "$INPUT" != "/dev/stdin" ]]; then
    echo "Error: file not found: $INPUT" >&2
    exit 1
fi

if ! [[ "$INDEX" =~ ^[0-9]+$ ]]; then
    echo "Error: index must be a non-negative integer, got: $INDEX" >&2
    exit 1
fi

OUTDIR="./content_blocks"
mkdir -p "$OUTDIR"

# Read JSON once, validate the message exists
MSG=$(jq --argjson idx "$INDEX" '.messages[$idx]' < "$INPUT")
if [[ "$MSG" == "null" ]]; then
    echo "Error: message at index $INDEX not found" >&2
    exit 1
fi

ROLE=$(echo "$MSG" | jq -r '.role // "unknown"')
COUNT=$(echo "$MSG" | jq '.content | length')

if [[ "$COUNT" -eq 0 ]]; then
    echo "Message $INDEX (role: $ROLE) has no content blocks."
    exit 0
fi

echo "Message $INDEX (role: $ROLE) — $COUNT content block(s):"

# Iterate over each content block
for i in $(seq 0 $((COUNT - 1))); do
    BLOCK=$(echo "$MSG" | jq ".content[$i]")
    TYPE=$(echo "$BLOCK" | jq -r '.type')
    SEQ=$(printf "%02d" $((i + 1)))

    # Check if block has cache_control
    HAS_CACHE=$(jq -r 'if .cache_control then "+c" else "" end' <<< "$BLOCK")

    FILENAME="${OUTDIR}/${SEQ}_${TYPE}${HAS_CACHE}.md"

    case "$TYPE" in
        text)
            jq -r '.text' <<< "$BLOCK"
            ;;
        tool_use)
            jq -r '.input' <<< "$BLOCK"
            ;;
        tool_result)
            jq -r '.content' <<< "$BLOCK"
            ;;
        image)
            jq -r '.source' <<< "$BLOCK"
            ;;
        thinking)
            jq -r '.thinking' <<< "$BLOCK"
            ;;
        *)
            jq '.' <<< "$BLOCK"
            ;;
    esac > "$FILENAME"

    echo "  -> $FILENAME"
done

echo "Done. Files written to $OUTDIR/"
