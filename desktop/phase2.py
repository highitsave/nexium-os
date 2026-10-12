#!/usr/bin/env python3
"""Materialize and install the reproducible Nexium Phase 2 native desktop layer.
No icons are generated. Run --materialize before --install ROOT.
"""
import argparse, configparser, hashlib, json, os, pathlib, shutil, subprocess
P = pathlib.Path
FILES = {}
FILES['desktop/README.md'] = '''# Nexium Phase 2

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
'''
FILES['desktop/packages.txt'] = '''openbox
plank
tint2
pcmanfm
xterm
mousepad
lxtask
lxappearance
obconf
feh
zenity
picom
network-manager-gnome
pavucontrol
adwaita-icon-theme
dbus-x11
libglib2.0-bin
sudo
network-manager
network-manager-gnome
wpasupplicant
iw
rfkill
pciutils
usbutils
wireless-regdb
firmware-linux-nonfree
firmware-realtek
firmware-iwlwifi
firmware-atheros
firmware-brcm80211
firmware-libertas
firmware-misc-nonfree
'''
FILES['desktop/dock/README.md'] = '''# Provisional native dock
Plank, bottom centered, 10 ordered pins, standard Adwaita fallback icons.
Pins map to desktop entries in /usr/share/applications. Running indicators
and native pin/unpin are provided by Plank. The icon mapping in
branding/icons/mapping.json is provisional; do not finalize until the actual
supplied Mac pack arrives. The preview image is not sliced or integrated.
'''
APPS = [
 ('files','Files','/usr/bin/pcmanfm','system-file-manager'),
 ('browser','Browser','/usr/bin/chromium','web-browser'),
 ('terminal','Terminal','/usr/bin/xterm','utilities-terminal'),
 ('messages','Nexium Messages (Coming soon)','/usr/local/bin/nexium-coming-soon Messages','mail-message-new'),
 ('calls','Nexium Calls (Coming soon)','/usr/local/bin/nexium-coming-soon Calls','call-start'),
 ('settings','Settings','/usr/local/bin/nexium-settings','preferences-system'),
 ('vault','NEXIUM VAULT (Coming soon)','/usr/local/bin/nexium-coming-soon Vault','system-software-install'),
 ('editor','Text Editor','/usr/bin/mousepad','accessories-text-editor'),
 ('monitor','System Monitor','/usr/bin/lxtask','utilities-system-monitor'),
 ('trash','Trash','/usr/bin/pcmanfm trash:///','user-trash')]
