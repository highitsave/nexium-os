#!/bin/bash
set -euo pipefail
root=work/root
before=reports/browser/chooser-packages-before.tsv
sudo chroot "$root" dpkg-query -W -f='${Package}\t${Version}\t${Installed-Size}\n' > "$before"
sudo mkdir -p "$root/usr/share/keyrings"
curl -fsSL https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg | sudo tee "$root/usr/share/keyrings/brave-browser-archive-keyring.gpg" >/dev/null
echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/brave-browser-archive-keyring.gpg] https://brave-browser-apt-release.s3.brave.com/ stable main' | sudo tee "$root/etc/apt/sources.list.d/brave-browser-release.list"
sudo chroot "$root" apt-get update
for p in firefox-esr brave-browser; do
  sudo chroot "$root" apt-cache show --no-all-versions "$p" | tee "reports/browser/$p-metadata.txt"
  sudo chroot "$root" apt-get -s install --no-install-recommends "$p" | tee "reports/browser/$p-simulated-deps.txt"
done
sudo chroot "$root" env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends firefox-esr brave-browser
sudo chroot "$root" dpkg-query -W -f='${Package}\t${Version}\t${Installed-Size}\n' > reports/browser/chooser-packages-after.tsv
sudo chroot "$root" apt-get clean
python3 - <<'PY'
import json,re
from pathlib import Path
def read(n):return {p:(v,int(s or 0)*1024) for p,v,s in (l.split('\t') for l in Path(n).read_text().splitlines())}
before=read('reports/browser/chooser-packages-before.tsv');after=read('reports/browser/chooser-packages-after.tsv')
entries={}
for name in ['firefox-esr','brave-browser']:
    text=Path(f'reports/browser/{name}-metadata.txt').read_text()
    def value(k):return re.search(r'^'+k+r': (.*)$',text,re.M)[1]
    entries[name]={'version':value('Version'),'deb_package_bytes':int(value('Size')),'installed_bytes':after[name][1],'debian_metadata_installed_bytes':int(value('Installed-Size'))*1024,'filename':value('Filename')}
extra={p:{'version':v,'installed_bytes':s,'previous_bytes':before.get(p,('',0))[1]} for p,(v,s) in after.items() if before.get(p)!=(v,s)}
report={'current_iso_bytes':777256960,'ceiling_bytes':1000000000,'headroom_bytes':1000000000-777256960,'browsers':entries,'added_or_changed':extra,'both_installed_delta_bytes':sum(v['installed_bytes']-v['previous_bytes'] for v in extra.values()),'caution':'DEB and installed sizes are not the compressed ISO delta. Fit is measured by rebuilding candidate ISO with xz and unchanged boot inputs.','existing_pyside6_venv_apparent_bytes':716222983,'previous_native_package_delta_bytes':4969472}
Path('reports/browser/browser-sizes.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
PY
