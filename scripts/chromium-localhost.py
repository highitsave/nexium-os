#!/usr/bin/env python3
import argparse, hashlib, json, os, re, shutil, subprocess
from pathlib import Path as P
BAD=re.compile(r'localhost|127\.0\.0\.1',re.I)
BROWSER=re.compile(r'chromium|chrome',re.I)
PREFS={'preferences','secure preferences','local state','master_preferences','initial_preferences'}
INITIAL={'master_preferences','initial_preferences'}
def paths(root):
    for scope in ['etc','home','root','opt','usr']:
        base=root/scope
        if base.exists():yield from base.rglob('*')
def enterprise(root):
    return [p for p in paths(root) if p.name.lower() in INITIAL or BROWSER.search(str(p.relative_to(root))) and 'policies' in [q.lower() for q in p.relative_to(root).parts]]
def files(root):
    result={}
    for p in paths(root):
        if p.is_symlink() or not p.is_file():continue
        rel=str(p.relative_to(root));name=p.name.lower();ischrome=bool(BROWSER.search(rel))
        if name in INITIAL or ischrome and (name in PREFS or '/policies/' in rel.lower()):result[p]='policy/preferences';continue
        if p.stat().st_size>1000000:continue
        candidate=(ischrome or p.suffix in ['.desktop','.sh','.service'] or rel.startswith(('usr/local/','etc/xdg/','etc/environment')) or name in ['.profile','.bashrc'])
        if not candidate:continue
        try:text=p.read_text()
        except (UnicodeError,OSError):continue
        if BROWSER.search(text) or ischrome or re.search(r'(?i)(https?|all)_proxy',text):result[p]='launcher/environment'
    return result
def audit(root):
    items=[]
    for p,kind in sorted(files(root).items()):
        try:text=p.read_text()
        except UnicodeError:raise AssertionError('Non-text browser configuration: '+str(p))
        matches=[{'line':n,'text':line} for n,line in enumerate(text.splitlines(),1) if BAD.search(line) or kind=='launcher/environment' and re.search(r'proxy-server|host-resolver-rules|Exec=|exec .*chrome',line)]
        item={'file':'/'+str(p.relative_to(root)),'kind':kind,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'lines':matches}
        items.append(item)
        if matches:print('CHROMIUM AUDIT',json.dumps(item),flush=True)
    print('ENTERPRISE PATHS:',json.dumps(['/'+str(p.relative_to(root)) for p in enterprise(root)]),flush=True)
    entry=root/'usr/bin/chromium';print('CHROMIUM ENTRY:',os.readlink(entry) if entry.is_symlink() else 'regular file',flush=True)
    output=subprocess.run(['chroot',str(root),'/usr/bin/readlink','-f','/usr/bin/chromium'],capture_output=True,text=True)
    print('CHROMIUM RESOLVED:',output.stdout.strip(),flush=True)
    return items
def guard(root):
    forbidden=enterprise(root)
    assert not forbidden,'FAIL Chromium enterprise policy directory/file or initial/master preferences: '+str([str(p.relative_to(root)) for p in forbidden])
    prefs=[p for p,kind in files(root).items() if kind=='policy/preferences']
    assert prefs,'No browser preferences found; guard cannot pass vacuously'
    bad=[]
    for p in prefs:
        for n,line in enumerate(p.read_text().splitlines(),1):
            if BAD.search(line):bad.append('/'+str(p.relative_to(root))+':'+str(n)+': '+line)
    assert not bad,'FAIL Chromium localhost preference guard:\n'+'\n'.join(bad)
    print('PASS CHROMIUM GUARD:',len(prefs),'preferences without localhost/127.0.0.1; ZERO enterprise policy directories/files or initial/master preferences',flush=True)
