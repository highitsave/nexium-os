#!/usr/bin/env bash
# Run as root in an Ubuntu 22.04 container, with this repository at /work.
set -euo pipefail
cd /work
export DEBIAN_FRONTEND=noninteractive
mkdir -p config/{archives,package-lists,packages.chroot,includes.chroot/usr/share/applications} reports
exec > >(tee reports/apps-resolution.log) 2>&1
printf 'Target: Ubuntu jammy amd64; recommendations disabled\n'
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl gnupg extrepo python3 xz-utils

# Official vendor instructions; never mix Debian distribution repositories into Ubuntu.
extrepo enable librewolf
extrepo update librewolf
curl -fsSL https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg -o /usr/share/keyrings/brave-browser-archive-keyring.gpg
curl -fsSL https://brave-browser-apt-release.s3.brave.com/brave-browser.sources -o /etc/apt/sources.list.d/brave-browser-release.sources
curl -fsSL https://updates.signal.org/desktop/apt/keys.asc | gpg --batch --yes --dearmor -o /usr/share/keyrings/signal-desktop-keyring.gpg
curl -fsSL https://updates.signal.org/static/desktop/apt/signal-desktop.sources -o /etc/apt/sources.list.d/signal-desktop.sources
curl -fsSL https://packages.element.io/debian/element-io-archive-keyring.gpg -o /usr/share/keyrings/element-io-archive-keyring.gpg
printf '%s\n' 'deb [signed-by=/usr/share/keyrings/element-io-archive-keyring.gpg] https://packages.element.io/debian/ default main' > /etc/apt/sources.list.d/element-io.list

# Mozilla's own native DEB repository provides ESR without Ubuntu's Snap wrapper.
# Reference: https://support.mozilla.org/en-US/kb/install-firefox-linux
curl -fsSL https://packages.mozilla.org/apt/repo-signing-key.gpg -o /usr/share/keyrings/packages.mozilla.org.asc
fingerprint="$(gpg --show-keys --with-colons /usr/share/keyrings/packages.mozilla.org.asc | awk -F: '$1=="fpr" {print $10; exit}')"
[[ "$fingerprint" == 35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3 ]]
printf '%s\n' 'deb [signed-by=/usr/share/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main' > /etc/apt/sources.list.d/mozilla.list
printf 'Package: *\nPin: origin packages.mozilla.org\nPin-Priority: 1000\n' > /etc/apt/preferences.d/mozilla
apt-get -o APT::Update::Error-Mode=any update

# Translate the official signed sources into live-build archive files.
# live-build imports each .key.chroot itself; do not use trusted=yes.
python3 - <<'PY'
from pathlib import Path
import shutil
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
    (root / f'nexium-mozilla.list.{stage}').write_text('deb [arch=amd64] https://packages.mozilla.org/apt mozilla main\n')
    shutil.copyfile('/usr/share/keyrings/packages.mozilla.org.asc', root / f'nexium-mozilla.key.{stage}')
    shutil.copyfile('/etc/apt/preferences.d/mozilla', root / f'nexium-mozilla.pref.{stage}')
PY

# Discord distributes a .deb, not a public apt repository.
curl -fL --retry 3 'https://discord.com/api/downloads/distributions/app/installers/latest?channel=stable&platform=linux&arch=x64&format=deb' -o config/packages.chroot/discord.deb
dpkg-deb --info config/packages.chroot/discord.deb

# The common ungoogled-chromium repo links to platform packaging/binaries.
# Pin the portablelinux GitHub release AND the hash published in its download index.
# These are contributor builds, not an upstream guarantee of binary authenticity.
uc_version=155.0.8059.39-1
uc_sha256=acc30f037e0080a0bf03456f8cf8cda4aca55a778b17174d0a4aaa8e7749cb79
uc_url="https://github.com/ungoogled-software/ungoogled-chromium-portablelinux/releases/download/${uc_version}/ungoogled-chromium-${uc_version}-x86_64_linux.tar.xz"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
curl -fL --retry 3 "$uc_url" -o "$work/ungoogled.tar.xz"
printf '%s  %s\n' "$uc_sha256" "$work/ungoogled.tar.xz" | sha256sum -c -
mkdir -p "$work/pkg/opt/ungoogled-chromium" "$work/pkg/usr/bin" "$work/pkg/usr/share/applications" "$work/pkg/DEBIAN"
tar -xJf "$work/ungoogled.tar.xz" --strip-components=1 -C "$work/pkg/opt/ungoogled-chromium"
test -x "$work/pkg/opt/ungoogled-chromium/chrome"
if [[ -f "$work/pkg/opt/ungoogled-chromium/chrome-sandbox" ]]; then
  chown root:root "$work/pkg/opt/ungoogled-chromium/chrome-sandbox"
  chmod 4755 "$work/pkg/opt/ungoogled-chromium/chrome-sandbox"
