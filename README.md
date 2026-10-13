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
