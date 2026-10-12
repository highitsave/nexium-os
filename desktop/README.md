# Nexium Phase 2

The inspected repaired Tab 1.2 base is a custom Xorg/Matchbox Chromium kiosk,
not XFCE. The inspection exposed no native panel, file manager or terminal.
Plymouth 22.02.122-3 is present. See inspection runs 38185136150 and 38185258316.
This layer replaces the kiosk session (not the boot equipment) with Openbox,
Plank, Tint2 and native Debian applications. Existing Matchbox and kiosk web
source are retained, inactive. Chromium remains the one ungoogled browser.

## Reproduction
Run `python3 desktop/phase2.py --materialize` (requires rsvg-convert), then use
`.github/workflows/phase2-build.yml` or its documented shell commands.
The workflow verifies the exact repaired base checksum, installs the package
list in its extracted root, overlays this source, uses the existing patch
compression flags and repair workflow boot verifier, and publishes artifacts.
Every installed overlay file is SHA256 checked in the output squashfs.
APT versions are reported in the artifact; Debian archive updates can change
package versions. This is repeatable configuration, not a bit-reproducible ISO.

## Interaction and limitations
Ten initial Plank pins; real apps have native windows, running indicators and
Plank pin/unpin. Icons and arrangement are provisional pending the supplied
Mac pack. Tint2 provides launcher, tasks, clock, battery and XEmbed tray.
NetworkManager applet appears when supported; hardware/audio/battery behavior
requires actual hardware testing. Openbox supplies Alt-Tab, window controls,
right-click menu, Super-E (Files), Super-T (Terminal), Super-S (Settings).
Picom supplies rounded corners only with a working compositor; GTK CSS also
rounds client-side windows. No expensive animation is required. Without
compositing, Openbox decorations remain square (honest fallback).
Welcome is shown once per writable HOME. Nonpersistent live changes vanish
on reboot; the default session does not install or write to internal disks.
Messages/Calls/Vault show explicit coming-soon dialogs, with no network,
message delivery, calls or software-install claims. They are NOT implemented.
System Information reads actual kernel/memory/package data. The Settings hub
opens appearance, window, network and audio tools, or system information.
Active cream made by TOMO! splash uses a regenerated initrd; see branding/boot/README.md.


## iOS4 sheet integration

After materializing, run `python3 scripts/prepare-ios4.py` (Pillow required). The resulting `NexiumIOS4` theme uses the supplied JPEG crops at 64px/128px. See `branding/icons/ios4/README.md` for provenance and explicit Files/Terminal/Trash substitutes. These current details supersede earlier reference-only icon notes.
