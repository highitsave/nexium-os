import json,hashlib,os,shutil
from pathlib import Path
def installed(r,p):return (r/p).exists()
def install(root):
    r=Path(root);uid,gid=next((int(x.split(':')[2]),int(x.split(':')[3])) for x in (r/'etc/passwd').read_text().splitlines() if x.startswith('nexium:'));paths=[]
    target=r/'usr/local/lib/nexium/nexium_launchers.py';target.write_bytes(Path('browser/nexium_launchers.py').read_bytes());paths.append(target)
    choices=[('chooser','Browser chooser','/usr/local/bin/nexium-browser --chooser','nexium-browser')]
    if installed(r,'usr/bin/firefox-esr'):choices.append(('firefox-choice','Firefox','/usr/bin/firefox-esr','firefox-esr'))
    if installed(r,'usr/bin/brave-browser'):choices.append(('brave-choice','Brave','/usr/bin/brave-browser','brave-browser'))
    for key in ['chooser','firefox-choice','brave-choice']:
        (r/f'usr/share/applications/nexium-{key}.desktop').unlink(missing_ok=True)
        for base in ['etc/skel','home/nexium']:
            (r/base/f'.config/plank/dock1/launchers/11-{key}.dockitem').unlink(missing_ok=True)
    for key,title,cmd,icon in choices:
        p=r/f'usr/share/applications/nexium-{key}.desktop';p.write_text(f'[Desktop Entry]\nType=Application\nName={title}\nExec={cmd}\nIcon={icon}\nTerminal=false\nCategories=Network;WebBrowser;\n');paths.append(p)
        for base in ['etc/skel','home/nexium']:
            q=r/base/f'.config/plank/dock1/launchers/11-{key}.dockitem';q.parent.mkdir(parents=True,exist_ok=True);q.write_text(f'[PlankDockItemPreferences]\nLauncher=file:///usr/share/applications/nexium-{key}.desktop\n');paths.append(q)
            if base=='home/nexium':os.chown(q,uid,gid)
    # Never seed a fake user site or Google engine into the shipped image.
    for base in ['etc/skel','home/nexium']:
        p=r/base/'.config/nexium-browser/launchers.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{"version":1,"search_engine":"DuckDuckGo","sites":[]}\n');p.chmod(0o600);paths.append(p)
        if base=='home/nexium':os.chown(p,uid,gid);os.chown(p.parent,uid,gid)
    manifest=json.loads(Path('reports/phase2-manifest.json').read_text())
    for name in list(manifest):
        if '11-' in name or any(f'nexium-{key}.desktop' in name for key in ['chooser','firefox-choice','brave-choice']):manifest.pop(name)
    for p in paths:manifest['/'+str(p.relative_to(r))]=hashlib.sha256(p.read_bytes()).hexdigest()
    Path('reports/phase2-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Store a reproducible selection manifest in the image and verification manifest.
    selected=['Nexium Browser']+[title for key,title,cmd,icon in choices if key!='chooser']
    p=r/'etc/nexium-browsers.json';p.write_text(json.dumps({'shipped':selected,'search_default':'DuckDuckGo','search_options':['DuckDuckGo','Bing']},indent=2)+'\n')
    manifest['/etc/nexium-browsers.json']=hashlib.sha256(p.read_bytes()).hexdigest();Path('reports/phase2-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return selected
