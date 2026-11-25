#!/usr/bin/env bash
# Generate the original XAC Golden Gate icon set from local SVG primitives.
set -euo pipefail
here="$(cd -- "$(dirname -- "$0")" && pwd)"
apps="$here/scalable/apps"
mkdir -p "$apps"
while IFS='|' read -r name glyph hue; do
  [[ -n "$name" ]] || continue
  cat > "$apps/$name.svg" <<SVG
<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
 <defs>
  <linearGradient id="body" x2="0" y2="1"><stop stop-color="$hue"/><stop offset="1" stop-color="#FBF6E9"/></linearGradient>
  <linearGradient id="shine" x2="0" y2="1"><stop stop-color="#fff" stop-opacity=".82"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="5" stdDeviation="5" flood-color="#493422" flood-opacity=".24"/></filter>
 </defs>
 <rect x="10" y="8" width="108" height="112" rx="29" fill="url(#body)" stroke="#E8C87A" stroke-width="3" filter="url(#shadow)"/>
 <path d="M14 37 Q14 13 39 13 H89 Q114 13 114 38 Q79 29 14 43Z" fill="url(#shine)"/>
 <circle cx="64" cy="67" r="34" fill="#fff" fill-opacity=".52" stroke="#D8B86E" stroke-width="2"/>
 <text x="64" y="81" text-anchor="middle" font-family="sans-serif" font-size="42" font-weight="700" fill="#563E2A">$glyph</text>
 <path d="M30 103 Q64 115 98 103" fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="3" stroke-linecap="round"/>
</svg>
SVG
done <<'ICONS'
files|F|#E8C87A
terminal|_|#CFAF6C
browser|B|#E2C27A
settings|S|#D5B46D
photos|P|#EBD59A
music|M|#DDBA69
video|V|#DAB66B
mail|@|#E8C87A
calendar|31|#D4B56F
app-store|A|#E6C879
trash|T|#C6AA70
folder|D|#E8C87A
ICONS
cat > "$here/index.theme" <<'THEME'
[Icon Theme]
Name=XAC-icons
Comment=Original cream and gold XAC Golden Gate icons
Inherits=hicolor
Directories=scalable/apps

[scalable/apps]
Size=128
Type=Scalable
MinSize=16
MaxSize=512
THEME
chmod 0644 "$here/index.theme" "$apps"/*.svg
