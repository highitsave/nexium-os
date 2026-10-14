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
# Failure-only guest diagnostics. This does not satisfy or replace any proof gate.
diagnostic=r'''import os,json,urllib.request,subprocess,pwd,ctypes,threading,time
from pathlib import Path
assert os.getuid()!=0 and pwd.getpwuid(os.getuid()).pw_name=='nexium', 'diagnostics require normal nexium user'
data={'uid':os.getuid(),'home':str(Path.home()),'environment':dict(os.environ),'commands':[],'key_samples':[]}
env=os.environ.copy()
# Use the actual graphical terminal's DISPLAY and authority, not a guessed display.
assert env.get('DISPLAY'), 'diagnostic terminal has no DISPLAY'
x=ctypes.CDLL('libX11.so.6')
x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p
x.XStringToKeysym.argtypes=[ctypes.c_char_p];x.XStringToKeysym.restype=ctypes.c_ulong
x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XKeysymToKeycode.restype=ctypes.c_ubyte
x.XQueryKeymap.argtypes=[ctypes.c_void_p,ctypes.c_char_p]
x.XCloseDisplay.argtypes=[ctypes.c_void_p]
d=x.XOpenDisplay(env['DISPLAY'].encode());assert d, 'cannot open actual X display'
names=['Super_L','Control_L','Alt_L','t','F2']
codes={n:int(x.XKeysymToKeycode(d,x.XStringToKeysym(n.encode()))) for n in names}
data['x_keycodes']=codes
stop=threading.Event()
def sample():
    last=None;begin=time.monotonic()
    while not stop.is_set():
        buf=ctypes.create_string_buffer(32);x.XQueryKeymap(d,buf)
        pressed=[n for n,c in codes.items() if c and buf.raw[c//8] & (1 << (c%8))]
        if pressed!=last:
            data['key_samples'].append({'elapsed':round(time.monotonic()-begin,3),'pressed':pressed});last=pressed
        time.sleep(.005)
t=threading.Thread(target=sample);t.start()
urllib.request.urlopen(urllib.request.Request('http://10.0.2.2:8888/diagnostic-ready.json',data=json.dumps({'display':env['DISPLAY'],'keycodes':codes}).encode(),method='POST'),timeout=10).read()
commands=[
    'id; loginctl list-sessions; loginctl session-status',
    'ps -eo user,pid,args',
    'printf "PATH=%s\\n" "$PATH"; command -v xterm; command -v openbox; command -v openbox-session; ls -l /usr/bin/xterm /usr/bin/openbox /usr/bin/openbox-session /tmp/.X11-unix',
    'xprop -root _OB_CONFIG_FILE _OB_VERSION _NET_SUPPORTING_WM_CHECK _NET_ACTIVE_WINDOW; wm=$(xprop -root _NET_SUPPORTING_WM_CHECK | grep -o "0x[0-9a-fA-F]*" | head -n1); if test -n "$wm"; then xprop -id "$wm" _NET_WM_NAME WM_CLASS; fi',
    'cat "$HOME/.config/openbox/rc.xml"; cat "$HOME/.config/openbox/autostart"; for pid in $(pgrep -u "$(id -u)" -x openbox); do tr "\\0" " " < /proc/$pid/cmdline; echo; tr "\\0" "\\n" < /proc/$pid/environ | grep -E "^(HOME|PATH|DISPLAY|XDG_CONFIG_HOME|XDG_CURRENT_DESKTOP)="; done',
    'tail -n 200 "$HOME/.xsession-errors"; journalctl --user -b --no-pager -n 200',
    'xmodmap -pm; setxkbmap -query; xwininfo -root -tree',
    "xterm -e /bin/sh -c 'echo NEXIUMDIAGNOSTIC; sleep 5'",
]
try:
    for command in commands:
        try:
            r=subprocess.run(command,shell=True,capture_output=True,text=True,env=env,timeout=20)
            record={'command':command,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
        except subprocess.TimeoutExpired as e:
            record={'command':command,'timeout':20,'stdout':(e.stdout or b'').decode(errors='replace') if isinstance(e.stdout,bytes) else e.stdout,'stderr':(e.stderr or b'').decode(errors='replace') if isinstance(e.stderr,bytes) else e.stderr}
        data['commands'].append(record)
    time.sleep(15)
finally:
    stop.set();t.join();x.XCloseDisplay(d)
urllib.request.urlopen(urllib.request.Request('http://10.0.2.2:8888/terminal-diagnostic.json',data=json.dumps(data,indent=2).encode(),method='POST'),timeout=10).read()
'''
compile(diagnostic,'failure-only-guest-diagnostic','exec')
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body=pathlib.Path('scripts/chooser-live-test.py').read_bytes() if self.path=='/chooser-test.py' else write.encode() if self.path=='/write.py' else diagnostic.encode() if self.path=='/diagnostic.py' else probe.encode()
        self.send_response(200);self.end_headers();self.wfile.write(body)
    def do_POST(self):
        name=self.path.strip('/') if self.path in ['/browser-window.png','/persistence-before.json','/terminal-diagnostic.json','/diagnostic-ready.json'] else 'live-session.json'
        (O/name).write_bytes(self.rfile.read(int(self.headers['Content-Length'])))
        self.send_response(200);self.end_headers();self.wfile.write(b'OK')