def clean(data,path=''):
    if isinstance(data,dict):
        result={};local_proxy=any('proxy' in k.lower() and BAD.search(json.dumps(v)) for k,v in data.items())
        for k,v in data.items():
            context=path+'.'+k
            if local_proxy and 'proxy' in k.lower():
                if isinstance(v,dict):result[k]={'mode':'direct'}
                elif k.lower() in ['proxymode','proxy_mode']:result[k]='direct'
            elif BAD.search(json.dumps(v)) and re.search(r'homepage|startup|restoreonstartup|urls_to_restore|newtab',context,re.I):
                result[k]=['https://github.com/highitsave/nexium-os-releases'] if isinstance(v,list) else 'https://github.com/highitsave/nexium-os-releases' if isinstance(v,str) else clean(v,context)
            else:result[k]=clean(v,context)
        return result
    if isinstance(data,list):return [clean(v,path) for v in data]
    if isinstance(data,str) and BAD.search(data):raise AssertionError('Unrecognized localhost preference '+path+': '+data+'; inspect audit, do not blindly delete')
    return data
def fix(root):
    before_report=P('reports/chromium-before-fix.json')
    items=audit(root)
    if not before_report.exists():before_report.write_text(json.dumps(items,indent=2)+'\n')
    binary=root/'opt/ungoogled-chromium/chrome';digest=hashlib.sha256(binary.read_bytes()).hexdigest()
    for p in sorted(enterprise(root),key=lambda p:len(p.parts)):
        if not p.exists() and not p.is_symlink():continue
        print('REMOVED ENTERPRISE CONFIG:','/'+str(p.relative_to(root)),flush=True)
        if p.is_dir() and not p.is_symlink():shutil.rmtree(p)
        else:p.unlink()
    for p,kind in files(root).items():
        text=p.read_text()
        if kind=='policy/preferences' and BAD.search(text):
            p.write_text(json.dumps(clean(json.loads(text)),indent=2)+'\n');print('FIXED BROWSER CONFIG:','/'+str(p.relative_to(root)),flush=True)
        elif kind=='launcher/environment' and BAD.search(text):
            lines=[]
            for n,line in enumerate(text.splitlines(),1):
                original=line
                if BAD.search(line) and BROWSER.search(line):
                    line=re.sub(r'--proxy-server(?:=|\s+)(?:"[^"]*"|\x27[^\x27]*\x27|[^\s;]+)',lambda m:'' if BAD.search(m.group()) else m.group(),line)
                    line=re.sub(r'https?://(?:localhost|127\.0\.0\.1)(?::\d+)?[^\s"\x27;]*','https://github.com/highitsave/nexium-os-releases',line,flags=re.I)
                    if 'host-resolver-rules' in line and BAD.search(line):raise AssertionError('Inspect resolver rule '+str(p)+':'+str(n)+': '+line)
                if BAD.search(line) and re.search(r'(?i)(https?|all)_proxy\s*=',line):
                    print('REMOVED LOCAL PROXY ENV:','/'+str(p.relative_to(root))+':'+str(n),line,flush=True);continue
                if original!=line:print('FIXED LAUNCH LINE:','/'+str(p.relative_to(root))+':'+str(n),line,flush=True)
                lines.append(line)
            changed='\n'.join(lines)+'\n'
            if changed!=text:p.write_text(changed)
    wrapper=root/'usr/bin/ungoogled-chromium';text=wrapper.read_text()
    assert text.startswith('#!') and '/opt/ungoogled-chromium/chrome' in text,'Unexpected wrapper; inspect before changing'
    if '# NEXIUM_DIRECT_BROWSER' not in text:
        assert text.count('exec /opt/ungoogled-chromium/chrome')==1,text
        text=text.replace('exec /opt/ungoogled-chromium/chrome','# NEXIUM_DIRECT_BROWSER\nunset http_proxy https_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY\nif [ "$#" -eq 0 ]; then set -- https://github.com/highitsave/nexium-os-releases; fi\nexec /opt/ungoogled-chromium/chrome',1)
        wrapper.write_text(text);wrapper.chmod(0o755)
    # User preferences, NOT managed enterprise policies.
    for base in ['etc/skel','home/nexium']:
        p=root/base/'.config/chromium/Default/Preferences';p.parent.mkdir(parents=True,exist_ok=True)
        data=json.loads(p.read_text()) if p.exists() else {}
        data['homepage']='https://github.com/highitsave/nexium-os-releases';data['homepage_is_newtabpage']=False
        data['session']={**data.get('session',{}),'restore_on_startup':4,'startup_urls':['https://github.com/highitsave/nexium-os-releases']};data['proxy']={'mode':'direct'}
        p.write_text(json.dumps(data,indent=2)+'\n')
    assert hashlib.sha256(binary.read_bytes()).hexdigest()==digest,'Ungoogled ELF changed'

    # Public-only updater; no credential or enterprise policy.
    update = root/'usr/local/bin/nexium-update-check'
    update.parent.mkdir(parents=True, exist_ok=True)
    update.write_bytes(P('scripts/nexium-update-check').read_bytes())
    update.chmod(0o755)
    (root/'etc/nexium-version').write_text('1.2-golden-gate-phase2' + chr(10))
    for name in ['etc/xdg/autostart/nexium-update-check.desktop', 'usr/share/applications/nexium-update-check.desktop']:
        entry = root/name
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text('[Desktop Entry]\nType=Application\nName=Check Nexium Updates\nExec=/usr/local/bin/nexium-update-check --notify\nIcon=system-software-update\nTerminal=false\nCategories=System;\n')
    guard(root)
    tracked={'/'+str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p,kind in files(root).items() if kind=='policy/preferences' or p==wrapper}
    P('reports/chromium-fixed-manifest.json').write_text(json.dumps({'binary_sha256':digest,'files':tracked},indent=2)+'\n')
    print('PASS UNGOOGLED ELF UNCHANGED:',digest,flush=True)
