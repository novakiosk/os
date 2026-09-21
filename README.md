# NOVA Kiosk OS

[![Build](https://github.com/novakiosk/os/actions/workflows/build.yml/badge.svg)](https://github.com/novakiosk/os/actions/workflows/build.yml)

A [BlueBuild](https://blue-build.org) Fedora Atomic image for x86_64 kiosks,
managed through [NOVA Kiosk](https://github.com/novakiosk/novakiosk).
It includes Sway, Chromium, [NOVA Agent](https://github.com/novakiosk/agent),
[NOVA Keys](https://github.com/novakiosk/novakeys), CUPS printing, and remote
view/control through the Agent's outbound connection.

## Install and enroll

Generate an installer from the published image with the
[BlueBuild CLI](https://blue-build.org/how-to/generate-iso/):

```sh
sudo bluebuild generate-iso --iso-name novakiosk-os.iso image ghcr.io/novakiosk/os:latest
```

Write the ISO to a USB drive and boot it. During installation, create a separate
administrator account; do not name it `kiosk`. The image provides the `kiosk`
account, starts its graphical session automatically, and keeps its password locked.
Use the administrator account for SSH and maintenance; `sudo nmtui` configures
networking if needed.

Create an enrollment code in your NOVA Kiosk instance, then run:

```sh
sudo -u kiosk /usr/bin/novakiosk-agent smoke \
  --instance https://kiosk.example.com \
  --state-dir /var/lib/novakiosk-agent
```

Enter the code when prompted and approve the machine in the admin UI. The Agent
service takes over automatically after enrollment; no separate foreground process
is needed. Content, keyboard settings, printers, and remote access are managed
through NOVA Kiosk. Chromium uses the kiosk's default printer and hides Save as PDF.
Additional printer drivers may need to be added to the image recipe.

To check enrollment and view Agent logs:

```sh
sudo -u kiosk novakiosk-agent status --state-dir /var/lib/novakiosk-agent
sudo journalctl _SYSTEMD_USER_UNIT=novakiosk-agent.service -f
```

## Updates

Each image build downloads the latest stable Agent and NOVA Keys releases,
checks their `SHA256SUMS` and executable versions, and installs the binaries in
`/usr/bin`. Each application's license and bundled dependency notices are kept
under `/usr/share/licenses/novakiosk-agent/` or `/usr/share/licenses/novakeys/`.
Services and configuration come from this repository.

GitHub Actions builds daily at 06:00 UTC, on code changes, and on manual runs.
A new application release is included in the next successful image build.
Installed kiosks receive it by updating their OS image and rebooting:

```sh
sudo rpm-ostree upgrade
sudo systemctl reboot
```

The admin UI's **Stage system update** action stages the same update; restart
separately to activate it. `rpm-ostree status` shows deployed versions. To return
to the previous OS deployment, run `sudo rpm-ostree rollback` and reboot.

## Customize and build

Edit [recipes/recipe.yml](recipes/recipe.yml) for packages and modules, and
[files/](files/) for system configuration. Follow BlueBuild's
[local build guide](https://blue-build.org/how-to/local/) or use
the included GitHub Actions workflow. Forks need their own
[signing key and `SIGNING_SECRET`](https://blue-build.org/how-to/cosign/).
Local builders must rebuild the installer layers to pick up newer application
releases; a cached layer retains its previous downloads.

## Project

Built for [NOVA Spektrum](https://novaspektrum.no) and published with permission.
Maintained personally by the author, not supported or warranted by NOVA Spektrum.
The NOVA Spektrum name is not covered by the [Apache-2.0 license](LICENSE).
