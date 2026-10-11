#!/usr/bin/env bash
# Run as root in an Ubuntu 22.04 container, with this repository at /work.
set -euo pipefail
cd /work
export DEBIAN_FRONTEND=noninteractive
mkdir -p config/{archives,package-lists,packages.chroot,includes.chroot/usr/share/applications} reports
exec > >(tee reports/apps-resolution.log) 2>&1
printf 'Target: Ubuntu jammy amd64; recommendations disabled\n'
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl gnupg extrepo python3

# Official vendor instructions; never mix Debian distribution repositories into Ubuntu.
extrepo enable librewolf
extrepo update librewolf
curl -fsSL https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg -o /usr/share/keyrings/brave-browser-archive-keyring.gpg
curl -fsSL https://brave-browser-apt-release.s3.brave.com/brave-browser.sources -o /etc/apt/sources.list.d/brave-browser-release.sources
curl -fsSL https://updates.signal.org/desktop/apt/keys.asc | gpg --batch --yes --dearmor -o /usr/share/keyrings/signal-desktop-keyring.gpg
curl -fsSL https://updates.signal.org/static/desktop/apt/signal-desktop.sources -o /etc/apt/sources.list.d/signal-desktop.sources
curl -fsSL https://packages.element.io/debian/element-io-archive-keyring.gpg -o /usr/share/keyrings/element-io-archive-keyring.gpg
printf '%s\n' 'deb [signed-by=/usr/share/keyrings/element-io-archive-keyring.gpg] https://packages.element.io/debian/ default main' > /etc/apt/sources.list.d/element-io.list
apt-get -o APT::Update::Error-Mode=any update

# Translate the official signed Deb822 sources into live-build archive files.
# live-build imports each .key.chroot itself; do not use trusted=yes.
python3 - <<'PY'
from pathlib import Path
import re, shutil
root = Path('config/archives')
vendors = [('librewolf', 'extrepo_librewolf.sources'), ('brave', 'brave-browser-release.sources'), ('signal', 'signal-desktop.sources')]
for name, filename in vendors:
    text = (Path('/etc/apt/sources.list.d') / filename).read_text()
    fields = {}
    for line in text.splitlines():
        if line and not line.startswith(('#', ' ', '\t')) and ':' in line:
            key, value = line.split(':', 1)
            fields[key.lower()] = value.strip()
    uri = fields['uris'].split()[0]
    suite = fields['suites'].split()[0]
    components = fields.get('components', 'main')
    keyfile = fields['signed-by'].split()[0]
    source = f'deb [arch=amd64] {uri} {suite} {components}\n'
    for stage in ('chroot', 'binary'):
        (root / f'nexium-{name}.list.{stage}').write_text(source)
        shutil.copyfile(keyfile, root / f'nexium-{name}.key.{stage}')
for stage in ('chroot', 'binary'):
    (root / f'nexium-element.list.{stage}').write_text('deb [arch=amd64] https://packages.element.io/debian/ default main\n')
    shutil.copyfile('/usr/share/keyrings/element-io-archive-keyring.gpg', root / f'nexium-element.key.{stage}')
PY

# Discord distributes a .deb, not a public apt repository.
curl -fL --retry 3 'https://discord.com/api/downloads/distributions/app/installers/latest?channel=stable&platform=linux&arch=x64&format=deb' -o config/packages.chroot/discord.deb
dpkg-deb --info config/packages.chroot/discord.deb

: > config/package-lists/nexium-apps.list.chroot
: > reports/unavailable.txt
resolved=()
resolve() {
  local pkg="$1" candidate
  candidate="$(apt-cache policy "$pkg" | awk '/Candidate:/ {print $2; exit}')"
  if [[ -n "$candidate" && "$candidate" != '(none)' ]] && apt-get -s --no-install-recommends install "$pkg" > "reports/${pkg}.log" 2>&1; then
    printf 'RESOLVED %s %s\n' "$pkg" "$candidate"
    printf '%s\n' "$pkg" >> config/package-lists/nexium-apps.list.chroot
    resolved+=("$pkg")
    return 0
  fi
  printf 'UNAVAILABLE %s (no installable jammy candidate)\n' "$pkg" | tee -a reports/unavailable.txt
  return 1
}
resolve firefox-esr || true
if ! resolve chromium; then
  resolve ungoogled-chromium || true
fi
for pkg in librewolf brave-browser telegram-desktop signal-desktop element-desktop network-manager openssh-client xorg xdg-utils; do
  resolve "$pkg" || true
done

# Validate the whole set together, including Discord dependencies.
apt-get -s --no-install-recommends install "${resolved[@]}" ./config/packages.chroot/discord.deb > reports/combined-plan.txt
printf 'RESOLVED discord %s (official .deb)\n' "$(dpkg-deb -f config/packages.chroot/discord.deb Version)"
printf 'COMBINED DEPENDENCY CHECK PASSED\n'
# Print download/installed-space estimates, not an ISO size claim.
apt-get -y --print-uris --no-install-recommends install "${resolved[@]}" ./config/packages.chroot/discord.deb > reports/download-plan.txt
cat reports/download-plan.txt

python3 - <<'PY'
from pathlib import Path
apps = [('jitsi', 'Jitsi Meet', 'https://meet.jit.si/'), ('zoom', 'Zoom Web', 'https://app.zoom.us/wc/'), ('teams', 'Microsoft Teams Web', 'https://teams.microsoft.com/')]
for slug, name, url in apps:
    Path(f'config/includes.chroot/usr/share/applications/nexium-{slug}.desktop').write_text(f'[Desktop Entry]\nType=Application\nName={name}\nComment=Online service; requires an internet connection and a supported browser\nExec=xdg-open {url}\nIcon=web-browser\nTerminal=false\nCategories=Network;VideoConference;\n')
    print(f'WEB FALLBACK {name}: {url}')
PY
printf 'Prepared live-build package list, vendor archives, Discord .deb and web launchers.\n'
printf 'Size goal: about 1 GB; actual ISO size remains unknown until a successful build.\n'
