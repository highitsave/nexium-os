#!/bin/bash
set -euxo pipefail
root=work/root
sudo cat "$root/etc/os-release" | tee reports/browser/debian-base.txt
sudo chroot "$root" dpkg-query -W -f='${Package}\t${Version}\t${Installed-Size}\n' > reports/browser/packages-before.tsv
sudo chroot "$root" apt-cache policy python3-pyside6 python3-pyside6.qtwebenginewidgets python3-pyside6.qtwebenginecore python3-pyqt6.qtwebengine libqt6webenginecore6 qt6-webengine | tee reports/browser/debian-pyside6-availability.txt
sudo chroot "$root" apt-cache search pyside6 | tee reports/browser/pyside6-search.txt
pkgs=$(sudo chroot "$root" dpkg-query -W -f='${Package}\n' | grep -E '^(ungoogled-chromium|chromium)(-|$)' || true)
sudo du -sb "$root/opt/ungoogled-chromium" | tee reports/browser/standalone-chromium-bytes.txt
if [ -n "$pkgs" ]; then sudo chroot "$root" env DEBIAN_FRONTEND=noninteractive apt-get purge -y $pkgs; fi
sudo rm -rf "$root/opt/ungoogled-chromium"
sudo rm -f "$root/usr/bin/chromium" "$root/usr/bin/ungoogled-chromium"
native='python3 python3-venv ca-certificates libglib2.0-0 libdbus-1-3 libfontconfig1 libfreetype6 libgl1 libegl1 libopengl0 libnss3 libnspr4 libxkbcommon0 libxkbcommon-x11-0 libxcomposite1 libxdamage1 libxrandr2 libxfixes3 libdrm2 libgbm1 libasound2 libxcb1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xfixes0 libxcb-xkb1 libx11-xcb1 libxrender1 libxext6 libx11-6'
sudo chroot "$root" env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends $native
sudo chroot "$root" python3 -m venv /opt/nexium-browser/venv
sudo chroot "$root" /opt/nexium-browser/venv/bin/pip install --only-binary=:all: --no-cache-dir PySide6
sudo chroot "$root" /opt/nexium-browser/venv/bin/pip freeze | tee reports/browser/python-lock.txt
sudo chroot "$root" /opt/nexium-browser/venv/bin/python -c 'import PySide6; from PySide6.QtWebEngineWidgets import QWebEngineView; from PySide6.QtWebEngineCore import QWebEngineProfile,QWebEnginePage; print("PySide6",PySide6.__version__); print("PASS QTWEBENGINE IMPORTS")' | tee reports/browser/imports.txt
sudo du -sb "$root/opt/nexium-browser/venv" | tee reports/browser/pyside6-footprint.txt
for bin in $(sudo find "$root/opt/nexium-browser" -name QtWebEngineProcess -o -name libQt6WebEngineCore.so.6 -o -name libqxcb.so); do
  target=${bin#work/root}
  sudo chroot "$root" ldd "$target" | tee -a reports/browser/loader.txt
done
! grep -q 'not found' reports/browser/loader.txt
sudo chroot "$root" dpkg-query -W -f='${Package}\t${Version}\t${Installed-Size}\n' > reports/browser/packages-after.tsv
python3 - <<'PY'
from pathlib import Path
import json
def read(name):
    return {p:(v,int(k or 0)*1024) for p,v,k in (l.split('\t') for l in Path(name).read_text().splitlines())}
before=read('reports/browser/packages-before.tsv');after=read('reports/browser/packages-after.tsv')
added={p:{'version':v,'installed_bytes':n,'before_bytes':before.get(p,('',0))[1]} for p,(v,n) in after.items() if before.get(p)!=(v,n)}
removed={p:{'version':v,'installed_bytes':n} for p,(v,n) in before.items() if p not in after}
venv=int(Path('reports/browser/pyside6-footprint.txt').read_text().split()[0])
delta=sum(v['installed_bytes']-v['before_bytes'] for v in added.values())
savings=sum(v['installed_bytes'] for v in removed.values())
report={'baseline_iso_user_reported_bytes':764084224,'ceiling_bytes':1000000000,'headroom_bytes':235915776,'pyside6_venv_apparent_bytes':venv,'native_package_delta_installed_bytes':delta,'removed_packages_installed_bytes':savings,'uncompressed_conservative_addition_without_removal':764084224+venv+delta,'uncompressed_budget_with_package_removal':764084224+venv+delta-savings,'important':'Installed footprint is NOT compressed ISO size. Only rebuilt ISO stat determines fit. Debian PyQt6 does not provide PySide6 modules; compatible pinned wheel lock is used.','added_or_changed':added,'removed':removed,'largest_remaining_packages':sorted([{'name':p,'bytes':n} for p,(v,n) in after.items()],key=lambda x:x['bytes'],reverse=True)[:15]}
Path('reports/browser/size-math.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
PY
