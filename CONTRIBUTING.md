# Contributing to Nexium OS

Open an issue explaining the problem, affected commit/image and evidence, or submit a focused pull request. Do not post passwords, tokens, private user data or recovery codes. Use a public-safe commit identity.

## Development and checks

- Read SPEC.md and the selected workflow before changing generated desktop/branding code. Keep changes reproducible in the generator or a documented patch helper.
- Run `python3 -m py_compile browser/nexium_browser.py browser/nexium_launchers.py scripts/*.py` and `python3 scripts/test-browser-chooser.py` for browser changes. Use PyYAML to parse all `.github/workflows/*.yml` before dispatch; GitHub's own workflow validation is also required.
- For privileged image builds use a disposable Linux build environment and the README workflow. Never bypass the byte ceiling, real-window assertion, ten original dock pins/icons, source identity, firmware/admin checks or boot-preservation gates to make a job green.
- Record actual ISO bytes/SHA-256 and final-image test evidence. A running process, 1x1 window, package download size, or green job alone is not proof of a usable browser or fitting ISO.
- Added sites must validate URLs, persist under the user's home, support removal and open without shell interpolation. Default search stays DuckDuckGo, with Bing selectable; do not add Google defaults.
- Preserve third-party copyright/license notices. Do not contribute proprietary assets without distribution rights. Describe provenance and applicable licenses for artwork/vendor sources.

Contributions to original project code are under the MIT License unless explicitly agreed otherwise. This does not override third-party licensing. Do not publish releases or contact users from automated workflows without project authorization.

Login/persistence changes must retain the original boot structures and exact persistence-only GRUB delta check. Require captured branded greeter before and after reboot, normal-user login, a changed boot ID and persistent marker on labeled storage. Never describe live credentials or passwordless sudo as hardened security. Do not run the destructive partition formatter on a user's drive during CI; use a disposable virtual disk.
