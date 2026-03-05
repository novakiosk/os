#!/bin/bash

# Check if any physical display outputs are connected.
# If not, start Sway with a headless backend so it's still
# reachable over VNC (wayvnc).
has_monitor=false
for status_file in /sys/class/drm/card*-*/status; do
    if [ -f "$status_file" ] && grep -q "^connected$" "$status_file"; then
        has_monitor=true
        break
    fi
done

if [ "$has_monitor" = false ]; then
    export WLR_BACKENDS=headless
    export WLR_LIBINPUT_NO_DEVICES=1
    export WLR_RENDERER=pixman
fi

exec sway
