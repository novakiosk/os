#!/usr/bin/bash
set -euo pipefail

ethtool_bin="/usr/sbin/ethtool"
if [[ ! -x "${ethtool_bin}" ]]; then
  ethtool_bin="/usr/bin/ethtool"
fi

if [[ ! -x "${ethtool_bin}" ]]; then
  exit 0
fi

shopt -s nullglob
for devpath in /sys/class/net/*; do
  iface="$(basename "${devpath}")"
  [[ "${iface}" == "lo" ]] && continue

  # Skip non-physical interfaces (no backing device) and wireless interfaces.
  [[ -e "${devpath}/device" ]] || continue
  [[ -d "${devpath}/wireless" ]] && continue

  if "${ethtool_bin}" "${iface}" 2>/dev/null | grep -Eq 'Supports Wake-on:.*g'; then
    "${ethtool_bin}" -s "${iface}" wol g >/dev/null 2>&1 || true
  fi
done