for i,(key,name,cmd,icon) in enumerate(APPS,1):
    FILES[f'desktop/dock/applications/nexium-{key}.desktop'] = f'''[Desktop Entry]
Type=Application
Name={name}
Exec={cmd}
Icon={icon}
Terminal=false
Categories=Utility;
StartupNotify=true
'''
    FILES[f'desktop/dock/launchers/{i:02d}-{key}.dockitem'] = f'''[PlankDockItemPreferences]
Launcher=file:///usr/share/applications/nexium-{key}.desktop
'''
FILES['branding/icons/mapping.json'] = json.dumps({k:v for k,n,c,v in APPS},indent=2)+'\n'
FILES['branding/icons/README.md'] = '''# Supplied Mac icon pack hook — pending files

The intended source is Avery's supplied Mac icon pack, replacing the earlier
iOS 4 note. Only IMG-0874.jpeg, a preview/reference sheet, has been supplied.
It is not integrated, sliced or redrawn. No bespoke icons are generated.
Actual individual pack files and their usage rights remain needed.

Put the actual pack as a freedesktop theme in `branding/icons/supplied/`, with
`index.theme`, scalable/ or resolution directories (e.g. 48x48/apps/), and
Inherits=Adwaita. Or adapt mapping.json to map each provisional dock identity
to an existing icon name in that supplied theme. Do not stretch artwork.
The install hook copies that theme into /usr/share/icons/NexiumSupplied and
selects NexiumSupplied only when index.theme and valid mapped icons exist.
Otherwise Adwaita remains selected. Missing requested icons must fall back
to standard named icons, never generated substitute artwork. Re-run the
workflow after files arrive; review the dock arrangement with Avery then.
The current layout is a provisional implementation of the requested ten
entries, not a finalized supplied-icon design.
'''
FILES['desktop/panel/tint2rc'] = '''# Top launcher, task list, tray, battery and clock
panel_items = LTSCB
panel_position = top center horizontal
panel_size = 100% 30
panel_margin = 0 0
panel_padding = 6 2 6
panel_background_id = 1
panel_layer = top
strut_policy = follow_size
rounded = 8
border_width = 1
background_color = #fff8e7 95
border_color = #d7b973 80
launcher_padding = 4 2 4
launcher_icon_size = 22
launcher_item_app = /usr/share/applications/nexium-applications.desktop
launcher_item_app = /usr/share/applications/nexium-info.desktop
launcher_icon_theme = Adwaita
taskbar_mode = single_desktop
taskbar_padding = 2 0 2
task_icon = 1
task_text = 1
task_maximum_size = 180 26
task_font = Sans 10
task_font_color = #4c3b22 100
task_active_font_color = #34240f 100
systray_padding = 3 0 3
systray_icon_size = 20
time1_format = %a %d %b  %H:%M
time1_font = Sans 10
clock_font_color = #4c3b22 100
clock_padding = 6 0
battery_font = Sans 10
battery_font_color = #4c3b22 100
battery_padding = 3 0
battery_hide = 100
'''
FILES['desktop/panel/README.md'] = '''# Tint2 top panel
Launcher (native Openbox menu), System Information, running tasks, XEmbed
tray, local clock and battery when supported. NetworkManager applet is
started separately. Modern StatusNotifier-only apps may not appear in the
legacy tray. Hardware tray entries are conditional, not simulated.
'''
FILES['desktop/themes/GoldenGate/gtk-3.0/gtk.css'] = '''@import url("resource:///org/gtk/libgtk/theme/Adwaita/gtk-contained.css");
@define-color theme_bg_color #fff8e7;
@define-color theme_fg_color #463a2c;
@define-color theme_base_color #fffdf5;
@define-color theme_selected_bg_color #d4b46a;
@define-color theme_selected_fg_color #302515;
window, dialog, .background { background-color: #fff8e7; color: #463a2c; }
headerbar, .titlebar { background-image: linear-gradient(to bottom, #fff7dd, #ecd8a6); border-radius: 12px 12px 0 0; }
button { border-radius: 8px; }
entry, textview, list { background-color: #fffdf5; color: #463a2c; border-radius: 7px; }
selection, *:selected { background-color: #d4b46a; color: #302515; }
decoration { border-radius: 12px 12px 0 0; }
'''
FILES['desktop/themes/GoldenGate/gtk-2.0/gtkrc'] = '''include "/usr/share/themes/Adwaita/gtk-2.0/gtkrc"
style "nexium-gold" {
  bg[NORMAL] = "#fff8e7"
  fg[NORMAL] = "#463a2c"
  base[NORMAL] = "#fffdf5"
  bg[SELECTED] = "#d4b46a"
  fg[SELECTED] = "#302515"
}
class "*" style "nexium-gold"
'''
FILES['desktop/themes/GoldenGate/openbox-3/themerc'] = '''window.active.title.bg: gradient vertical
window.active.title.bg.color: #fff7dd
window.active.title.bg.colorTo: #ecd8a6
window.inactive.title.bg: flat solid
window.inactive.title.bg.color: #f2ebdc
window.active.label.bg: parentrelative
window.inactive.label.bg: parentrelative
window.active.label.text.color: #463a2c
window.inactive.label.text.color: #8e806b
window.active.button.unpressed.bg: parentrelative
window.active.button.unpressed.image.color: #725a2e
window.inactive.button.unpressed.bg: parentrelative
window.inactive.button.unpressed.image.color: #9d8e73
window.active.handle.bg: flat solid
window.active.handle.bg.color: #ecd8a6
window.inactive.handle.bg: flat solid
window.inactive.handle.bg.color: #f2ebdc
window.active.grip.bg: parentrelative
window.inactive.grip.bg: parentrelative
border.width: 1
window.active.border.color: #d4b46a
window.inactive.border.color: #d8cdb7
window.handle.width: 3
padding.width: 8
padding.height: 6
menu.items.bg: flat solid
menu.items.bg.color: #fff8e7
menu.items.text.color: #463a2c
menu.items.active.bg: flat solid
menu.items.active.bg.color: #d4b46a
menu.items.active.text.color: #302515
menu.title.bg: flat solid
menu.title.bg.color: #ecd8a6
menu.title.text.color: #463a2c
'''
FILES['desktop/themes/picom.conf'] = '''backend = "xrender";
vsync = false;
shadow = true;
shadow-radius = 10;
shadow-opacity = 0.18;
fading = false;
corner-radius = 12;
rounded-corners-exclude = [ "window_type = 'dock'", "window_type = 'desktop'" ];
'''
FILES['desktop/themes/README.md'] = '''# Golden Gate light theme
Pale gold and cream, GTK 2/3 and Openbox decorations. Picom XRender rounds
corners where compositing is supported; GTK3 client-side decoration is also
rounded. No promised rounding when compositor/driver support is unavailable.
Existing GTK4 applications can keep their platform styling.
'''
FILES['desktop/session/rc.xml'] = '''<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
 <theme><name>GoldenGate</name><titleLayout>NLIMC</titleLayout><keepBorder>yes</keepBorder><font place="ActiveWindow"><name>Sans</name><size>10</size><weight>Bold</weight></font></theme>
 <desktops><number>2</number><firstdesk>1</firstdesk></desktops>
 <focus><focusNew>yes</focusNew><followMouse>no</followMouse></focus>
 <placement><policy>Smart</policy><center>yes</center></placement>
 <keyboard>
  <keybind key="A-Tab"><action name="NextWindow"/></keybind>
  <keybind key="A-S-Tab"><action name="PreviousWindow"/></keybind>
  <keybind key="A-F4"><action name="Close"/></keybind>
  <keybind key="W-e"><action name="Execute"><command>pcmanfm</command></action></keybind>
  <keybind key="W-t"><action name="Execute"><command>xterm</command></action></keybind>
  <keybind key="W-s"><action name="Execute"><command>nexium-settings</command></action></keybind>
  <keybind key="W-space"><action name="ShowMenu"><menu>root-menu</menu></action></keybind>
  <keybind key="A-F10"><action name="ToggleMaximize"/></keybind>
 </keyboard>
 <mouse>
  <context name="Titlebar"><mousebind button="Left" action="Drag"><action name="Move"/></mousebind><mousebind button="Left" action="DoubleClick"><action name="ToggleMaximize"/></mousebind><mousebind button="Right" action="Press"><action name="ShowMenu"><menu>client-menu</menu></action></mousebind></context>
  <context name="Frame"><mousebind button="A-Left" action="Drag"><action name="Move"/></mousebind><mousebind button="A-Right" action="Drag"><action name="Resize"/></mousebind></context>
  <context name="Desktop"><mousebind button="Right" action="Press"><action name="ShowMenu"><menu>root-menu</menu></action></mousebind></context>
  <context name="Close"><mousebind button="Left" action="Click"><action name="Close"/></mousebind></context>
  <context name="Iconify"><mousebind button="Left" action="Click"><action name="Iconify"/></mousebind></context>
  <context name="Maximize"><mousebind button="Left" action="Click"><action name="ToggleMaximize"/></mousebind></context>
 </mouse>
 <menu><file>menu.xml</file><hideDelay>200</hideDelay></menu>
 <applications><application class="Plank"><decor>no</decor><skip_taskbar>yes</skip_taskbar></application></applications>
</openbox_config>
'''
from xml.sax.saxutils import escape
FILES['desktop/session/menu.xml'] = '<?xml version="1.0"?><openbox_menu xmlns="http://openbox.org/3.4/menu"><menu id="root-menu" label="Nexium OS">' + ''.join(f'<item label="{escape(n)}"><action name="Execute"><command>{escape(c)}</command></action></item>' for k,n,c,ic in APPS) + '''<separator/><item label="Welcome"><action name="Execute"><command>nexium-welcome --force</command></action></item><item label="System Information"><action name="Execute"><command>nexium-info</command></action></item><separator/><item label="Log out"><action name="Exit"/></item></menu></openbox_menu>\n'''
FILES['desktop/session/session'] = '''#!/bin/sh
# Native session under Xinit as the existing unprivileged nexium user.
export XDG_SESSION_TYPE=x11
export XDG_CURRENT_DESKTOP=Openbox XDG_SESSION_DESKTOP=Openbox DESKTOP_SESSION=openbox
export XCURSOR_THEME=Adwaita XCURSOR_SIZE=24
xset s off -dpms s noblank 2>/dev/null || true
exec dbus-run-session -- openbox-session
'''
FILES['desktop/session/autostart'] = '''#!/bin/sh
feh --no-fehbg --bg-fill /usr/share/backgrounds/nexium/golden-gate.png &
picom --config /etc/xdg/nexium/picom.conf &
tint2 -c /etc/xdg/nexium/tint2rc &
nm-applet &
gsettings set org.gnome.desktop.interface gtk-theme GoldenGate 2>/dev/null || true
gsettings set org.gnome.desktop.interface icon-theme "$(cat /etc/xdg/nexium/icon-theme)" 2>/dev/null || true
schema=net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/
gsettings set "$schema" position bottom 2>/dev/null || true
gsettings set "$schema" alignment center 2>/dev/null || true
gsettings set "$schema" icon-size 48 2>/dev/null || true
gsettings set "$schema" hide-mode intelligent 2>/dev/null || true
plank &
nexium-welcome &
'''
FILES['desktop/session/nexium-kiosk.service'] = '''[Unit]
Description=Nexium OS native desktop (Openbox, Plank, Tint2)
After=systemd-user-sessions.service NetworkManager.service plymouth-start.service
Conflicts=getty@tty1.service
[Service]
User=nexium
PAMName=login
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
StandardInput=tty
StandardOutput=journal
UtmpIdentifier=tty1
UtmpMode=user
ExecStartPre=+-/bin/plymouth quit --retain-splash
ExecStart=/usr/bin/xinit /usr/local/lib/nexium/session -- :0 vt1 -nolisten tcp -keeptty -background none
Restart=always
RestartSec=1
[Install]
WantedBy=graphical.target
'''
FILES['desktop/session/settings.ini'] = '''[Settings]
gtk-theme-name=GoldenGate
gtk-icon-theme-name=Adwaita
gtk-font-name=Sans 10
gtk-application-prefer-dark-theme=0
'''
FILES['desktop/apps/nexium-coming-soon'] = '''#!/bin/sh
case "$1" in
 Messages) text="Nexium Messages — coming soon. No messaging backend or persistent conversation client is implemented in Phase 2. Nothing is sent.";;
 Calls) text="Nexium Calls — coming soon. Signaling, accounts and audio calling are not implemented. No call is placed.";;
 Vault) text="NEXIUM VAULT — coming soon. The application center is not implemented. No packages are installed by this placeholder.";;
 *) exit 2;;
esac
exec zenity --info --title="Nexium OS — $1" --width=480 --text="$text"
'''
FILES['desktop/apps/nexium-welcome'] = '''#!/bin/sh
state="${XDG_STATE_HOME:-$HOME/.local/state}/nexium"
[ "$1" = --force ] || [ ! -f "$state/welcome-seen" ] || exit 0
if zenity --info --title="Welcome to Nexium OS" --width=540 --text="Welcome to Nexium OS — Golden Gate desktop.\n\nYour bottom dock opens native applications. Right-click the desktop or press Super+Space for the launcher. Super+E opens Files; Super+T opens Terminal; Alt+Tab switches windows.\n\nMessages, Calls and NEXIUM VAULT are coming soon, not functioning communication or package clients. Mac icons are pending actual pack files; standard fallbacks are in use.\n\nThis is a live system: without persistence, changes in HOME disappear after reboot. The session does not automatically install to or change your internal disks. Native terminal administration still requires care.\n\nUse System Information in the top panel for actual system details."; then
 mkdir -p "$state"; touch "$state/welcome-seen"
fi
'''
FILES['desktop/apps/nexium-info'] = '''#!/bin/sh
file=$(mktemp)
trap 'rm -f "$file"' EXIT HUP INT TERM
{
 echo 'Nexium OS — System Information'
 echo 'Phase 2: Golden Gate native desktop'
 echo 'Openbox window manager; Plank dock; Tint2 panel'
 echo 'Standard fallback icons; supplied Mac pack files pending'
 echo
 cat /etc/os-release
 echo; uname -a
 echo; free -h
 echo; df -h /
 echo; dpkg-query -W openbox plank tint2 pcmanfm xterm mousepad lxtask plymouth chromium 2>/dev/null || true
 echo
 echo 'Live mode: without persistence, HOME and package changes vanish on reboot.'
 echo 'Messages / Calls / Vault are coming-soon placeholders, not implemented.'
} > "$file"
zenity --text-info --title="Nexium OS — System Information" --filename="$file" --width=650 --height=520
'''
FILES['desktop/apps/nexium-settings'] = '''#!/bin/sh
choice=$(zenity --list --title="Nexium OS — Settings" --column=Setting --height=310 --width=360 Appearance Windows Network Audio 'System Information') || exit 0
case "$choice" in
 Appearance) exec lxappearance;;
 Windows) exec obconf;;
 Network) exec nm-connection-editor;;
 Audio) exec pavucontrol;;
 'System Information') exec nexium-info;;
esac
'''
FILES['desktop/apps/nexium-applications'] = '''#!/bin/sh
exec openbox --show-menu root-menu
'''
for key,name,exec_,icon in [('welcome','Welcome to Nexium OS','nexium-welcome --force','dialog-information'),('info','Nexium OS — System Information','nexium-info','computer'),('applications','Applications','nexium-applications','start-here')]:
    FILES[f'desktop/apps/nexium-{key}.desktop']=f'[Desktop Entry]\nType=Application\nName={name}\nExec=/usr/local/bin/{exec_}\nIcon={icon}\nTerminal=false\nCategories=Utility;\n'
