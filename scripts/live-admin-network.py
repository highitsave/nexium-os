#!/usr/bin/env python3
import argparse,os,subprocess,json
from pathlib import Path as P
PACKAGES=['sudo','network-manager','network-manager-gnome','wpasupplicant','iw','rfkill','pciutils','usbutils','wireless-regdb','firmware-linux-nonfree','firmware-realtek','firmware-iwlwifi','firmware-atheros','firmware-brcm80211','firmware-libertas','firmware-misc-nonfree']
def run(root,*args):return subprocess.check_output(['chroot',str(root),*args],text=True).strip()
def users(root):
    result=[]
    for line in (root/'etc/passwd').read_text().splitlines():
        fields=line.split(':');name=fields[0];uid=int(fields[2])
        if name=='nexium' or (1000<=uid<65534 and fields[6] not in ['/usr/sbin/nologin','/bin/false']):result.append(name)
    assert 'nexium' in result,'Desktop service user missing'
    return sorted(set(result))
def sources(root):
    for p in [root/'etc/apt/sources.list',*(root/'etc/apt/sources.list.d').glob('*.list')]:
        if not p.exists():continue
        lines=[]
        for line in p.read_text().splitlines():
            if line.lstrip().startswith(('deb ','deb-src ')) and 'debian' in line and ' main' in line:
                for component in ['contrib','non-free','non-free-firmware']:
                    if component not in line.split():line+=' '+component
            lines.append(line)
        p.write_text('\n'.join(lines)+'\n')
    for p in (root/'etc/apt/sources.list.d').glob('*.sources'):
        text=p.read_text();lines=[]
        for line in text.splitlines():
            if line.startswith('Components:'):
                for component in ['contrib','non-free','non-free-firmware']:
                    if component not in line.split():line+=' '+component
            lines.append(line)
        p.write_text('\n'.join(lines)+'\n')
    print('APT firmware components enabled before package install',flush=True)
def install(root):
    selected=users(root);p=root/'etc/sudoers.d/90-nexium-live-admin';p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('# Intentionally passwordless admin in the authorized live desktop image.\n'+''.join(name+' ALL=(ALL:ALL) NOPASSWD: ALL\n' for name in selected));p.chmod(0o440)
    for name in selected:run(root,'/usr/sbin/usermod','-aG','sudo',name)
    run(root,'/usr/sbin/visudo','-cf','/etc/sudoers.d/90-nexium-live-admin');run(root,'/usr/sbin/visudo','-cf','/etc/sudoers')
    p=root/'etc/NetworkManager/conf.d/10-nexium-live.conf';p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('[main]\nplugins=ifupdown,keyfile\n[ifupdown]\nmanaged=true\n')
    print(run(root,'/usr/bin/systemctl','enable','NetworkManager.service'),flush=True)
    p=root/'usr/local/bin/nexium-network-diagnostics';p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('#!/bin/sh\necho "Hardware adapter and firmware diagnostics; no saved Wi-Fi secrets"\nlspci -nnk\nlsusb\nip -brief link\nrfkill list\nnmcli general status\nnmcli device status\nnmcli radio\nsudo -n dmesg | grep -iE "firmware|wlan|wifi|iwlwifi|rtl|ath|brcm" || true\n');p.chmod(0o755)
    tracked={str(p.relative_to(root)):p.read_text() for p in [root/'etc/sudoers.d/90-nexium-live-admin',root/'etc/NetworkManager/conf.d/10-nexium-live.conf',root/'usr/local/bin/nexium-network-diagnostics']}
    P('reports/admin-network-manifest.json').write_text(json.dumps({'users':selected,'files':tracked},indent=2)+'\n')
    verify(root)
def verify(root):
    assert (root/'usr/bin/sudo').is_file(),'merged-/usr sudo missing'
    p=root/'etc/sudoers.d/90-nexium-live-admin';assert p.stat().st_mode&0o777==0o440 and 'NOPASSWD: ALL' in p.read_text()
    print(run(root,'/usr/sbin/visudo','-cf','/etc/sudoers.d/90-nexium-live-admin'),flush=True);print(run(root,'/usr/sbin/visudo','-cf','/etc/sudoers'),flush=True)
    for name in users(root):
        assert 'sudo' in run(root,'/usr/bin/id','-nG',name).split()
        run(root,'/usr/sbin/runuser','-u',name,'--','/usr/bin/sudo','-n','true')
        print('PASS ADMIN:',name,'/usr/bin/sudo -n true; sudo group; validated 0440 NOPASSWD drop-in',flush=True)
    for package in PACKAGES:
        assert run(root,'/usr/bin/dpkg-query','-W','-f=${Status}',package)=='install ok installed',package
    assert list((root/'usr/lib/firmware').rglob('*')) or list((root/'lib/firmware').rglob('*')),'firmware absent'
    assert (root/'etc/systemd/system/multi-user.target.wants/NetworkManager.service').is_symlink(),'NetworkManager not enabled'
    expected=json.loads(P('reports/admin-network-manifest.json').read_text())
    for path,text in expected['files'].items():assert (root/path).read_text()==text,path
    print('PASS NETWORK: firmware package set installed; NetworkManager enabled and ifupdown interfaces managed. Physical Lenovo adapter is not accessible to this cloud build.',flush=True)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('mode',choices=['sources','install','verify']);a.add_argument('root');args=a.parse_args();globals()[args.mode](P(args.root).resolve())
