# NOVA Kiosk OS

[![Build](https://github.com/novakiosk/os/actions/workflows/build.yml/badge.svg)](https://github.com/novakiosk/os/actions/workflows/build.yml)

A [BlueBuild](https://blue-build.org) Fedora Atomic image for x86_64 kiosks,
managed through [NOVA Kiosk](https://github.com/novakiosk/novakiosk).
It includes Sway, Chromium, [NOVA Agent](https://github.com/novakiosk/agent),
[NOVA Keys](https://github.com/novakiosk/novakeys), CUPS printing, and remote
view/control through the Agent's outbound connection.

## Install and enroll

For occasional initial-install media, use the custom
[NOVA BlueBuild CLI](https://github.com/novakiosk/bluebuild-cli) with Rust,
Docker (or Podman) installed. Build the CLI and its pinned companion
installer from the same reviewed fork checkout:

```sh
# Run from the bluebuild-cli checkout.
cargo build --release
sudo docker build -t localhost/bluebuild-installer:display-name-v1.4.0 \
  -f installer/Containerfile installer
sudo ./target/release/bluebuild generate-iso \
  --run-driver docker \
  --interactive-setup --display-name novakiosk-os \
  --iso-name novakiosk-os-YYYYMMDD.iso \
  --output-dir /path/to/installer-output \
  image ghcr.io/novakiosk/os:latest
```

`--display-name` changes only the displayed installer name.
`--interactive-setup` restores network configuration (including static addresses
without DHCP) and user creation in both the classic installer and WebUI. Add
`--web-ui` to select WebUI.

Write the ISO to a USB drive and boot it. During installation, create a separate
user account and select the installer's administrator option to grant sudo access.
Do not name it `kiosk`. The image provides the `kiosk`
account, starts its graphical session automatically, and keeps its password locked.
Use the administrator account for SSH and maintenance; `sudo nmtui` configures
networking if needed.

Create an enrollment code in your NOVA Kiosk instance, then run:

```sh
sudo -u novakiosk-agent /usr/bin/novakiosk-agent smoke \
  --instance https://kiosk.example.com \
  --state-dir /var/lib/novakiosk-agentd
```

Enter the code when prompted and approve the machine in the admin UI. The Agent
service takes over automatically after enrollment; no separate foreground process
is needed. Content, keyboard settings, printers, and remote access are managed
through NOVA Kiosk. Chromium uses the kiosk's default printer and hides Save as PDF.
Additional printer drivers may need to be added to the image recipe.

To check enrollment and view Agent logs:

```sh
sudo -u novakiosk-agent novakiosk-agent status --state-dir /var/lib/novakiosk-agentd
sudo journalctl -u novakiosk-agentd.service -f
```

## Updates

Each image build downloads the latest stable Agent and NOVA Keys releases,
checks their `SHA256SUMS` and executable versions, and installs the binaries in
`/usr/bin`. Each application's license and bundled dependency notices are kept
under `/usr/share/licenses/novakiosk-agent/` or `/usr/share/licenses/novakeys/`.
Services and configuration come from this repository.


## Customize and build

Edit [recipes/recipe.yml](recipes/recipe.yml) for packages and modules, and
[files/](files/) for system configuration. Follow BlueBuild's
[local build guide](https://blue-build.org/how-to/local/) or use
the included GitHub Actions workflow. Forks need their own
[signing key and `SIGNING_SECRET`](https://blue-build.org/how-to/cosign/).

## Project

Built for [NOVA Spektrum](https://novaspektrum.no) and published with permission.
Maintained personally by the author, not supported or warranted by NOVA Spektrum.
The NOVA Spektrum name is not covered by the [Apache-2.0 license](LICENSE).