FILES['branding/wallpaper/golden-gate.svg'] = '''<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
<defs><linearGradient id="sky" x2="0" y2="1"><stop stop-color="#fff6dc"/><stop offset="1" stop-color="#ddb569"/></linearGradient><linearGradient id="water" x2="0" y2="1"><stop stop-color="#99b7bc"/><stop offset="1" stop-color="#425e70"/></linearGradient></defs>
<rect width="1920" height="1080" fill="url(#sky)"/><circle cx="1370" cy="290" r="120" fill="#fff9df" opacity=".8"/>
<path d="M0 540 Q250 270 600 540 Q850 410 1100 560 L1920 590 L1920 790 L0 790Z" fill="#bda778"/>
<path d="M1100 600 Q1500 350 1920 510 L1920 820 L1050 820Z" fill="#998c72"/>
<rect y="660" width="1920" height="420" fill="url(#water)"/>
<path d="M0 734 Q850 684 1920 717 M0 850 Q990 790 1920 837 M0 970 Q900 925 1920 952" fill="none" stroke="#e9dcc0" stroke-width="4" opacity=".3"/>
<g fill="none" stroke="#ae633e"><path d="M0 658 L1920 658" stroke-width="24"/><path d="M620 682 V338 M665 682 V338 M1320 682 V338 M1365 682 V338" stroke-width="18"/><path d="M610 360 H675 M610 416 H675 M1310 360 H1375 M1310 416 H1375" stroke-width="16"/>
<path d="M0 618 Q315 630 640 350 Q990 760 1340 350 Q1640 630 1920 618" stroke-width="7"/>
<path d="M100 633 V658 M200 630 V658 M300 602 V658 M400 553 V658 M500 484 V658 M740 457 V658 M840 536 V658 M940 593 V658 M1040 609 V658 M1140 567 V658 M1240 473 V658 M1440 489 V658 M1540 553 V658 M1640 592 V658 M1740 618 V658 M1840 629 V658" stroke-width="3"/></g>
<text x="110" y="970" font-family="sans-serif" font-size="52" fill="#fff7df" letter-spacing="8">NEXIUM OS</text><text x="112" y="1010" font-family="sans-serif" font-size="20" fill="#e9dcc0" letter-spacing="5">GOLDEN GATE</text></svg>
'''
FILES['branding/wallpaper/README.md'] = '''# Golden Gate wallpaper
Original SVG geometric bridge landscape (not an icon or supplied Apple art).
Rasterized reproducibly with rsvg-convert to golden-gate.png, installed at
/usr/share/backgrounds/nexium/golden-gate.png and selected by session feh.
SVG and PNG are committed; neither claims to be an official macOS wallpaper.
'''
FILES['branding/boot/README.md'] = '''# Golden Gate cream boot branding
User-authorized active Plymouth theme: nexium-gold.
Cream/pale-gold background and exact attribution: made by TOMO!
Attribution PNG is reproducibly rendered from this committed generator.
The selected config and all theme assets are embedded by update-initramfs.
This pass intentionally regenerates /live/initrd.img; unchanged-initrd
verification is replaced with source/config/theme verification in initrd.
Kernel, grub.cfg, GRUB2 isohybrid boot structure and NEXIUM_OS stay preserved.
'''
FILES['branding/boot/plymouthd.conf'] = '''[Daemon]
Theme=nexium-gold
ShowDelay=0
DeviceTimeout=8
'''
FILES['branding/boot/nexium-gold.plymouth'] = '''[Plymouth Theme]
Name=Nexium OS Golden Gate Cream
Description=Cream and pale-gold boot splash: made by TOMO!
ModuleName=script
[script]
ImageDir=/usr/share/plymouth/themes/nexium-gold
ScriptFile=/usr/share/plymouth/themes/nexium-gold/nexium-gold.script
'''
FILES['branding/boot/nexium-gold.script'] = '''Window.SetBackgroundTopColor(0.9804, 0.9569, 0.8784);
Window.SetBackgroundBottomColor(0.9412, 0.8863, 0.7373);
attribution = Image("attribution.png");
attribution_sprite = Sprite(attribution);
attribution_sprite.SetX((Window.GetWidth() - attribution.GetWidth()) / 2);
attribution_sprite.SetY((Window.GetHeight() - attribution.GetHeight()) / 2);
attribution_sprite.SetZ(100);
'''

