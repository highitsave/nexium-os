#!/usr/bin/env bash
# XAC Golden Gate installer. Original XAC work, MIT License.
set -euo pipefail
umask 022
here="$(cd -- "$(dirname -- "$0")" && pwd)"
root="${DESTDIR:-}"
backup="$root/var/backups/xac"
manifest="$root/usr/share/xac/installed-files.txt"

fail() { printf 'install-xac: %s\n' "$*" >&2; exit 1; }
for required in XAC.colors XAC-icons/index.theme XAC-dock/xac-dock-layout.sh XAC-sddm/Main.qml XAC-sddm/theme.conf XAC-sddm/background.svg; do
  [[ -f "$here/$required" ]] || fail "required asset missing: $required"
done
mkdir -p "$(dirname "$manifest")" "$backup"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

install_one() {
  local source="$1" destination="$2" relative old
  relative="${destination#"$root"}"
  if [[ -e "$destination" ]] && ! cmp -s -- "$source" "$destination"; then
    old="$backup$relative"
    if [[ ! -e "$old" ]]; then mkdir -p "$(dirname "$old")"; cp -a -- "$destination" "$old"; fi
  fi
  install -D -m 0644 -- "$source" "$destination"
  printf '%s\n' "$destination" >> "$tmp"
}

install_one "$here/XAC.colors" "$root/usr/share/color-schemes/XAC.colors"
while IFS= read -r -d '' file; do
  install_one "$file" "$root/usr/share/icons/XAC-icons/${file#"$here/XAC-icons/"}"
done < <(find "$here/XAC-icons" -type f -print0)
install_one "$here/XAC-dock/xac-dock-layout.sh" "$root/usr/share/xac/XAC-dock/xac-dock-layout.sh"
chmod 0755 "$root/usr/share/xac/XAC-dock/xac-dock-layout.sh"
while IFS= read -r -d '' file; do
  install_one "$file" "$root/usr/share/sddm/themes/XAC/${file#"$here/XAC-sddm/"}"
done < <(find "$here/XAC-sddm" -type f -print0)
install_one "$here/LICENSE" "$root/usr/share/doc/xac/LICENSE"
install_one "$here/README.md" "$root/usr/share/doc/xac/README.md"
install -D -m 0644 "$tmp" "$manifest"
printf 'XAC Golden Gate assets installed under %s/usr/share. No packages or AUR were used.\n' "$root"
