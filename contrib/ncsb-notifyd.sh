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
# Config: Uses ncsb's config/env handling (see: ncsb config)
#
# Environment:
#   NCSB_PLAYER    - Player name (default: from config)
#   POLL_INTERVAL  - Polling interval in seconds (default: 2)

set -euo pipefail

PLAYER="${1:-${NCSB_PLAYER:-}}"
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
    
    # Get host from ncsb config
    local host
    host=$(ncsb config 2>/dev/null | grep "^  host:" | cut -d: -f2- | xargs) || host="localhost"
    local port
    port=$(ncsb config 2>/dev/null | grep "^  port:" | cut -d: -f2- | xargs) || port="9000"
    
    if [ -n "$coverid" ] && [ ! -f "$cover_file" ]; then
        curl -s "http://$host:$port/music/$coverid/cover.jpg" -o "$cover_file" 2>/dev/null || true
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
    local cmd_args=()
    [ -n "$PLAYER" ] && cmd_args=(-P "$PLAYER")
    
    local status
    status=$(ncsb "${cmd_args[@]}" status 2>/dev/null) || return 0
    
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
log "Starting ncsb-notifyd${PLAYER:+ for player: $PLAYER} (poll: ${POLL_INTERVAL}s)"

while true; do
    poll
    sleep "$POLL_INTERVAL"
done