fi
cat > "$work/pkg/usr/bin/ungoogled-chromium" <<'SH'
#!/bin/sh
exec /opt/ungoogled-chromium/chrome "$@"
SH
chmod 755 "$work/pkg/usr/bin/ungoogled-chromium"
cat > "$work/pkg/usr/share/applications/ungoogled-chromium.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Ungoogled Chromium
Exec=ungoogled-chromium %U
Icon=web-browser
Terminal=false
Categories=Network;WebBrowser;
MimeType=text/html;x-scheme-handler/http;x-scheme-handler/https;
DESKTOP
uc_deps='ca-certificates, fonts-liberation, libasound2, libatk-bridge2.0-0, libatk1.0-0, libatspi2.0-0, libc6, libcairo2, libcups2, libdbus-1-3, libdrm2, libexpat1, libgbm1, libglib2.0-0, libgtk-3-0, libnspr4, libnss3, libpango-1.0-0, libudev1, libx11-6, libxcb1, libxcomposite1, libxdamage1, libxext6, libxfixes3, libxkbcommon0, libxrandr2, xdg-utils'
cat > "$work/pkg/DEBIAN/control" <<CONTROL
Package: ungoogled-chromium
Version: ${uc_version}+nexium1
Architecture: amd64
Maintainer: Onx <assistant@email.tomo.ai>
Installed-Size: $(du -sk "$work/pkg/opt" | cut -f1)
Depends: ${uc_deps}
Description: Ungoogled Chromium portable Linux release, packaged for Nexium
 Pinned contributor binary from ungoogled-software on GitHub.
CONTROL
dpkg-deb --root-owner-group -Zxz -z1 --build "$work/pkg" config/packages.chroot/ungoogled-chromium.deb
printf 'SOURCE ungoogled-chromium %s SHA256 %s\n' "$uc_url" "$uc_sha256"

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
if ! resolve firefox-esr; then
  # Mozilla's native Firefox is preferred to Ubuntu's transitional Snap package.
  resolve firefox || true
fi
apt-cache policy firefox-esr firefox chromium chromium-browser > reports/browser-origins.txt
apt-cache show firefox chromium-browser >> reports/browser-origins.txt 2>/dev/null || true
resolve chromium || true
for pkg in librewolf brave-browser telegram-desktop  network-manager openssh-client xorg xdg-utils; do
  resolve "$pkg" || true
done

# Validate the whole set including both local DEBs before installing smoke-test deps.
local_debs=(./config/packages.chroot/discord.deb ./config/packages.chroot/ungoogled-chromium.deb)
apt-get -s --no-install-recommends install "${resolved[@]}" "${local_debs[@]}" > reports/combined-plan.txt
printf 'RESOLVED discord %s (official .deb)\n' "$(dpkg-deb -f config/packages.chroot/discord.deb Version)"
printf 'COMBINED DEPENDENCY CHECK PASSED\n'
apt-get -y --print-uris --no-install-recommends install "${resolved[@]}" "${local_debs[@]}" > reports/download-plan.txt
cat reports/download-plan.txt

# Disposable Jammy container only: validate native linking/version, not a booted GUI.
# Never bypass Chromium's sandbox in the shipped launcher.
apt-get install -y --no-install-recommends ./config/packages.chroot/ungoogled-chromium.deb > reports/ungoogled-install.log 2>&1
ldd /opt/ungoogled-chromium/chrome > reports/ungoogled-ldd.txt 2>&1
if grep -E 'not found|version .* not found' reports/ungoogled-ldd.txt; then
  printf 'FAILED ungoogled-chromium: Jammy dynamic-link compatibility\n'
  exit 1
fi
ungoogled-chromium --version | tee reports/ungoogled-version.txt
printf 'RESOLVED ungoogled-chromium %s (SHA256-verified GitHub portablelinux; Jammy link/version test passed)\n' "$uc_version"
printf 'NOTE browser GUI/sandbox in a booted ISO remains untested\n'

python3 - <<'PY'
from pathlib import Path
apps = [('jitsi', 'Jitsi Meet', 'https://meet.jit.si/'), ('zoom', 'Zoom Web', 'https://app.zoom.us/wc/'), ('teams', 'Microsoft Teams Web', 'https://teams.microsoft.com/')]
for slug, name, url in apps:
    Path(f'config/includes.chroot/usr/share/applications/nexium-{slug}.desktop').write_text(f'[Desktop Entry]\nType=Application\nName={name}\nComment=Online service; requires an internet connection and a supported browser\nExec=xdg-open {url}\nIcon=web-browser\nTerminal=false\nCategories=Network;VideoConference;\n')
    print(f'WEB FALLBACK {name}: {url}')
PY
printf 'Prepared live-build package list, vendor archives, local DEBs and web launchers.\n'
printf 'Size goal: about 1 GB; actual ISO size remains unknown until a successful build.\n'
