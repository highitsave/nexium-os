import os,json,hashlib,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
def install(root):
    r=Path(root);paths=[]
    def put(name,text,mode=0o644):
        p=r/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);p.chmod(mode);paths.append(p);return p
    put('usr/share/xsessions/nexium.desktop','[Desktop Entry]\nName=Nexium Golden Gate\nComment=Nexium Openbox desktop\nExec=/usr/local/lib/nexium/session\nType=Application\nDesktopNames=Openbox;\n')
    put('etc/lightdm/lightdm.conf','[LightDM]\nrun-directory=/run/lightdm\n[Seat:*]\ngreeter-session=lightdm-gtk-greeter\nuser-session=nexium\nautologin-user=\nallow-guest=false\ngreeter-hide-users=false\n')
    put('etc/lightdm/lightdm-gtk-greeter.conf','[greeter]\nbackground=/usr/share/backgrounds/nexium/greeter.png\ntheme-name=GoldenGate\nicon-theme-name=NexiumIOS4\nfont-name=DejaVu Sans 11\nindicators=~spacer;~clock;~power\nclock-format=%H:%M\nposition=50%,center 65%,center\nuser-background=false\n')
    put('etc/X11/default-display-manager','/usr/sbin/lightdm\n')
    put('etc/skel/.dmrc','[Desktop]\nSession=nexium\n');dm=put('home/nexium/.dmrc','[Desktop]\nSession=nexium\n')
    uid,gid=next((int(x.split(':')[2]),int(x.split(':')[3])) for x in (r/'etc/passwd').read_text().splitlines() if x.startswith('nexium:'));os.chown(dm,uid,gid)
    # Public live-image credentials, not a saved user's private password.
    subprocess.run(['chroot',str(r),'chpasswd'],input='nexium:nexium\n',text=True,check=True)
    subprocess.run(['systemctl','--root',str(r),'disable','nexium-kiosk.service'],check=True)
    subprocess.run(['systemctl','--root',str(r),'enable','lightdm.service'],check=True)
    subprocess.run(['systemctl','--root',str(r),'set-default','graphical.target'],check=True)
    # Debian live-config must not reset the login/password or add automatic login.
    put('etc/live/config.conf.d/90-nexium.conf','LIVE_CONFIG_NOCOMPONENTS="user-setup,lightdm"\nLIVE_CONFIG_NOAUTOLOGIN="true"\nLIVE_USERNAME="nexium"\n')
    put('usr/share/nexium/persistence.conf','/ union\n')
    put('usr/local/sbin/nexium-persistence-setup',Path('scripts/nexium-persistence-setup').read_text(),0o755)
    art=Image.new('RGB',(1280,800),'#eee5d2');d=ImageDraw.Draw(art)
    f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',64);small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',23)
    d.text((640,170),'Nexium login',font=f,fill='#453a2e',anchor='mm');d.text((640,232),'Golden Gate',font=small,fill='#88704f',anchor='mm')
    p=r/'usr/share/backgrounds/nexium/greeter.png';art.save(p);paths.append(p)
    manifest=json.loads(Path('reports/phase2-manifest.json').read_text())
    for p in paths:manifest['/'+str(p.relative_to(r))]=hashlib.sha256(p.read_bytes()).hexdigest()
    Path('reports/phase2-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
def verify(root):
    r=Path(root)
    assert not (r/'etc/systemd/system/graphical.target.wants/nexium-kiosk.service').exists()
    assert 'lightdm.service' in os.readlink(r/'etc/systemd/system/display-manager.service')
    text=(r/'etc/lightdm/lightdm.conf').read_text();assert 'autologin-user=\n' in text and 'user-session=nexium' in text
    assert (r/'usr/share/nexium/persistence.conf').read_text()=='/ union\n'
    assert (r/'usr/share/backgrounds/nexium/greeter.png').is_file()
    print('PASS LightDM greeter enabled, kiosk disabled, normal nexium login; / union template; branded greeter')
if __name__=='__main__':
    import sys
    (install if sys.argv[1]=='install' else verify)(sys.argv[2])