def render_cream_attribution():
    from PIL import Image, ImageDraw, ImageFont
    image=Image.new('RGBA',(640,180),(0,0,0,0))
    draw=ImageDraw.Draw(image)
    regular=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',26)
    bold=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',44)
    draw.text((320,35),'Nexium OS',font=regular,fill=(126,92,51,255),anchor='mm')
    draw.text((320,98),'made by TOMO!',font=bold,fill=(93,61,31,255),anchor='mm')
    draw.line((190,148,450,148),fill=(196,153,83,255),width=3)
    image.save('branding/boot/attribution.png')

def materialize():
    for name,text in FILES.items():
        p=P(name);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    subprocess.run(['rsvg-convert','-o','branding/wallpaper/golden-gate.png','branding/wallpaper/golden-gate.svg'],check=True)
    render_cream_attribution()
    # Reuse, do not reinvent, the exact verifier from repair-tab-boot.yml.
    import yaml
    workflow=yaml.safe_load(P('.github/workflows/repair-tab-boot.yml').read_text())
    runs=[s.get('run','') for j in workflow['jobs'].values() for s in j['steps']]
    source=next(s for s in runs if 'def schema(text):' in s)
    script=source.split("<<'PY'",1)[1].split('\nPY',1)[0].lstrip('\n')
    # The repair verifier may have shell text around multiple heredocs; locate
    # the actual block containing schema, preserving all of its boot checks.
    blocks=source.split("<<'PY'")[1:]
    script=next(b.split('\nPY',1)[0].lstrip('\n') for b in blocks if 'def schema(text):' in b)
    # Strip the shell pipeline from the copied heredoc header.
    script = script.split('\n', 1)[1] if script.lstrip().startswith('|') else script
    # Retain everything through the boot verification; follow with Phase 2
    # content checks instead of the repair-only unchanged-squashfs checks.
    end=script.index("print('VALID ISO9660:")
    end=script.index('\n',end)
    # INITRD_CREAM_VERIFICATION replaces obsolete unchanged-initrd checks only.
    script=script[:end]
    assert "name.suffix=='.squashfs'" in script
    script=script.replace("name.suffix=='.squashfs'", "name==P('live/initrd.img') or name.suffix=='.squashfs'",1)
    script=script.replace("['live/vmlinuz','live/initrd.img','boot/grub/grub.cfg']", "['live/vmlinuz','boot/grub/grub.cfg']",1)
    P('scripts/verify-phase2-boot.py').write_text(script+'\n'+"\n# INITRD_CREAM_VERIFICATION: user-authorized regenerated initrd.\nimport shutil\ntarget=P('work/final-initrd')\nif target.exists(): shutil.rmtree(target)\nsubprocess.run(['unmkinitramfs',str(b/'live/initrd.img'),str(target)],check=True)\ndef unpacked(path):\n    matches=[p for p in target.rglob(P(path).name) if p.is_file() and str(p).endswith(path)]\n    assert len(matches)==1, (path,matches)\n    return matches[0]\nconfig=unpacked('etc/plymouth/plymouthd.conf')\nassert 'Theme=nexium-gold' in config.read_text()\nassert config.read_bytes()==P('branding/boot/plymouthd.conf').read_bytes()\nfor name in ['nexium-gold.plymouth','nexium-gold.script','attribution.png']:\n    packed=unpacked('usr/share/plymouth/themes/nexium-gold/'+name)\n    assert packed.read_bytes()==P('branding/boot',name).read_bytes(),name\n    print('INITRD SOURCE SHA256 MATCH:',name,hashlib.sha256(packed.read_bytes()).hexdigest())\nassert originals[P('live/initrd.img')].read_bytes()!=rebuilt[P('live/initrd.img')].read_bytes()\nprint('PASS REGENERATED INITRD: selected Theme=nexium-gold; cream script and made by TOMO! attribution PNG match committed branding source')\nprint('INITRD SHA256:',hashlib.sha256((b/'live/initrd.img').read_bytes()).hexdigest())\n")
    print('Materialized',len(FILES),'source files and wallpaper PNG; reused repair boot verifier')

