#!/usr/bin/env python3
"""Extract only user-provided artwork; reproducible crops and theme wiring."""
from pathlib import Path
from PIL import Image, ImageDraw
import hashlib, json, runpy

base=Path('branding/icons/ios4')
source=base/'IMG-0875.jpeg'
im=Image.open(source).convert('RGB')
assert im.size==(1131,707), im.size
xs=[2,144,285,427,568,710,851,992]
ys=[0,142,283,425,567]
rows=[
 ['app-store','blank-gray','calculator','calendar','camera','clock','compass','contacts'],
 ['cydia','facetime','camera-video','linen','game-center','ipod','itunes','mail'],
 ['maps','messages','music','nike-ipod','notes','phone','photos','safari'],
 ['settings','stocks','utilities-folder','tools-folder','videos','voice-memos','voice-control','weather-celsius'],
 ['weather-fahrenheit','snow','tv']]
manifest={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_size':im.size,'resampling':'Pillow LANCZOS','icons':{}}
for row,names in enumerate(rows):
    for col,name in enumerate(names):
        box=(xs[col],ys[row],xs[col]+136,ys[row]+136)
        crop=im.crop(box).convert('RGBA')
        # Alpha cleanup follows the existing rounded silhouette; no glyphs drawn.
        mask=Image.new('L',(136*4,136*4),0)
        ImageDraw.Draw(mask).rounded_rectangle((0,0,136*4-1,136*4-1),radius=24*4,fill=255)
        crop.putalpha(mask.resize((136,136),Image.Resampling.LANCZOS))
        hashes={}
        for size,folder in [(136,'original'),(128,'128x128'),(64,'64x64')]:
            dest=base/folder/(name+'.png');dest.parent.mkdir(parents=True,exist_ok=True)
            img=crop if size==136 else crop.resize((size,size),Image.Resampling.LANCZOS)
            img.save(dest)
            with Image.open(dest) as check:
                assert check.size==(size,size) and check.mode=='RGBA',dest
            hashes[folder]=hashlib.sha256(dest.read_bytes()).hexdigest()
        manifest['icons'][name]={'crop_box':box,'sha256':hashes}
(base/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
apps=runpy.run_path('desktop/phase2.py')['APPS']
def choose(key,name,cmd):
    if key=='trash': return 'blank-gray'
    s=(key+' '+name+' '+cmd).lower()
    for terms,icon in [(['browser','chromium','firefox'],'safari'),(['files','pcmanfm','file manager'],'utilities-folder'),(['terminal','xterm'],'linen'),(['messages','sms'],'messages'),(['calls','phone'],'phone'),(['settings','preferences'],'settings'),(['editor','mousepad'],'notes'),(['monitor','lxtask'],'stocks'),(['vault'],'cydia')]:
        if any(t in s for t in terms): return icon
    raise ValueError('No explicit sheet mapping for '+repr((key,name,cmd)))
mapping={k:choose(k,n,c) for k,n,c,i in apps}
(base/'mapping.json').write_text(json.dumps(mapping,indent=2)+'\n')
theme=base/'theme'
for size in [64,128]:
    d=theme/f'{size}x{size}/apps';d.mkdir(parents=True,exist_ok=True)
    for name in manifest['icons']:
        (d/('ios4-'+name+'.png')).write_bytes((base/f'{size}x{size}'/(name+'.png')).read_bytes())
    for alias,name in {'folder':'utilities-folder','user-home':'utilities-folder','user-trash':'blank-gray','user-trash-full':'blank-gray','web-browser':'safari','utilities-terminal':'linen','accessories-text-editor':'notes','preferences-system':'settings','utilities-system-monitor':'stocks','call-start':'phone','sms':'messages'}.items():
        (d/(alias+'.png')).write_bytes((base/f'{size}x{size}'/(name+'.png')).read_bytes())
(theme/'index.theme').write_text('[Icon Theme]\nName=Nexium iOS4\nComment=User-authorized JPEG sheet crops; see provenance README\nInherits=Adwaita,hicolor\nDirectories=64x64/apps,128x128/apps\n\n[64x64/apps]\nSize=64\nContext=Applications\nType=Fixed\n\n[128x128/apps]\nSize=128\nContext=Applications\nType=Fixed\n')
(base/'README.md').write_text('''# User-authorized iOS 4 sheet crops

The source is `IMG-0875.jpeg`, supplied by Avery with explicit permission to crop it. This is not a vector reconstruction or a bespoke icon pack. Upstream artwork ownership is not claimed. JPEG compression remains in the original pixels.

Run `python3 scripts/prepare-ios4.py` after `desktop/phase2.py --materialize` with Pillow installed. `manifest.json` records exact crop boxes and hashes. All 35 cells are cropped to 136x136, with rounded exterior alpha cleanup only, then resampled with LANCZOS to 128x128 and 64x64. No glyphs or new artwork are drawn. PNG dimensions and RGBA modes are checked after saving.

Dock substitutions: Files uses Utilities-folder; Terminal uses the blank linen cell; Trash uses the blank gray cell. These are explicitly substitutes because this sheet contains no actual Files, terminal or Trash glyphs. Browser uses Safari, Calls Phone, Messages SMS, Settings gears, Text Editor Notes, System Monitor Stocks, Vault Cydia. Adwaita/hicolor supply any unmapped system icons. Messages, Calls and Vault remain honest coming-soon apps regardless of their icons.

`theme/` installs as `NexiumIOS4`. The existing `branding/icons/supplied/` drop-in hook remains available for a later complete pack. The earlier Mac preview is not sliced or used. 128px exports are not extra detail beyond the source resolution.
''')
p=Path('desktop/phase2.py');s=p.read_text()
marker='    # Install authorized iOS4 crops with manifest tracking.\n'
if marker not in s:
    needle="    icon_theme='Adwaita'\n"
    assert needle in s
    block="""    # Install authorized iOS4 crops with manifest tracking.
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
"""
    s=s.replace(needle,needle+block,1)
old="    print('Mac icons: reference preview only; Adwaita fallback; pack NOT integrated')"
new="""    icon_theme=(r/'etc/xdg/nexium/icon-theme').read_text().strip()
    print('ICON THEME:',icon_theme)
    if icon_theme=='NexiumIOS4':
        icon_map=json.loads(P('branding/icons/ios4/mapping.json').read_text())
        for k,n,c,i in APPS:
            desktop=r/f'usr/share/applications/nexium-{k}.desktop'
            icon='ios4-'+icon_map[k]
            assert 'Icon='+icon in desktop.read_text(),k
            for size in [64,128]:
                assert (r/f'usr/share/icons/NexiumIOS4/{size}x{size}/apps/{icon}.png').read_bytes().startswith(b'\\x89PNG\\r\\n\\x1a\\n')
            print('ICON',k,'=>',icon,'64px and 128px PNG verified')
        print('iOS4: user-authorized sheet crops integrated; Mac preview not used; unmapped icons inherit Adwaita')
    else: print('ICON THEME fallback or supplied pack:',icon_theme)"""
if old in s:s=s.replace(old,new)
compile(s,str(p),'exec');p.write_text(s)
for k,n,c,i in apps:
    p=Path(f'desktop/dock/applications/nexium-{k}.desktop')
    lines=[('Icon=ios4-'+mapping[k]) if x.startswith('Icon=') else x for x in p.read_text().splitlines()]
    p.write_text('\n'.join(lines)+'\n')
# Materialization regenerates the old reference-only documentation; update it.
Path('branding/icons/README.md').write_text('# Nexium icon inputs\n\nThe user-authorized iOS4 sheet is cropped reproducibly under `ios4/`; see its README, mapping and manifest. The earlier Mac preview is not integrated. `supplied/` and `mapping.json` remain a future complete-theme drop-in hook. No ownership of upstream artwork is claimed.\n')
doc=Path('desktop/README.md')
doc.write_text(doc.read_text()+'\n\n## iOS4 sheet integration\n\nAfter materializing, run `python3 scripts/prepare-ios4.py` (Pillow required). The resulting `NexiumIOS4` theme uses the supplied JPEG crops at 64px/128px. See `branding/icons/ios4/README.md` for provenance and explicit Files/Terminal/Trash substitutes. These current details supersede earlier reference-only icon notes.\n')
contact=Image.new('RGB',(8*160,5*172),(25,25,25));draw=ImageDraw.Draw(contact)
for row,names in enumerate(rows):
    for col,name in enumerate(names):
        icon=Image.open(base/'128x128'/(name+'.png'))
        contact.paste(icon,(col*160+16,row*172+4),icon)
        draw.text((col*160+4,row*172+140),name,fill='white')
Path('reports').mkdir(exist_ok=True)
contact.save('reports/ios4-contact-sheet.png')
Path('reports/ios4-icons.txt').write_text('PASS: 35 user-sheet crops; 105 PNG assets (original 136x136, 128x128, 64x64)\nSOURCE SHA256: '+manifest['source_sha256']+'\nMAPPING: '+json.dumps(mapping,sort_keys=True)+'\nNo bespoke icons drawn; Mac preview not used; Files/Terminal/Trash are documented sheet substitutes.\n')
print(Path('reports/ios4-icons.txt').read_text())
