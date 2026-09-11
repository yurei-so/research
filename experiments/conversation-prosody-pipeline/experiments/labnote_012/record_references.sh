#!/usr/bin/env bash
set -euo pipefail

reference_dir="${PROSODY_012_REFERENCE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/conversation-prosody/prosody-012/references}"

if ! command -v pw-record >/dev/null 2>&1; then
  echo "pw-record is required but was not found." >&2
  exit 1
fi

umask 077
mkdir -p "$reference_dir"

record_one() {
  local filename="$1"
  local context="$2"
  local reading="$3"
  local destination="$reference_dir/$filename"

  if [[ -e "$destination" ]]; then
    echo "Refusing to overwrite existing recording: $destination" >&2
    echo "Move it aside or delete that exact file before recording again." >&2
    exit 1
  fi

  echo
  echo "Context: $context"
  echo "Read naturally, emphasizing the CAPITALIZED word:"
  echo "  $reading"
  read -r -p "Press Enter to start recording... "

  pw-record --rate 48000 --channels 1 --format s16 "$destination" &
  local recorder_pid=$!
  trap 'kill -INT "$recorder_pid" 2>/dev/null || true' INT TERM EXIT

  read -r -p "Recording. Press Enter after the sentence... "
  kill -INT "$recorder_pid" 2>/dev/null || true
  wait "$recorder_pid" 2>/dev/null || true
  trap - INT TERM EXIT

  chmod 600 "$destination"
  echo "Saved privately: $destination"
}

echo "Prosody 012 private reference capture"
echo "The files stay outside the repository in:"
echo "  $reference_dir"
echo "Keep each take between 1 and 12 seconds. This helper never overwrites a take."

record_one \
  "location-day__location.wav" \
  "Correct the meeting location." \
  "We meet at the LIBRARY on Friday."

record_one \
  "location-day__day.wav" \
  "Correct the meeting day." \
  "We meet at the library on FRIDAY."

record_one \
  "person-object__person.wav" \
  "Correct who borrowed it." \
  "JORDAN borrowed my bicycle again."

record_one \
  "person-object__object.wav" \
  "Correct what was borrowed." \
  "Jordan borrowed my BICYCLE again."

echo
echo "All four takes are present. Validate them with:"
echo "  python3 validate_references.py --reference-dir '$reference_dir'"