def install(root):
    # QUEUED_LIVE_FIXES: source hooks before ownership and overlay manifest.
    subprocess.run(['python3','scripts/chromium-localhost.py','fix',str(root)],check=True)
    subprocess.run(['python3','scripts/live-admin-network.py','install',str(root)],check=True)
    r=P(root).resolve();manifest={}
    def put(source,dest,executable=False):
        p=r/dest.lstrip('/');p.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,p);p.chmod(0o755 if executable else 0o644)
        manifest['/'+dest.lstrip('/')]=hashlib.sha256(p.read_bytes()).hexdigest()
    for p in P('desktop/dock/applications').glob('*.desktop'):put(p,'usr/share/applications/'+p.name)
    for p in P('desktop/apps').iterdir():put(p,('usr/share/applications/' if p.suffix=='.desktop' else 'usr/local/bin/')+p.name,p.suffix!='.desktop')
    for p in P('desktop/themes/GoldenGate').rglob('*'):
        if p.is_file():put(p,'usr/share/themes/GoldenGate/'+str(p.relative_to('desktop/themes/GoldenGate')))
    put('desktop/themes/picom.conf','etc/xdg/nexium/picom.conf')
    put('desktop/panel/tint2rc','etc/xdg/nexium/tint2rc')
    put('desktop/session/session','usr/local/lib/nexium/session',True)
    put('desktop/session/nexium-kiosk.service','etc/systemd/system/nexium-kiosk.service')
    put('branding/wallpaper/golden-gate.png','usr/share/backgrounds/nexium/golden-gate.png')
    for p in P('branding/boot').glob('nexium-gold.*'):put(p,'usr/share/plymouth/themes/nexium-gold/'+p.name)
    put('branding/wallpaper/golden-gate.png','usr/share/plymouth/themes/nexium-gold/golden-gate.png')
    put('branding/boot/attribution.png','usr/share/plymouth/themes/nexium-gold/attribution.png')
    put('branding/boot/plymouthd.conf','etc/plymouth/plymouthd.conf')
    icon_theme='Adwaita'
    # Install authorized iOS4 crops with manifest tracking.
    ios4=P('branding/icons/ios4/theme')
    if (ios4/'index.theme').exists():
        for p in ios4.rglob('*'):
            if p.is_file():put(p,'usr/share/icons/NexiumIOS4/'+str(p.relative_to(ios4)))
        icon_theme='NexiumIOS4'
        icon_map=json.loads(P('branding/icons/ios4/mapping.json').read_text())
        for k,n,c,i in APPS:
            p=r/f'usr/share/applications/nexium-{k}.desktop'
            text=p.read_text().replace('Icon='+i,'Icon=ios4-'+icon_map[k]);p.write_text(text)
            manifest['/'+str(p.relative_to(r))]=hashlib.sha256(p.read_bytes()).hexdigest()
    supplied=P('branding/icons/supplied')
    if (supplied/'index.theme').exists():
        mapping=json.loads(P('branding/icons/mapping.json').read_text())
        assert all(any(supplied.rglob(v+'.*')) for v in mapping.values()), 'Supplied theme lacks mapped icons; keep fallback or fix mapping explicitly'
        shutil.copytree(supplied,r/'usr/share/icons/NexiumSupplied',dirs_exist_ok=True)
        icon_theme='NexiumSupplied'
        for k,n,c,i in APPS:
            p=r/f'usr/share/applications/nexium-{k}.desktop'
            text=p.read_text().replace('Icon='+i,'Icon='+mapping[k]);p.write_text(text)
            manifest['/'+str(p.relative_to(r))]=hashlib.sha256(p.read_bytes()).hexdigest()
    (r/'etc/xdg/nexium/icon-theme').write_text(icon_theme+'\n')
    for base in ['etc/skel','home/nexium']:
        for src,dest in [('rc.xml','.config/openbox/rc.xml'),('menu.xml','.config/openbox/menu.xml'),('autostart','.config/openbox/autostart'),('settings.ini','.config/gtk-3.0/settings.ini')]:
            put('desktop/session/'+src,base+'/'+dest,src=='autostart')
        for p in P('desktop/dock/launchers').glob('*.dockitem'):put(p,base+'/.config/plank/dock1/launchers/'+p.name)
        p=r/base/'.config/gtk-3.0/settings.ini';p.write_text(p.read_text().replace('Adwaita',icon_theme));manifest['/'+str(p.relative_to(r))]=hashlib.sha256(p.read_bytes()).hexdigest()
        p=r/base/'.gtkrc-2.0';p.write_text(f'gtk-theme-name="GoldenGate"\ngtk-icon-theme-name="{icon_theme}"\n')
    # Existing live account UID/GID, not an invented user or a root desktop.
    account=next(line.split(':') for line in (r/'etc/passwd').read_text().splitlines() if line.startswith('nexium:'))
    for p in (r/'home/nexium').rglob('*'):
        if not p.is_symlink():os.chown(p,int(account[2]),int(account[3]))
    for p in (r/'etc/systemd/system').rglob('nexium-launcher.service'):
        if p.is_symlink():p.unlink()
    release=r/'etc/os-release'
    text=release.read_text();lines=text.splitlines()
    lines=[x for x in lines if not x.startswith(('NAME=','PRETTY_NAME='))]
    lines.extend(['NAME="Nexium OS"','PRETTY_NAME="Nexium OS (Golden Gate Phase 2)"'])
    release.write_text('\n'.join(lines)+'\n')
    (r/'etc/issue').write_text('Nexium OS — Golden Gate Phase 2\\n\\l\n')
    P('reports/phase2-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Installed native layer:',len(manifest),'SHA256-tracked files; icon theme:',icon_theme)

