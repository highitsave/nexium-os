import ast,pathlib,subprocess,json,time,socket,threading,http.server,hashlib,os
from PIL import Image,ImageStat
O=pathlib.Path('reports/boot').resolve();F=O/'frames';F.mkdir(parents=True,exist_ok=True)
# Reuse the already strict PID/window/paint probe, never import its VM side effects.
tree=ast.parse(pathlib.Path('scripts/capture-nexium-browser.py').read_text())
probe=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='probe' for t in n.targets))
# QEMU software renderer only: avoid Mesa llvmpipe's LLVM subtarget crash, no sandbox bypass.
software="os.environ.update({'GALLIUM_DRIVER':'softpipe','QT_QUICK_BACKEND':'software','QT_OPENGL':'software','QTWEBENGINE_CHROMIUM_FLAGS':'--disable-gpu'})\n"
probe=probe.replace("data={'environment':",software+"data={'environment':",1)
before="data['environment']['test_vm_rendering']='softpipe, Qt software, WebEngine disable-gpu; sandbox remains enabled'\ndata['persistence_reboot_pass']=open(os.path.expanduser('~/.nexium-persistence-check')).read()=='NEXIUM_PERSISTENCE_PROOF\\n' and open('/proc/sys/kernel/random/boot_id').read().strip()!=open(os.path.expanduser('~/.nexium-previous-boot-id')).read().strip()\ndata['live_cmdline']=open('/proc/cmdline').read()\ndata['persistence_mounts']=command('findmnt; lsblk -f')\ndata['login_status']=command('systemctl is-active lightdm; loginctl list-sessions; id')\nassert data['persistence_reboot_pass'] and 'persistence' in data['live_cmdline']\n"
probe=probe.replace("data['sudo_noninteractive']=",before+"data['sudo_noninteractive']=",1)
compile(probe,'post-reboot-guest-probe','exec')
write=r'''import os,json,urllib.request,subprocess
from pathlib import Path
assert os.getuid()!=0
Path.home().joinpath('.nexium-persistence-check').write_text('NEXIUM_PERSISTENCE_PROOF\n')
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
Path.home().joinpath('.nexium-previous-boot-id').write_text(boot)
subprocess.run(['sync'],check=True)
data={'marker':'NEXIUM_PERSISTENCE_PROOF','boot_id_before':boot,'uid':os.getuid(),'cmdline':Path('/proc/cmdline').read_text(),'mounts':subprocess.run(['findmnt'],capture_output=True,text=True).stdout}
urllib.request.urlopen(urllib.request.Request('http://10.0.2.2:8888/persistence-before.json',data=json.dumps(data,indent=2).encode(),method='POST')).read()
subprocess.run(['sudo','-n','systemctl','reboot'],check=True)
'''
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body=pathlib.Path('scripts/chooser-live-test.py').read_bytes() if self.path=='/chooser-test.py' else write.encode() if self.path=='/write.py' else probe.encode()
        self.send_response(200);self.end_headers();self.wfile.write(body)
    def do_POST(self):
        name=self.path.strip('/') if self.path in ['/browser-window.png','/persistence-before.json'] else 'live-session.json'
        (O/name).write_bytes(self.rfile.read(int(self.headers['Content-Length'])))
        self.send_response(200);self.end_headers();self.wfile.write(b'OK')