def verify(root):
    assert (root/'usr/local/bin/nexium-update-check').read_bytes() == P('scripts/nexium-update-check').read_bytes()
    assert (root/'etc/nexium-version').read_text().strip() == '1.2-golden-gate-phase2'
    for name in ['etc/xdg/autostart/nexium-update-check.desktop', 'usr/share/applications/nexium-update-check.desktop']:
        assert 'Exec=/usr/local/bin/nexium-update-check --notify' in (root/name).read_text()
    for base in ['etc/skel', 'home/nexium']:
        prefs = json.loads((root/base/'.config/chromium/Default/Preferences').read_text())
        assert prefs['homepage'] == 'https://github.com/highitsave/nexium-os-releases'
        assert prefs['session']['startup_urls'] == ['https://github.com/highitsave/nexium-os-releases']
    print('PASS public update checker/version/autostart/startup; no credentials', flush=True)
    guard(root);expected=json.loads(P('reports/chromium-fixed-manifest.json').read_text())
    for name,digest in expected['files'].items():assert hashlib.sha256((root/name.lstrip('/')).read_bytes()).hexdigest()==digest,name
    assert hashlib.sha256((root/'opt/ungoogled-chromium/chrome').read_bytes()).hexdigest()==expected['binary_sha256']
    assert (root/'usr/bin/chromium').is_symlink() and os.readlink(root/'usr/bin/chromium')=='/usr/bin/ungoogled-chromium'
    text=(root/'usr/bin/ungoogled-chromium').read_text();assert 'set -- https://github.com/highitsave/nexium-os-releases' in text and '--no-sandbox' not in text and '--no-proxy-server' not in text
    print('PASS FINAL CHROMIUM: no managed policies; direct https://github.com/highitsave/nexium-os-releases default; preference hashes and original ungoogled ELF',flush=True)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('mode',choices=['audit','fix','verify','guard']);a.add_argument('root');a.add_argument('--report');args=a.parse_args();root=P(args.root).resolve()
    if args.mode=='audit':
        items=audit(root)
        if args.report:P(args.report).write_text(json.dumps(items,indent=2)+'\n')
    else:globals()[args.mode](root)
