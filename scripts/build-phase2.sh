#!/bin/bash
set -euxo pipefail
iso=$(find source -name '*.iso' -print -quit)
test -n "$iso"
test "$(stat -c%s "$iso")" = 661454848
echo '9a1cfad24c2f06a5a94eea73a89f0f495c5e045a4287cf4435f2940c1a1507f5  '"$iso" | sha256sum -c -
cp "$iso" work/orig.iso
xorriso -indev work/orig.iso -report_el_torito plain -report_system_area plain > reports/original-boot.txt 2>&1
xorriso -osirrox on -indev work/orig.iso -extract / work/original
sudo unsquashfs -d work/root work/original/live/filesystem.squashfs
sudo cp -a work/root/etc/resolv.conf work/resolv.saved
sudo rm -f work/root/etc/resolv.conf
sudo cp /etc/resolv.conf work/root/etc/resolv.conf
if [ -e work/root/usr/sbin/policy-rc.d ]; then sudo cp -a work/root/usr/sbin/policy-rc.d work/policy.saved; fi
printf '#!/bin/sh\nexit 101\n' | sudo tee work/root/usr/sbin/policy-rc.d
sudo chmod +x work/root/usr/sbin/policy-rc.d
sudo mount -t proc proc work/root/proc
sudo mount --rbind /dev work/root/dev
sudo mount --make-rslave work/root/dev
sudo mount --bind /sys work/root/sys
cleanup() { sudo umount -R work/root/tmp/.X11-unix 2>/dev/null || true; sudo umount -R work/root/proc 2>/dev/null || true; sudo umount -R work/root/sys 2>/dev/null || true; sudo umount -R work/root/dev 2>/dev/null || true; }
trap cleanup EXIT
sudo chroot work/root apt-get update
packages=$(grep -v '^#' desktop/packages.txt | xargs)
sudo chroot work/root env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends $packages gnome-themes-extra
sudo chroot work/root apt-get clean
sudo python3 desktop/phase2.py --install work/root | tee reports/install.txt
sudo chroot work/root dpkg-query -W > reports/installed-packages.tsv
# Native application/Xorg smoke test only; not an ISO boot test.
Xvfb :99 -screen 0 1280x800x24 -ac > reports/xvfb.log 2>&1 &
sleep 2
sudo mkdir -p work/root/tmp/.X11-unix
sudo mount --bind /tmp/.X11-unix work/root/tmp/.X11-unix
sudo chroot work/root runuser -u nexium -- env HOME=/home/nexium DISPLAY=:99 /usr/local/lib/nexium/session > reports/desktop-smoke.log 2>&1 &
sleep 10
DISPLAY=:99 xwininfo -root -tree | tee reports/windows.txt
for app in pcmanfm xterm mousepad lxtask; do
  sudo chroot work/root runuser -u nexium -- env HOME=/home/nexium DISPLAY=:99 "$app" > "reports/$app.log" 2>&1 &
done
sleep 8
DISPLAY=:99 xwininfo -root -tree | tee reports/native-app-windows.txt
DISPLAY=:99 xprop -root _NET_SUPPORTING_WM_CHECK _NET_CLIENT_LIST | tee reports/window-manager.txt
DISPLAY=:99 xwd -root -silent -out reports/desktop.xwd || true
sudo pkill -u "$(awk -F: '$1=="nexium" {print $3}' work/root/etc/passwd)" || true
sleep 2
cleanup
sudo rm -f work/root/etc/resolv.conf work/root/usr/sbin/policy-rc.d
sudo cp -a work/resolv.saved work/root/etc/resolv.conf
if [ -e work/policy.saved ]; then sudo cp -a work/policy.saved work/root/usr/sbin/policy-rc.d; fi
# Smoke test must not suppress first-run Welcome in the live image.
sudo rm -rf work/root/home/nexium/.local/state/nexium work/root/home/nexium/.cache
sudo python3 desktop/phase2.py --install work/root > reports/reinstall.txt
sudo find work/root -type f -path '*/.Xauthority' -delete
sudo rm -f work/root/tmp/.X*-lock
sudo mksquashfs work/root work/new.squashfs -noappend -comp xz -b 1048576 -Xdict-size 1048576 -Xbcj x86 -processors 2
out=output/nexium-os-1.2-ungoogled-amd64.iso
xorriso -indev work/orig.iso -outdev "$out" -boot_image any replay -map work/new.squashfs /live/filesystem.squashfs -commit -end
xorriso -indev "$out" -report_el_torito plain -report_system_area plain > reports/final-boot.txt 2>&1
xorriso -osirrox on -indev "$out" -extract / work/final
python3 scripts/verify-phase2-boot.py | tee reports/boot-verification.txt
sudo unsquashfs -d work/final-root work/final/live/filesystem.squashfs
sudo python3 desktop/phase2.py --verify work/final-root | tee reports/desktop-verification.txt
unsquashfs -s work/final/live/filesystem.squashfs | tee reports/squashfs.txt
test "$(stat -c%s "$out")" -lt 1000000000
sha256sum "$out" | tee output/SHA256SUMS reports/iso-sha256.txt
python3 - <<'PY' | tee reports/size.txt
from pathlib import Path
size=Path('output/nexium-os-1.2-ungoogled-amd64.iso').stat().st_size
print('ISO:',size,'bytes')
print('ISO:',size/1000000,'MB (decimal)')
print('Under 1,000,000,000 bytes:',size<1000000000)
PY
{ echo '## Nexium Phase 2 native desktop'; cat reports/source-commit.txt reports/size.txt reports/iso-sha256.txt reports/boot-verification.txt reports/desktop-verification.txt reports/native-app-windows.txt; echo 'Xvfb native desktop smoke test, not a physical or virtual ISO boot test.'; } >> "$GITHUB_STEP_SUMMARY"
