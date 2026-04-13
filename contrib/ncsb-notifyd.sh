#!/bin/bash
# ncsb-notifyd — Daemon to notify on track/state changes
#
# Polls LMS and sends notify-send when track changes or playback state changes.
# Requires: ncsb, jq, notify-send, curl
#
# Usage:
#   ncsb-notifyd [PLAYER]
#   NCSB_PLAYER=eos ncsb-notifyd
#
# Environment:
#   NCSB_PLAYER  - Player name (default: eos)
#   LMS_HOST     - LMS server host (default: sol.wg.letterbox.pw)
#   LMS_PORT     - LMS server port (default: 9000)
#   POLL_INTERVAL - Polling interval in seconds (default: 2)

set -euo pipefail

PLAYER="${1:-${NCSB_PLAYER:-eos}}"
HOST="${LMS_HOST:-sol.wg.letterbox.pw}"
PORT="${LMS_PORT:-9000}"
POLL_INTERVAL="${POLL_INTERVAL:-2}"

# State tracking
PREV_TRACK_ID=""
PREV_MODE=""

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >&2
}

fetch_cover() {
    local coverid="$1"
    local cover_file="/tmp/ncsb-cover-$coverid.jpg"
    
    if [ -n "$coverid" ] && [ ! -f "$cover_file" ]; then
        curl -s "http://$HOST:$PORT/music/$coverid/cover.jpg" -o "$cover_file" 2>/dev/null || true
    fi
    
    echo "$cover_file"
}

send_notification() {
    local title="$1"
    local album="$2"
    local artist="$3"
    local cover_file="$4"
    local mode="$5"
    
    local body="$album"
    [ -n "$artist" ] && body="$album"$'\n'"$artist"
    
    # Mode indicator
    local icon=""
    case "$mode" in
        play) icon="▶" ;;
        pause) icon="⏸" ;;
        stop) icon="⏹" ;;
    esac
    [ -n "$icon" ] && title="$icon $title"
    
    local notify_opts=()
    if [ -f "$cover_file" ]; then
        notify_opts=(-i "$cover_file")
    fi
    
    notify-send "${notify_opts[@]}" "$title" "$body"
}

poll() {
    local status
    status=$(ncsb -P "$PLAYER" status 2>/dev/null) || return 0
    
    local track_id mode title album artist coverid
    track_id=$(echo "$status" | jq -r '.playlist_loop[0].id // empty')
    mode=$(echo "$status" | jq -r '.mode // "stop"')
    title=$(echo "$status" | jq -r '.playlist_loop[0].title // "Unknown"')
    album=$(echo "$status" | jq -r '.playlist_loop[0].album // ""')
    artist=$(echo "$status" | jq -r '.playlist_loop[0].artist // ""')
    coverid=$(echo "$status" | jq -r '.playlist_loop[0].coverid // empty')
    
    # Check for changes
    if [ "$track_id" != "$PREV_TRACK_ID" ] || [ "$mode" != "$PREV_MODE" ]; then
        local cover_file=""
        [ -n "$coverid" ] && cover_file=$(fetch_cover "$coverid")
        
        send_notification "$title" "$album" "$artist" "$cover_file" "$mode"
        
        PREV_TRACK_ID="$track_id"
        PREV_MODE="$mode"
    fi
}

# Main loop
log "Starting ncsb-notifyd for player: $PLAYER (poll: ${POLL_INTERVAL}s)"

while true; do
    poll
    sleep "$POLL_INTERVAL"
done
