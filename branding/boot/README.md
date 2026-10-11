# Boot branding, preservation first
The source has Plymouth and Nexium-branded boot assets already. This build
keeps /live/vmlinuz, /live/initrd.img and /boot/grub/grub.cfg byte-identical.
A future Golden Gate Plymouth theme is staged in the rootfs, NOT activated
in the preserved initrd. No claim is made that the staged theme shows at boot.
Do not run update-initramfs in Phase 2; that would violate preservation.
Boot menu label remains NEXIUM_OS. See the reused repair boot verification.
