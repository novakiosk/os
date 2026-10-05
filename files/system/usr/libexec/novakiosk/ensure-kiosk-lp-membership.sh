#!/usr/bin/bash
set -euo pipefail

ensure_membership() {
 local user="$1" group="$2" group_entry group_gid group_members
getent passwd "${user}" >/dev/null 2>&1 || return 0
group_entry=$(getent group "${group}") || return 0
group_gid=$(cut -d: -f3 <<<"${group_entry}")

if id -G "${user}" | tr ' ' '\n' | grep -qx "${group_gid}"; then
  return 0
fi

if ! grep -q "^${group}:" /etc/group; then
  group_members=$(cut -d: -f4 <<<"${group_entry}")
  printf '%s:x:%s:%s\n' "${group}" "${group_gid}" "${group_members}" >>/etc/group
fi

/usr/bin/gpasswd --add "${user}" "${group}"
id -G "${user}" | tr ' ' '\n' | grep -qx "${group_gid}"
}
ensure_membership kiosk lp
ensure_membership novakiosk-agent lp
ensure_membership novakiosk-agent tss
