"""Measure actual ISO bytes; largest count first, Firefox wins a one-extra-browser tie."""
import json,subprocess,importlib.util,hashlib
from pathlib import Path
def run(argv):subprocess.run(argv,check=True)
spec=importlib.util.spec_from_file_location('overlay','scripts/install-chooser-overlay.py');overlay=importlib.util.module_from_spec(spec);spec.loader.exec_module(overlay)
attempts=[]
options=[('both',[]),('Firefox',['brave-browser']),('Brave',['firefox-esr']),('Nexium only',['brave-browser'])]
for label,remove in options:
    if remove:
        run(['chroot','work/root','env','DEBIAN_FRONTEND=noninteractive','apt-get','purge','-y',*remove])
        if label=='Brave':
            # Restore the other measured candidate only if Firefox also exceeds the cap.
            saved=Path('work/root/etc/resolv.conf').read_bytes();Path('work/root/etc/resolv.conf').write_bytes(Path('/etc/resolv.conf').read_bytes())
            try:run(['chroot','work/root','env','DEBIAN_FRONTEND=noninteractive','apt-get','install','-y','--no-install-recommends','brave-browser'])
            finally:Path('work/root/etc/resolv.conf').write_bytes(saved)
        run(['chroot','work/root','apt-get','clean'])
    shipped=overlay.install('work/root')
    Path('work/new.squashfs').unlink(missing_ok=True)
    run(['mksquashfs','work/root','work/new.squashfs','-noappend','-comp','xz','-b','1048576','-Xdict-size','1048576','-Xbcj','x86','-processors','2'])
    trial=Path('output/candidate.iso');trial.unlink(missing_ok=True)
    run(['xorriso','-indev','work/orig.iso','-outdev',str(trial),'-boot_image','any','replay','-map','work/new.squashfs','/live/filesystem.squashfs','-map','work/new.initrd','/live/initrd.img','-commit','-end'])
    size=trial.stat().st_size
    record={'candidate':label,'shipped':shipped,'iso_bytes':size,'sha256':hashlib.sha256(trial.read_bytes()).hexdigest(),'under_ceiling':size<1000000000}
    attempts.append(record);print(json.dumps(record),flush=True)
    Path('reports/browser/fitting-set.json').write_text(json.dumps({'baseline_bytes':777256960,'ceiling_bytes':1000000000,'headroom_bytes':222743040,'attempts':attempts,'selected':record if size<1000000000 else None},indent=2)+'\n')
    trial.unlink()
    if size<1000000000:break
else:raise AssertionError('Nothing sensible fits without cutting preservation; stopped')
run(['python3','scripts/nexium-phase2.py','--verify','work/root'])
