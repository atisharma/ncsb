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
#   NOTIFY_TIMEOUT - Notification timeout in seconds (default: 5)

set -euo pipefail

PLAYER="${1:-${NCSB_PLAYER:-}}"
POLL_INTERVAL="${POLL_INTERVAL:-2}"
NOTIFY_TIMEOUT="${NOTIFY_TIMEOUT:-5}"

# State tracking
PREV_TITLE=""
PREV_MODE=""

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >&2
}

# Get effective host/port from ncsb config output
get_host() {
    ncsb config 2>&1 | awk '/Effective settings/,0' | grep "host:" | cut -d: -f2- | xargs
}

get_port() {
    ncsb config 2>&1 | awk '/Effective settings/,0' | grep "port:" | cut -d: -f2- | xargs
}

# Get player MAC address
get_mac() {
    local player="$1"
    ncsb players 2>/dev/null | awk -v p="$player" '$1 == p {print $2}'
}

# Get current track info via LMS JSON-RPC API
get_current_track() {
    local host="$1"
    local port="$2"
    local mac="$3"
    
    # Get current index
    local cur_idx
    cur_idx=$(curl -s -X POST "http://$host:$port/jsonrpc.js" \
        -H "Content-Type: application/json" \
        -d "{\"id\":1,\"method\":\"slim.request\",\"params\":[\"$mac\",[\"status\",\"-\"]]}" \
        | jq -r '.result.playlist_cur_index // empty')
    
    if [ -z "$cur_idx" ]; then
        return 1
    fi
    
    # Get track at current index
    curl -s -X POST "http://$host:$port/jsonrpc.js" \
        -H "Content-Type: application/json" \
        -d "{\"id\":1,\"method\":\"slim.request\",\"params\":[\"$mac\",[\"status\",\"$cur_idx\",1,\"tags:cdtA\"]]}" \
        | jq '.result.playlist_loop[0]'
}

fetch_cover() {
    local coverid="$1"
    local host="$2"
    local port="$3"
    local cover_file="/tmp/ncsb-cover-$coverid.jpg"
    
    if [ -n "$coverid" ] && [ ! -f "$cover_file" ]; then
        # Request 200x200 (same as TUI default) to avoid fnott timeout on large images
        curl -s "http://$host:$port/music/$coverid/cover_200x200.jpg" -o "$cover_file" 2>/dev/null || true
    fi
    
    [ -f "$cover_file" ] && echo "$cover_file"
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
    
    local notify_opts=(-t "$((NOTIFY_TIMEOUT * 1000))")
    if [ -n "$cover_file" ] && [ -f "$cover_file" ]; then
        notify_opts+=(-i "$cover_file")
    fi
    
    notify-send "${notify_opts[@]}" "$title" "$body"
}

poll() {
    local cmd_args=()
    [ -n "$PLAYER" ] && cmd_args=(-P "$PLAYER")
    
    # Get current track info via ncsb info
    local info
    info=$(ncsb "${cmd_args[@]}" info 2>/dev/null) || return 0
    
    local title artist album mode
    title=$(echo "$info" | grep "^Title:" | cut -d: -f2- | xargs)
    artist=$(echo "$info" | grep "^Artist:" | cut -d: -f2- | xargs)
    album=$(echo "$info" | grep "^Album:" | cut -d: -f2- | xargs)
    mode=$(echo "$info" | grep "^Mode:" | cut -d: -f2- | xargs)
    
    # Check for changes
    if [ "$title" != "$PREV_TITLE" ] || [ "$mode" != "$PREV_MODE" ]; then
        local cover_file=""
        if [ "$mode" = "play" ] || [ "$mode" = "pause" ]; then
            local host port mac
            host=$(get_host)
            port=$(get_port)
            mac=$(get_mac "${PLAYER:-$(ncsb config 2>&1 | awk '/Effective settings/,0' | grep "player:" | cut -d: -f2- | xargs)}")
            
            if [ -n "$mac" ]; then
                local track_json
                track_json=$(get_current_track "$host" "$port" "$mac")
                local coverid
                coverid=$(echo "$track_json" | jq -r '.coverid // empty')
                [ -n "$coverid" ] && cover_file=$(fetch_cover "$coverid" "$host" "$port")
            fi
        fi
        
        send_notification "$title" "$album" "$artist" "$cover_file" "$mode"
        
        PREV_TITLE="$title"
        PREV_MODE="$mode"
    fi
}

# Main loop
log "Starting ncsb-notifyd${PLAYER:+ for player: $PLAYER} (poll: ${POLL_INTERVAL}s, timeout: ${NOTIFY_TIMEOUT}s)"

while true; do
    poll
    sleep "$POLL_INTERVAL"
done
