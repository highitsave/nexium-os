#!/bin/bash
set -euxo pipefail
base=$(find source -name '*.iso' -print -quit)
seed=$(find seed -name '*.iso' -print -quit)
test "$(stat -c%s "$base")" -eq 661454848
echo "9a1cfad24c2f06a5a94eea73a89f0f495c5e045a4287cf4435f2940c1a1507f5  $base" | sha256sum -c -
test "$(stat -c%s "$seed")" -eq 862846976
echo "e6e23037bb041db61e175c449ce8bd7f2d444e84a848d7cb285d3bb8b02af243  $seed" | sha256sum -c -
cp "$base" work/orig.iso
xorriso -indev work/orig.iso -report_el_torito plain -report_system_area plain > reports/original-boot.txt 2>&1
xorriso -osirrox on -indev work/orig.iso -extract / work/original
xorriso -osirrox on -indev "$seed" -extract / work/seed
sudo unsquashfs -d work/root work/seed/live/filesystem.squashfs
sudo cp -a work/root/etc/resolv.conf work/resolv.saved
sudo rm work/root/etc/resolv.conf
sudo cp /etc/resolv.conf work/root/etc/resolv.conf
if [ -e work/root/usr/sbin/policy-rc.d ];then sudo cp -a work/root/usr/sbin/policy-rc.d work/policy.saved;fi
printf '#!/bin/sh\nexit 101\n' | sudo tee work/root/usr/sbin/policy-rc.d
sudo chmod +x work/root/usr/sbin/policy-rc.d
sudo mount -t proc proc work/root/proc
sudo mount --rbind /dev work/root/dev
sudo mount --make-rslave work/root/dev
sudo mount --bind /sys work/root/sys
cleanup(){ sudo umount -R work/root/proc 2>/dev/null || true;sudo umount -R work/root/dev 2>/dev/null || true;sudo umount -R work/root/sys 2>/dev/null || true; }
trap cleanup EXIT
sudo chroot work/root dpkg-query -W -f='${Package}\t${Installed-Size}\n' > reports/browser/login-packages-before.tsv
sudo chroot work/root apt-get update
sudo chroot work/root env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends lightdm lightdm-gtk-greeter live-boot live-config xdotool wmctrl scrot e2fsprogs util-linux
sudo chroot work/root apt-get clean
sudo chroot work/root dpkg-query -W -f='${Package}\t${Version}\t${Installed-Size}\n' > reports/browser/final-packages.tsv
sudo python3 scripts/nexium-phase2.py --install work/root | tee reports/install.txt
sudo python3 scripts/install-login.py install work/root
sudo python3 scripts/nexium-phase2.py --verify work/root | tee reports/preflight-desktop.txt
sudo python3 scripts/install-login.py verify work/root | tee reports/login-verification.txt
sudo chroot work/root plymouth-set-default-theme nexium-gold
mapfile -t kernels < <(sudo find -L work/root/lib/modules -mindepth 1 -maxdepth 1 -type d -printf '%f\n')
test "${#kernels[@]}" -eq 1
sudo mkdir -p work/root/tmp/nexium-initrd
sudo chroot work/root update-initramfs -c -k "${kernels[0]}" -b /tmp/nexium-initrd 2>&1 | tee reports/initrd-regeneration.txt
sudo cp "work/root/tmp/nexium-initrd/initrd.img-${kernels[0]}" work/new.initrd
sudo rm -rf work/root/tmp/nexium-initrd
cleanup
sudo rm -f work/root/etc/resolv.conf work/root/usr/sbin/policy-rc.d
sudo cp -a work/resolv.saved work/root/etc/resolv.conf
if [ -e work/policy.saved ];then sudo cp -a work/policy.saved work/root/usr/sbin/policy-rc.d;fi
install -m 0644 work/original/boot/grub/grub.cfg work/persistence-grub.cfg
python3 scripts/persistence-grub.py work/persistence-grub.cfg | tee reports/grub-change.txt
sudo mksquashfs work/root work/new.squashfs -noappend -comp xz -b 1048576 -Xdict-size 1048576 -Xbcj x86 -processors 2
out=output/nexium-os-1.2-ungoogled-amd64.iso
xorriso -indev work/orig.iso -outdev "$out" -boot_image any replay -map work/new.squashfs /live/filesystem.squashfs -map work/new.initrd /live/initrd.img -map work/persistence-grub.cfg /boot/grub/grub.cfg -commit -end
xorriso -indev "$out" -report_el_torito plain -report_system_area plain > reports/final-boot.txt 2>&1
xorriso -osirrox on -indev "$out" -extract / work/final
python3 scripts/verify-phase2-boot.py | tee reports/boot-verification.txt
sudo unsquashfs -d work/final-root work/final/live/filesystem.squashfs
sudo python3 scripts/nexium-phase2.py --verify work/final-root | tee reports/desktop-verification.txt
sudo python3 scripts/install-login.py verify work/final-root | tee reports/final-login-verification.txt
test "$(stat -c%s "$out")" -lt 1000000000
sha256sum "$out" | tee output/SHA256SUMS reports/iso-sha256.txt
stat -c 'ISO_BYTES=%s' "$out" | tee reports/size.txt
sudo cat work/final-root/etc/nexium-browsers.json | tee reports/browser/shipped-browsers.json
# 512 MiB ext4 persistence partition attached as a USB storage device to the VM.
truncate -s 536870912 work/persistence-disk.img
printf 'label: dos\n, ,83\n' | sfdisk work/persistence-disk.img
loop=$(sudo losetup --find --show --partscan work/persistence-disk.img)
sudo mkfs.ext4 -F -L persistence "${loop}p1"
mkdir -p work/persistence-mount
sudo mount "${loop}p1" work/persistence-mount
printf '/ union\n' | sudo tee work/persistence-mount/persistence.conf
sync;sudo umount work/persistence-mount;sudo losetup -d "$loop"
