#!/usr/bin/bash
set -euo pipefail

user="kiosk"
group="lp"

getent passwd "${user}" >/dev/null 2>&1 || exit 0
group_entry=$(getent group "${group}") || exit 0
group_gid=$(cut -d: -f3 <<<"${group_entry}")

if id -G "${user}" | tr ' ' '\n' | grep -qx "${group_gid}"; then
  exit 0
fi

if ! grep -q "^${group}:" /etc/group; then
  group_members=$(cut -d: -f4 <<<"${group_entry}")
  printf '%s:x:%s:%s\n' "${group}" "${group_gid}" "${group_members}" >>/etc/group
fi

/usr/bin/gpasswd --add "${user}" "${group}"
id -G "${user}" | tr ' ' '\n' | grep -qx "${group_gid}"