def output_executable(root, target):
    subprocess.run(['chroot',str(root),'/usr/bin/test','-f',target],check=True)
    subprocess.run(['chroot',str(root),'/usr/bin/test','-x',target],check=True)

def verify_ungoogled(root):
    r=P(root)
    entry=r/'usr/bin/chromium'
    print('CHROMIUM ENTRY:', 'symlink -> '+os.readlink(entry) if entry.is_symlink() else 'regular file/wrapper')
    resolved=subprocess.check_output(['chroot',str(r),'/usr/bin/readlink','-f','/usr/bin/chromium'],text=True).strip()
    print('CHROMIUM RESOLVES TO:',resolved)
    binary='/opt/ungoogled-chromium/chrome'
    output_executable(r,binary)
    assert (r/binary.lstrip('/')).read_bytes()[:4]==b'\x7fELF','Ungoogled payload is not ELF'
    if resolved!=binary:
        wrapper=(r/resolved.lstrip('/')).read_text()
        print('CHROMIUM WRAPPER:',wrapper.strip())
        assert wrapper.startswith('#!') and binary in wrapper,'Wrapper does not invoke ungoogled binary'
    output_executable(r,'/usr/bin/chromium')
    version=subprocess.check_output(['chroot',str(r),'/usr/bin/chromium','--version'],text=True).strip()
    assert 'Chromium' in version,version
    print('UNGOOGLED BINARY:',binary,'exists, executable, ELF; browser --version:',version)