server=http.server.HTTPServer(('0.0.0.0',8888),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
iso=str(pathlib.Path('output/nexium-os-1.2-ungoogled-amd64.iso').resolve())
cmd=['qemu-system-x86_64','-machine','pc','-accel','tcg,thread=multi','-cpu','max','-smp','2','-m','3072','-boot','order=d,menu=on','-cdrom',iso,'-vga','std','-display','none','-nic','user,model=e1000','-device','qemu-xhci,id=xhci','-device','usb-tablet,bus=xhci.0','-drive','if=none,id=usbdata,format=raw,file='+str(pathlib.Path('work/persistence-disk.img').resolve()),'-device','usb-storage,drive=usbdata','-qmp','unix:/tmp/login-qmp.sock,server=on,wait=off','-serial','file:'+str(O/'serial.log'),'-rtc','base=utc']
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
        if 'return' in r or 'error' in r:
            if ex in ['send-key','input-send-event']:
                with (O/'qmp-inputs.jsonl').open('a') as log:
                    log.write(json.dumps({'elapsed':round(time.monotonic()-started,3),'command':ex,'arguments':args or {},'response':r})+'\n')
            assert 'error' not in r, 'FAIL QMP command rejected: '+json.dumps({'command':ex,'arguments':args or {},'response':r})
            return r
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
    # Keep each stage's actual latest paint in the top-level committed evidence.
    im.save(O/(stage+'-latest.png'))
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
    key('ret');time.sleep(2);im,text=frame('dismiss-welcome');w,h=im.size;qmp('input-send-event',{'events':[{'type':'abs','data':{'axis':'x','value':int((w-44)*32767/w)}},{'type':'abs','data':{'axis':'y','value':int((h*0.69)*32767/h)}},{'type':'btn','data':{'button':'left','down':True}},{'type':'btn','data':{'button':'left','down':False}}]});time.sleep(2);im,text=frame('dismiss-welcome-clicked');assert 'Nexium login' not in text and 'Welcome to Nexium OS' not in text,'FAIL welcome OK click did not close modal or returned to greeter';key('meta_l','t');time.sleep(3);typed('echo NEXIUMTERMINALREADY');key('ret');time.sleep(2);im,text=frame('terminal-ready');assert 'NEXIUMTERMINALREADY' in text.upper(), 'FAIL Super+T did not open terminal';time.sleep(3)
    typed("python3 -c 'import urllib.request;exec(urllib.request.urlopen(\"http://10.0.2.2:8888/"+name+"\").read())'");key('ret')
def diagnostic_pointer_terminal():
    # Pointer-only recovery for diagnostics: unlike tty2 it does not require a modifier chord.
    # The failed original proof stays failed even if this paints a working terminal.
    import csv,io
    im,text=frame('diagnostic-root-before');w,h=im.size
    def click(x,y,button):
        qmp('input-send-event',{'events':[{'type':'abs','data':{'axis':'x','value':int(x*32767/w)}},{'type':'abs','data':{'axis':'y','value':int(y*32767/h)}}]})
        qmp('input-send-event',{'events':[{'type':'btn','data':{'button':button,'down':True}}]});time.sleep(.3)
        qmp('input-send-event',{'events':[{'type':'btn','data':{'button':button,'down':False}}]});time.sleep(2)
    click(w/2,h/2,'right');im,text=frame('diagnostic-root-menu')
    tsv=subprocess.run(['tesseract',str(O/'diagnostic-root-menu-latest.png'),'stdout','--psm','11','tsv'],check=True,capture_output=True,text=True).stdout
    matches=[r for r in csv.DictReader(io.StringIO(tsv),delimiter='\t') if r.get('text','').strip().lower()=='terminal']
    assert len(matches)==1, 'diagnostic pointer root menu did not paint exactly one Terminal item: '+text
    r=matches[0];click(int(r['left'])+int(r['width'])/2,int(r['top'])+int(r['height'])/2,'left')
    frame('diagnostic-terminal-launch');typed('echo NEXIUMDIAGNOSTICTERMINAL');key('ret');time.sleep(3)
    im,text=frame('diagnostic-terminal-painted')
    assert 'NEXIUMDIAGNOSTICTERMINAL' in text.upper(), 'diagnostic pointer terminal did not paint executed marker: '+text
    typed("python3 -c 'import urllib.request;exec(urllib.request.urlopen(\"http://10.0.2.2:8888/diagnostic.py\").read())'");key('ret')
    for _ in range(30):
        if (O/'diagnostic-ready.json').exists():break
        frame('diagnostic-report-start');time.sleep(2)
    assert (O/'diagnostic-ready.json').exists(), 'diagnostic X key sampler not ready'
    # Compare existing short send-key chord with explicit staggered down/up while X samples actual keys.
    key('meta_l','t');time.sleep(2)
    for code in ['meta_l','t']:
        qmp('input-send-event',{'events':[{'type':'key','data':{'down':True,'key':{'type':'qcode','data':code}}}]});time.sleep(.5)
    time.sleep(1)
    for code in ['t','meta_l']:
        qmp('input-send-event',{'events':[{'type':'key','data':{'down':False,'key':{'type':'qcode','data':code}}}]});time.sleep(.5)
    frame('diagnostic-input-observation')
    for _ in range(60):
        if (O/'terminal-diagnostic.json').exists():break
        frame('diagnostic-report-wait');time.sleep(2)
    assert (O/'terminal-diagnostic.json').exists(), 'diagnostic guest report not received'
    print('FAILURE-ONLY GUEST DIAGNOSTICS BEGIN',flush=True)
    print((O/'terminal-diagnostic.json').read_text(),flush=True)
    print('FAILURE-ONLY GUEST DIAGNOSTICS END',flush=True)
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
except AssertionError as original:
    (O/'failure.txt').write_text(str(original)+'\n')
    # Recover only to collect evidence, never continue the proof after the failed shortcut.
    if str(original)=='FAIL Super+T did not open terminal':
        try:
            frame('terminal-failure')
            diagnostic_pointer_terminal()
        except Exception as diagnostic_error:
            (O/'diagnostic-error.txt').write_text(repr(diagnostic_error)+'\n')
            print('FAILURE-ONLY DIAGNOSTICS UNAVAILABLE: '+repr(diagnostic_error),flush=True)
    raise
finally:
    if p.poll() is None:
        qmp('quit');p.wait(timeout=30)
    server.shutdown()
