#!/usr/bin/bash
set -euo pipefail

user="kiosk"

id "${user}" >/dev/null 2>&1 || exit 0
/usr/bin/loginctl enable-linger "${user}"