def verify(root):
    subprocess.run(['python3','scripts/chromium-localhost.py','verify',str(root)],check=True)
    subprocess.run(['python3','scripts/live-admin-network.py','verify',str(root)],check=True)
    verify_ungoogled(root)
    r=P(root);manifest=json.loads(P('reports/phase2-manifest.json').read_text())
    for name,digest in manifest.items():assert hashlib.sha256((r/name.lstrip('/')).read_bytes()).hexdigest()==digest,name
    print('OUTPUT SQUASHFS: all',len(manifest),'desktop/branding overlay files present and SHA256-identical')
    for k,n,c,i in APPS:
        target=c.split()[0];output_executable(r,target)
        if k in ['settings','messages','calls','vault']:assert (r/'usr/bin/zenity').exists()
        print('DOCK',k,'=>',c, '(honest coming-soon placeholder)' if k in ['messages','calls','vault'] else '(real application)')
    pins=list((r/'home/nexium/.config/plank/dock1/launchers').glob('*.dockitem'))
    assert len(pins)==10, f'Expected 10 pins, got {len(pins)}'
    assert 'Nexium OS' in (r/'etc/os-release').read_text()
    assert 'User=nexium' in (r/'etc/systemd/system/nexium-kiosk.service').read_text()
    assert (r/'usr/share/backgrounds/nexium/golden-gate.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    print('Output desktop: Openbox / Plank / Tint2 / PCManFM / Xterm; Plymouth retained')
    icon_theme=(r/'etc/xdg/nexium/icon-theme').read_text().strip()
    print('ICON THEME:',icon_theme)
    if icon_theme=='NexiumIOS4':
        icon_map=json.loads(P('branding/icons/ios4/mapping.json').read_text())
        for k,n,c,i in APPS:
            desktop=r/f'usr/share/applications/nexium-{k}.desktop'
            icon='ios4-'+icon_map[k]
            assert 'Icon='+icon in desktop.read_text(),k
            for size in [64,128]:
                assert (r/f'usr/share/icons/NexiumIOS4/{size}x{size}/apps/{icon}.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
            print('ICON',k,'=>',icon,'64px and 128px PNG verified')
        print('iOS4: user-authorized sheet crops integrated; Mac preview not used; unmapped icons inherit Adwaita')
    else: print('ICON THEME fallback or supplied pack:',icon_theme)
    print('Boot theme: active nexium-gold cream made by TOMO!; regenerated initrd verified separately')
    print('No physical boot/hardware test performed; launcher resolution is not full hardware verification')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--materialize',action='store_true');a.add_argument('--install');a.add_argument('--verify');o=a.parse_args()
    if o.materialize:materialize()
    if o.install:install(o.install)
    if o.verify:verify(o.verify)
