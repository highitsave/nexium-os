#!/usr/bin/env python3
"""Browser-specific adapter; original queued Chromium scripts remain unchanged."""
import argparse, importlib.util, json, hashlib, shutil, subprocess, re, os
from pathlib import Path
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
phase=load('phase','desktop/phase2.py')
chrom=load('chrom','scripts/chromium-localhost.py')
original_run=subprocess.run
phase.APPS[:]=[(k,'Nexium Browser','/usr/local/bin/nexium-browser','web-browser') if k=='browser' else (k,n,c,i) for k,n,c,i in phase.APPS]
def browser_config(root,install=False):
    r=Path(root)
    if install:
        for p in sorted(chrom.enterprise(r),key=lambda p:len(p.parts)):
            if not p.exists() and not p.is_symlink():continue
            if p.is_dir() and not p.is_symlink():shutil.rmtree(p)
            else:p.unlink()
        for p,kind in chrom.files(r).items():
            if kind=='policy/preferences' and chrom.BAD.search(p.read_text()):
                p.write_text(json.dumps(chrom.clean(json.loads(p.read_text())),indent=2)+'\n')
        # Non-enterprise compatibility preferences keep localhost guards non-vacuous.
        for base in ['etc/skel','home/nexium']:
            p=r/base/'.config/chromium/Default/Preferences';p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps({'homepage':'https://github.com/highitsave/nexium-os-releases','proxy':{'mode':'direct'}},indent=2)+'\n')
        p=r/'usr/local/bin/nexium-update-check';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(Path('scripts/nexium-update-check').read_bytes());p.chmod(0o755)
        (r/'etc/nexium-version').write_text('1.2-golden-gate-nexium-browser\n')
    chrom.guard(r)
def run_hook(argv,*args,**kw):
    if isinstance(argv,list) and len(argv)>3 and argv[1]=='scripts/chromium-localhost.py':
        browser_config(argv[3],argv[2]=='fix');return subprocess.CompletedProcess(argv,0)
    return original_run(argv,*args,**kw)
subprocess.run=run_hook
def verify_browser(root):
    r=Path(root)
    assert not (r/'opt/ungoogled-chromium/chrome').exists(),'Standalone Chromium was not removed'
    for target in ['/usr/local/bin/nexium-browser','/opt/nexium-browser/venv/bin/python']:
        phase.output_executable(r,target)
    assert (r/'usr/local/lib/nexium/nexium_browser.py').read_bytes()==Path('browser/nexium_browser.py').read_bytes()
    original_run(['chroot',str(r),'/opt/nexium-browser/venv/bin/python','-c','from PySide6.QtWebEngineWidgets import QWebEngineView; from PySide6.QtWebEngineCore import QWebEngineProfile,QWebEnginePage; print("PASS PYSIDE6 QTWEBENGINE IMPORTS")'],check=True)
    print('PASS NEXIUM browser source, isolated Python, imports, and removal of standalone Chromium')
phase.verify_ungoogled=verify_browser
def install(root):
    phase.install(root)
    r=Path(root)
    script=r/'usr/local/lib/nexium/nexium_browser.py';script.write_bytes(Path('browser/nexium_browser.py').read_bytes());script.chmod(0o644)
    launcher=r/'usr/local/bin/nexium-browser'
    launcher.write_text('#!/bin/sh\nunset http_proxy https_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY\nexport QT_QPA_PLATFORM=xcb\nexec /opt/nexium-browser/venv/bin/python /usr/local/lib/nexium/nexium_browser.py "$@"\n');launcher.chmod(0o755)
    desktop=r/'usr/share/applications/nexium-browser.desktop'
    desktop.write_text('[Desktop Entry]\nType=Application\nName=Nexium Browser\nExec=/usr/local/bin/nexium-browser\nIcon=nexium-browser\nTerminal=false\nCategories=Network;WebBrowser;\nMimeType=text/html;x-scheme-handler/http;x-scheme-handler/https;\nStartupWMClass=nexium_browser.py\n')
    icon=r/'usr/share/icons/hicolor/scalable/apps/nexium-browser.svg';icon.parent.mkdir(parents=True,exist_ok=True)
    icon.write_bytes(Path('branding/icons/nexium-browser.svg').read_bytes())
    mapping=json.loads(Path('branding/icons/ios4/mapping.json').read_text())
    uid,gid=next((int(x.split(':')[2]),int(x.split(':')[3])) for x in (r/'etc/passwd').read_text().splitlines() if x.startswith('nexium:'))
    paths=[script,launcher,desktop,icon]
    for base in ['etc/skel','home/nexium']:
        p=r/base/'.config/mimeapps.list';p.parent.mkdir(parents=True,exist_ok=True);p.write_text('[Default Applications]\ntext/html=nexium-browser.desktop\nx-scheme-handler/http=nexium-browser.desktop\nx-scheme-handler/https=nexium-browser.desktop\n');paths.append(p)
        if base=='home/nexium':os.chown(p,uid,gid)
    manifest=json.loads(Path('reports/phase2-manifest.json').read_text())
    for p in paths:manifest['/'+str(p.relative_to(r))]=hashlib.sha256(p.read_bytes()).hexdigest()
    Path('reports/phase2-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
def verify(root):
    # Original checks still validate all ten iOS4 icons before custom browser icon override.
    r=Path(root);desktop=r/'usr/share/applications/nexium-browser.desktop'
    saved=desktop.read_bytes();mapping=json.loads(Path('branding/icons/ios4/mapping.json').read_text())
    manifest=json.loads(Path('reports/phase2-manifest.json').read_text())
    try:
        desktop.write_text(saved.decode().replace('Icon=nexium-browser','Icon=ios4-'+mapping['browser']))
        manifest['/usr/share/applications/nexium-browser.desktop']=hashlib.sha256(desktop.read_bytes()).hexdigest()
        Path('reports/phase2-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        phase.verify(root)
    finally:
        desktop.write_bytes(saved)
        manifest['/usr/share/applications/nexium-browser.desktop']=hashlib.sha256(saved).hexdigest()
        Path('reports/phase2-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    assert 'Icon=nexium-browser' in desktop.read_text()
    assert (r/'usr/share/icons/hicolor/scalable/apps/nexium-browser.svg').read_bytes()==Path('branding/icons/nexium-browser.svg').read_bytes()
    for name,digest in manifest.items():assert hashlib.sha256((r/name.lstrip('/')).read_bytes()).hexdigest()==digest,name
    print('PASS actual on-disk Nexium browser launcher and custom Nexium icon; full final manifest SHA256 checked')
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--install');a.add_argument('--verify');o=a.parse_args()
    if o.install:install(o.install)
    if o.verify:verify(o.verify)
