# User-authorized iOS 4 sheet crops

The source is `IMG-0875.jpeg`, supplied by Avery with explicit permission to crop it. This is not a vector reconstruction or a bespoke icon pack. Upstream artwork ownership is not claimed. JPEG compression remains in the original pixels.

Run `python3 scripts/prepare-ios4.py` after `desktop/phase2.py --materialize` with Pillow installed. `manifest.json` records exact crop boxes and hashes. All 35 cells are cropped to 136x136, with rounded exterior alpha cleanup only, then resampled with LANCZOS to 128x128 and 64x64. No glyphs or new artwork are drawn. PNG dimensions and RGBA modes are checked after saving.

Dock substitutions: Files uses Utilities-folder; Terminal uses the blank linen cell; Trash uses the blank gray cell. These are explicitly substitutes because this sheet contains no actual Files, terminal or Trash glyphs. Browser uses Safari, Calls Phone, Messages SMS, Settings gears, Text Editor Notes, System Monitor Stocks, Vault Cydia. Adwaita/hicolor supply any unmapped system icons. Messages, Calls and Vault remain honest coming-soon apps regardless of their icons.

`theme/` installs as `NexiumIOS4`. The existing `branding/icons/supplied/` drop-in hook remains available for a later complete pack. The earlier Mac preview is not sliced or used. 128px exports are not extra detail beyond the source resolution.
