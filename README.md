# novakiosk-os

[![bluebuild build badge](https://github.com/novakiosk/os/actions/workflows/build.yml/badge.svg)](https://github.com/novakiosk/os/actions/workflows/build.yml)
![License](https://img.shields.io/github/license/novakiosk/os)

`novakiosk-os` is a minimal [BlueBuild](https://blue-build.org) Fedora Atomic image recipe
for kiosk machines managed by [novakiosk](https://github.com/novakiosk/novakiosk) (optionally
with [novakeys](https://github.com/novakiosk/novakeys)).

`novakiosk` communicates with a kiosk agent running on the kiosk machine; 
this image provides the Sway session + browser and the OS-level dependencies that the kiosk agent expects.

For `novakiosk-os`, the Atomic privilege prerequisites used during onboarding are baked into the image.
That means the generic onboarding permission-install step can be skipped on this image.

## What’s included

- Sway session with auto-login via `greetd` (starts Sway as the `kiosk` user), including a
  VNC-accessible headless output with USB HID keyboard/scanner input when no monitor is connected
- Firefox as a system Flatpak (`org.mozilla.firefox`) for kiosk display
- Chromium as a system Flatpak (`org.chromium.Chromium`) for kiosks that need its more reliable
  custom/borderless CUPS media handling
- Firefox and Chromium enterprise policies for kiosk defaults (including auto-installing selected extensions)
- `ydotool` for kiosk agent automation (e.g. forcing refresh / sending input)
- `wayvnc` for remote view/control (used by novakiosk’s VNC feature)
- `openssh-server` + `openssl` for direct SSH access and key management
- Build tooling used by kiosk-agent dependencies (e.g. `gcc-c++`/`make`/`python3` for `node-pty`, used for
  novakiosk's built-in web terminal) + `libatomic` for some Node.js runtimes
- A root-owned Atomic update helper at `/usr/libexec/novakiosk-system-update`
- A matching system unit at `/usr/lib/systemd/system/novakiosk-system-update@.service`
- A polkit rule allowing the `kiosk` user/group to reboot, power off, and start
  `novakiosk-system-update@rpm-ostree.service`

## Firefox policies & extensions (Flatpak)

Firefox is installed from Flathub as a system Flatpak (`org.mozilla.firefox`). We manage Firefox defaults
(including extensions) using Firefox Enterprise Policies via the Flatpak `org.mozilla.firefox.systemconfig`
extension point.

Policy source (in the image):

- `/usr/share/novakiosk/firefox/policies/policies.json`

Policy location (generated on boot; treated as image-managed and refreshed on every boot):

- `/var/lib/flatpak/extension/org.mozilla.firefox.systemconfig/<arch>/stable/policies/policies.json`

Included extensions (auto-installed via policy):

- “I still don’t care about cookies” — needed because the novakiosk receiver renders sites inside an iframe,
  so cookie banners tend to reappear frequently during navigation.

Other kiosk defaults applied via policy:

- Disable password saving / password manager UI
- Disable form history + address/credit card autofill
- Disable telemetry, studies, Pocket, Firefox Accounts, and feedback prompts
- Disable Developer Tools and block `about:config`
- Force links opened by sites to reuse the same tab (best-effort; depends on site behavior)
- Work around a Firefox Wayland `-kiosk` black-screen issue by setting `widget.wayland.vsync.enabled=false`

## Chromium printing fallback (Flatpak)

Firefox remains the default browser, and Chromium is installed alongside it. This is useful for label and 
receipt printers whose CUPS queue uses custom or borderless media. A variable-size PPD can store a custom 
default such as `Custom.90x70mm` without advertising it as a named paper-size choice, so Firefox may not show
that default in its print dialog. Separately, Firefox has a
[known Linux/GTK printing bug](https://bugzilla.mozilla.org/show_bug.cgi?id=1914238) that can render custom
borderless output using A4 geometry. Chromium uses a different printing path and is therefore the recommended
browser for kiosks affected by these issues.

Chromium's kiosk policies are delivered through its Flatpak `org.chromium.Chromium.Extension` extension point.

Policy source (in the image):

- `/usr/share/novakiosk/chromium/policies/managed/policies.json`

Policy location (generated on boot; treated as image-managed and refreshed on every boot):

- `/var/lib/flatpak/extension/org.chromium.Chromium.Extension.novakiosk/<arch>/1/policies/managed/policies.json`

The policies disable password saving, autofill, browser sign-in/sync, telemetry, feedback, and Developer Tools;
keep printing enabled; suppress default-browser prompts; and force-install “I still don’t care about cookies” from
the Chrome Web Store.

## Intended use

This repo is primarily an internal recipe, but it is shared for anyone building kiosks with
`novakiosk`/`novakeys` who wants a small, reproducible Fedora Atomic base.

The defaults are opinionated. If you need a different setup, expect to fork and
adjust the recipe.

Note: this repo does not ship the kiosk agent itself; it only provides the OS image and its
dependencies. The kiosk agent is served when onboarding the kiosk via the novakiosk web interface.

This project was built for [NOVA Spektrum](https://novaspektrum.no) in Norway and is
published with their permission. It is maintained by the author personally and
is not maintained, supported, or warranted by NOVA Spektrum.

NOVA Spektrum is a registered name and is not covered by this license.

## Installation (rebase)

> [!WARNING]  
> [This is an experimental feature](https://www.fedoraproject.org/wiki/Changes/OstreeNativeContainerStable),
> try at your own discretion.

To rebase an existing Fedora Atomic system to the latest build:

- First rebase to the unsigned image, to get the proper signing keys and policies installed:
  ```
  rpm-ostree rebase ostree-unverified-registry:ghcr.io/novakiosk/os:latest
  ```
- Reboot to complete the rebase:
  ```
  systemctl reboot
  ```
- Then rebase to the signed image, like so:
  ```
  rpm-ostree rebase ostree-image-signed:docker://ghcr.io/novakiosk/os:latest
  ```
- Reboot again to complete the installation
  ```
  systemctl reboot
  ```

## ISO

Prebuilt ISO snapshot: [novakiosk-os-20260824.iso](http://static.nova.onl/novakiosk-os-20260824.iso)

Checksum (SHA256): 1a9daac69fcb81262a84ee52c556335f8a949d686f81c2e4a38bc31cdf57485a

Note: After the first installation, you will be prompted to enroll the secure boot key in the BIOS.

Enter the password `universalblue` when prompted to enroll the key.

### Passwords / polkit / SSH

This image auto-logs into the `kiosk` account locally. The `kiosk` user is created at boot (via `systemd-sysusers`) and is intended to be a dedicated kiosk/service user, not your day-to-day admin account.

Important:
- Create a **separate admin user** during installation and use **that** user for SSH and administrative tasks. Do **not** name your admin user `kiosk`.
- The `kiosk` user’s password is **locked** by default (no password login). This is intentional and helps avoid interactive logins as `kiosk`.
- `kiosk` is **not** a general-purpose sudo user. On this image, the kiosk privilege model is polkit-based:
  - `systemctl reboot`
  - `systemctl poweroff`
  - `systemctl start --wait novakiosk-system-update@rpm-ostree.service`
