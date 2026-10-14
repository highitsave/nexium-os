# Nexium OS

Nexium OS is an experimental amd64 Debian live-image project by Onx. The Golden Gate desktop uses Openbox, Plank, Tint2, PCManFM and Xterm, with a cream Plymouth splash. Nexium Browser is a Python/PySide6 QtWebEngine application. Messages, Calls and Vault are explicitly coming-soon placeholders, not working services.

## Browser chooser

The chooser offers Nexium Browser and any installed Firefox ESR/Brave binaries. Uninstalled browsers are disabled, not claimed to ship. Add browser / Add site validates http(s) URLs, prefixes https:// when omitted, and saves entries in `~/.config/nexium-browser/launchers.json`; Remove deletes a saved entry. Site links open in Nexium Browser tabs. DuckDuckGo is the default search engine; Bing is selectable. DuckDuckGo Browser and Safari are not Linux binaries shipped by this project.

Config survives app restarts. A RAM-only live session does **not** retain its home directory across reboot unless the live system has persistent storage; this project does not promise persistence on an unconfigured USB.

## Build

The supported cloud build is `.github/workflows/nexium-browser-complete.yml`, manually dispatched on main. It validates every workflow YAML, materializes the desktop, installs pinned/recorded browser dependencies, measures complete compressed candidate ISO images, chooses the largest set below 1,000,000,000 bytes, verifies boot preservation, and boots the final image in headless QEMU for GUI checks. Python package locks and exact measurements are retained in its verification artifact. It requires the repository's existing immutable base artifact `nexium-tab-1.2-ungoogled-iso` from run 38179706990; if that artifact expires, it must be restored from the same verified source, not replaced silently.

For a Linux build machine, inspect the workflow's dependency installation and run `python3 desktop/phase2.py --materialize`, `python3 scripts/prepare-ios4.py`, `python3 scripts/complete-chooser-fixes.py`, then `bash scripts/build-browser-chooser.sh` with the verified source ISO under `source/` and empty `work/`, `output/`, and `reports/boot/frames/` directories. The build requires sudo, chroot/mount support, several GB of free disk/RAM and network access. Expected base ISO: 661454848 bytes, SHA-256 `9a1cfad24c2f06a5a94eea73a89f0f495c5e045a4287cf4435f2940c1a1507f5`. Do not run the privileged build scripts on an untrusted checkout.

## Download and boot

Successful builds provide `nexium-browser-chooser-iso` containing the ISO and SHA256SUMS, plus `nexium-browser-chooser-verification`. Verify SHA-256 before writing or booting. Write the ISO as an image to a USB device using a trusted image writer; writing erases that device, so back it up and double-check the target. Boot amd64 BIOS or UEFI firmware. Secure Boot compatibility is not promised. Artifacts are build outputs, not published releases.

## Verification and limitations

The final gate requires a real mapped PID-owned Nexium window, normal geometry, painted nonblank pixels, a live chooser/restart test, Plank, cream splash and noninteractive sudo. The workflow fails on a failed GUI check and prints browser stdout/stderr. Kernel and GRUB configuration, EFI payload and original boot/system-area structure are preservation-checked; initrd is intentionally regenerated for Plymouth. QEMU/Xvfb evidence is not physical hardware validation. There is no guarantee that a particular Wi-Fi adapter or Lenovo model works until tested on that hardware. The live desktop uses passwordless sudo for the live user: do not treat it as a hardened multi-user system.

## License and third-party components

Original project code is under the MIT License in LICENSE. Debian packages, Firefox, Brave, Qt/PySide6, Chromium/QtWebEngine, bundled firmware, imported vendor sources and artwork retain their own licenses/notices. MIT does not relicense third-party assets or grant trademark rights. Before redistribution, review those licenses and provenance; especially supplied icon-sheet artwork. See CONTRIBUTING.md. No release is created by the build workflow.

## Real login and USB persistence

The login/persistence workflow is `.github/workflows/nexium-login-persistence.yml`. It builds on the measured Firefox ESR + Nexium Browser image, adds lightweight LightDM/GTK greeter and Golden Gate branding, disables the kiosk auto-session, and boots to a password prompt for the normal `nexium` user. Public initial **live-image** credentials are `nexium` / `nexium`; this is not a private account secret. Change the password locally with `passwd`; root login is not the desktop default. Passwordless sudo is still enabled for the live user, so this is NOT a hardened security boundary. No cloud authentication service or Google login is used.

All live GRUB kernel entries add `persistence`. The preservation verifier now requires the exact original grub.cfg plus only that parameter; it does not waive kernel, EFI payload, El Torito, GRUB2/MBR/system-area or initrd-theme checks. The kernel stays byte-identical. The initrd is regenerated with Debian live-boot/Plymouth support and verified against the cream-theme source.

Persistence is stored on the USB stick, NOT inside the ISO. Required layout: partition 1 holds the ISO/image as written; a separate partition 2 in **unused space beyond the image** is ext4, labeled exactly `persistence`, with a root-level `persistence.conf` containing exactly `/ union`. At least 256 MiB (preferably 512 MiB or more) must remain beyond the ISO. A nominal 1 GB stick may boot an under-1,000,000,000-byte ISO but does not have enough space for the recommended persistence layout. A larger stick is required; do not erase a drive or assume persistence works without that partition.

Rufus alone does not create this Debian persistence partition. After writing the image, use a Linux partition editor to create partition 2 in unallocated space, without modifying the ISO boot partitions. Back up the stick first and verify the actual device name and partition table. Some writers leave no editable free space or an incompatible layout; do not force a partition change in that case. Run the included `sudo nexium-persistence-setup /dev/sdX2 --format-this-partition` ONLY after substituting and verifying the new unused second partition. The script refuses whole disks, mounted partitions and partitions other than number 2, formats that partition (destroying its contents), labels it, and installs the shipped `/usr/share/nexium/persistence.conf` template. Manual equivalent after safely formatting: mount the ext4 partition and write `/ union` plus newline to `persistence.conf` at its root; unmount cleanly. Reboot the persistence-enabled entry. User files, browser/site config, password changes and installed packages can then persist; unplugging power without shutdown can corrupt it.

CI tests a labeled ext4 filesystem on a separate virtual USB storage disk: write a marker as the normal user, cleanly reboot, log in again, check a different kernel boot ID and the original marker, and test Add/remove site across separate app processes. This proves the live-boot path in QEMU, not that any particular physical USB stick is healthy or partitioned correctly. Consult the actual run's receipt before claiming a passing test.
