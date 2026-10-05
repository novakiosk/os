#!/usr/bin/env bash
set -euo pipefail
# The files module installs the repository-scoped trust policy and existing key.
# Validate these exact bytes before committing an image with fleet capability.
python3 -IB - <<'PY'
import importlib.machinery
helper=importlib.machinery.SourceFileLoader('update','/usr/libexec/novakiosk-system-update').load_module()
helper.verify_policy()
PY
chmod 0755 /usr/libexec/novakiosk-system-update
