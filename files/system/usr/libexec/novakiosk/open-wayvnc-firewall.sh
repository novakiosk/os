#!/usr/bin/bash
set -euo pipefail

port="5900/tcp"
zone="public"

firewall_cmd="/usr/bin/firewall-cmd"
offline_cmd="/usr/bin/firewall-offline-cmd"

if [[ -x "${firewall_cmd}" ]]; then
  default_zone="$("${firewall_cmd}" --get-default-zone 2>/dev/null || true)"
  if [[ -n "${default_zone}" ]]; then
    zone="${default_zone}"
  fi
fi

if [[ -x "${offline_cmd}" ]]; then
  if ! "${offline_cmd}" --zone="${zone}" --query-port="${port}" >/dev/null 2>&1; then
    "${offline_cmd}" --zone="${zone}" --add-port="${port}" >/dev/null
  fi
fi

if [[ -x "${firewall_cmd}" ]] && "${firewall_cmd}" --state >/dev/null 2>&1; then
  if ! "${firewall_cmd}" --quiet --zone "${zone}" --query-port="${port}"; then
    "${firewall_cmd}" --quiet --zone "${zone}" --add-port="${port}" || true
  fi
fi
