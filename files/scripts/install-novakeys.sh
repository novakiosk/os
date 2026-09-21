#!/usr/bin/env bash
set -euo pipefail

repository="https://github.com/novakiosk/novakeys"
[[ $(uname -m) == x86_64 ]] || { echo 'NOVA Keys release requires x86_64' >&2; exit 1; }
# Resolve once so both assets come from the same release even if latest changes.
if ! resolved=$(curl --fail --location --silent --show-error --proto '=https' --proto-redir '=https' \
    --connect-timeout 20 --max-time 180 --retry 2 --output /dev/null --write-out '%{url_effective}' \
    "$repository/releases/latest"); then
    echo 'Could not resolve the latest NOVA Keys release' >&2
    exit 1
fi
tag=${resolved#"$repository/releases/tag/"}
[[ "$tag" =~ ^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]] || { echo 'Invalid latest NOVA Keys release tag' >&2; exit 1; }
version=${tag#v}
printf 'Installing NOVA Keys %s\n' "$version"
name="novakeys-$version-x86_64"
archive="$name.tar.gz"
release="$repository/releases/download/$tag"
staging=$(mktemp -d)
trap 'rm -rf "$staging"' EXIT
cd "$staging"

for asset in SHA256SUMS "$archive"; do
    if ! curl --fail --location --silent --show-error --proto '=https' --proto-redir '=https' \
        --connect-timeout 20 --max-time 180 --retry 2 "$release/$asset" -o "$asset"; then
        echo "Required NOVA Keys v$version asset unavailable: $asset" >&2
        exit 1
    fi
done
checksum=$(awk -v asset="$archive" '$2 == asset {print $1}' SHA256SUMS)
[[ "$checksum" =~ ^[0-9a-f]{64}$ ]] || { echo 'Missing or ambiguous NOVA Keys checksum' >&2; exit 1; }
printf '%s  %s\n' "$checksum" "$archive" | sha256sum --check --strict -

# Extract the executable to a fixed staging path.
tar -xOzf "$archive" "$name/novakeys" > novakeys
test -s novakeys
chmod 0755 novakeys
[[ $(./novakeys --version) == "novakeys $version" ]] || { echo 'NOVA Keys payload version mismatch' >&2; exit 1; }
# Keep the application's license and all bundled dependency notices together.
mkdir license-files
tar -xzf "$archive" --directory license-files --strip-components=1 \
    --no-same-owner --no-same-permissions "$name/LICENSE" "$name/licenses"
test -s license-files/LICENSE
test -n "$(find license-files/licenses -type f -print -quit)"
find license-files -type d -exec chmod 0755 {} +
find license-files -type f -exec chmod 0644 {} +

install -Dm0755 novakeys /usr/bin/novakeys
# Replace the full notice tree so removed dependencies do not leave stale files.
rm -rf /usr/share/licenses/novakeys
install -d -m0755 /usr/share/licenses/novakeys
cp -R license-files/. /usr/share/licenses/novakeys/