server=http.server.HTTPServer(('0.0.0.0',8888),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
iso=str(pathlib.Path('output/nexium-os-1.2-ungoogled-amd64.iso').resolve())
cmd=['qemu-system-x86_64','-machine','pc','-accel','tcg,thread=multi','-cpu','max','-smp','2','-m','3072','-boot','order=d,menu=on','-cdrom',iso,'-vga','std','-display','none','-nic','user,model=e1000','-device','qemu-xhci,id=xhci','-drive','if=none,id=usbdata,format=raw,file='+str(pathlib.Path('work/persistence-disk.img').resolve()),'-device','usb-storage,drive=usbdata','-qmp','unix:/tmp/login-qmp.sock,server=on,wait=off','-serial','file:'+str(O/'serial.log'),'-rtc','base=utc']
(O/'qemu-invocation.json').write_text(json.dumps(cmd,indent=2)+'\n');started=time.monotonic();p=subprocess.Popen(cmd,stderr=(O/'qemu-stderr.log').open('w'))
sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
for _ in range(60):
    try:sock.connect('/tmp/login-qmp.sock');break
    except OSError:time.sleep(1)
stream=sock.makefile('rwb',buffering=0);stream.readline()
def qmp(ex,args=None):
    stream.write((json.dumps({'execute':ex,'arguments':args or {}})+'\n').encode())
    while True:
        r=json.loads(stream.readline())
        if 'return' in r or 'error' in r:assert 'error' not in r, 'FAIL QMP command rejected: '+json.dumps({'command':ex,'arguments':args or {},'response':r});return r
qmp('qmp_capabilities')
def key(*codes):
    qmp('send-key',{'keys':[{'type':'qcode','data':c} for c in codes],'hold-time':40});time.sleep(.12)
chars={' ':'spc','-':'minus','.':'dot',"'":'apostrophe','/':'slash',';':'semicolon',':':('shift','semicolon'),'(':('shift','9'),')':('shift','0'),'"':('shift','apostrophe')}
def typed(value):
    for c in value:
        mapped=('shift',c.lower()) if 'A'<=c<='Z' else chars.get(c,c);key(*(mapped if isinstance(mapped,tuple) else [mapped]))
entries=[];greeters=[];splash=[];desktop=[]
def frame(stage):
    n=len(entries);qmp('screendump',{'filename':'/tmp/login-frame.ppm'});im=Image.open('/tmp/login-frame.ppm').convert('RGB');file=F/f'frame-{n:04d}.png';im.save(file)
    text=subprocess.run(['tesseract',str(file),'stdout'],capture_output=True,text=True).stdout
    e={'frame':n,'stage':stage,'elapsed':round(time.monotonic()-started,2),'ocr':text};entries.append(e)
    if 'TOMO' in text.upper():splash.append(e);im.save(O/'cream-splash.png')
    (O/'frames.json').write_text(json.dumps(entries,indent=2))
    return im,text
def boot_and_login(stage):
    deadline=time.monotonic()+600;sent=False;logged=False;greeter=None;login_at=0;retry=0
    while time.monotonic()<deadline:
        im,text=frame(stage)
        if not sent and ('NEXIUM' in text.upper() or time.monotonic()-started>15):key('ret');sent=True
        if not logged and 'Nexium login' in text:
            greeter={'stage':stage,'width':im.width,'height':im.height,'variance':sum(ImageStat.Stat(im).var),'ocr':text}
            assert im.width>=800 and im.height>=600 and greeter['variance']>50
            im.save(O/f'greeter-{stage}.png');greeters.append(greeter)
            # Greeter explicitly requests the normal user's username, then password.
            typed('nexium');key('ret');time.sleep(3);typed('nexium');key('ret');logged=True;login_at=time.monotonic()
        if logged and ('Welcome to Nexium OS' in text or time.monotonic()-login_at>30 and 'Nexium login' not in text):
            time.sleep(15);im,text=frame(stage);im.save(O/f'desktop-{stage}.png');desktop.append(stage);return
        if logged and time.monotonic()-login_at>40 and 'Nexium login' in text and retry<1:
            # Alternative keyboard route if GTK initially focused its user selector.
            key('tab');typed('nexium');key('ret');retry+=1;login_at=time.monotonic()
        time.sleep(2)
    raise AssertionError('FAIL greeter/login/desktop timeout '+stage)
def terminal_script(name):
    key('ret');time.sleep(2);im,text=frame('dismiss-welcome');w,h=im.size;qmp('input-send-event',{'events':[{'type':'abs','data':{'axis':'x','value':int((w-44)*32767/w)}},{'type':'abs','data':{'axis':'y','value':int((h-8)*32767/h)}},{'type':'btn','data':{'button':'left','down':True}},{'type':'btn','data':{'button':'left','down':False}}]});time.sleep(2);im,text=frame('dismiss-welcome-clicked');assert 'Nexium login' not in text,'FAIL welcome OK click returned to greeter';key('meta_l','t');time.sleep(3);typed('echo NEXIUMTERMINALREADY');key('ret');time.sleep(2);im,text=frame('terminal-ready');assert 'NEXIUMTERMINALREADY' in text.upper(), 'FAIL Super+T did not open terminal';time.sleep(3)
    typed("python3 -c 'import urllib.request;exec(urllib.request.urlopen(\"http://10.0.2.2:8888/"+name+"\").read())'");key('ret')
try:
    boot_and_login('before-reboot')
    terminal_script('write.py')
    for _ in range(120):
        if (O/'persistence-before.json').exists():break
        frame('reboot-request');time.sleep(2)
    assert (O/'persistence-before.json').exists(),'FAIL persistence write/normal user reboot request'
    # Require a genuine reboot reaching greeter again, not a second terminal in the same boot.
    time.sleep(20);boot_and_login('after-reboot')
    terminal_script('probe.py')
    for _ in range(450):
        if (O/'live-session.json').exists():break
        frame('post-reboot-gui');time.sleep(2)
    live=json.loads((O/'live-session.json').read_text()) if (O/'live-session.json').exists() else {}
    im,text=frame('final');im.save(O/'final-desktop.png')
    print('NEXIUM STDOUT/STDERR BEGIN',flush=True);print(live.get('browser_launch',{}).get('stdout_stderr','<no report>'),flush=True);print('NEXIUM STDOUT/STDERR END',flush=True)
    print(json.dumps(live,indent=2),flush=True)
    receipt={'iso_bytes':pathlib.Path(iso).stat().st_size,'iso_sha256':hashlib.sha256(pathlib.Path(iso).read_bytes()).hexdigest(),'greeter_paint_pass':len(greeters)>=2,'greeters':greeters,'persistence_reboot_pass':live.get('persistence_reboot_pass',False),'chooser_restart_pass':live.get('chooser_restart_pass',False),'browser_gui_pass':live.get('browser_gui_pass',False),'cream_splash_pass':bool(splash),'plank_running':live.get('plank_running',False),'sudo_exit':live.get('sudo_noninteractive',{}).get('exit'),'wall_elapsed_seconds':round(time.monotonic()-started,2),'test_kind':'HEADLESS QEMU BIOS, virtual USB persistence; NOT PHYSICAL HARDWARE'}
    (O/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2),flush=True)
    assert receipt['greeter_paint_pass'] and receipt['persistence_reboot_pass'] and receipt['chooser_restart_pass']
    assert receipt['cream_splash_pass'] and receipt['plank_running'] and receipt['sudo_exit']==0 and receipt['browser_gui_pass']
    subprocess.run(['python3','scripts/assert-nexium-capture.py',str(O)],check=True)
    print('PASS FINAL LOGIN, USB PERSISTENCE AFTER REAL REBOOT, CHOOSER RESTARTS AND REAL NEXIUM PAINT',flush=True)
finally:
    if p.poll() is None:
        qmp('quit');p.wait(timeout=30)
    server.shutdown()
