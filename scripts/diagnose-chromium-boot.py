import pathlib,subprocess,json,time,socket,threading,http.server,hashlib,os
from PIL import Image,ImageDraw
O=pathlib.Path('reports/boot').resolve();F=O/'frames';start=time.monotonic()
probe=r'''import os,subprocess,json,urllib.request
def command(c):
    p=subprocess.run(c,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15)
    return {'command':c,'exit':p.returncode,'output':p.stdout}
data={'environment':{k:os.environ.get(k) for k in ['DISPLAY','XDG_SESSION_TYPE','XDG_CURRENT_DESKTOP','XDG_SESSION_DESKTOP','DESKTOP_SESSION']}}
commands=['pgrep -a -x plank','ps -ef | grep -E "plank|openbox|tint2|picom"','command -v gsettings; dpkg-query -W libglib2.0-bin','gsettings get org.gnome.desktop.interface gtk-theme','gsettings get org.gnome.desktop.interface icon-theme','gsettings list-recursively net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/']
data['sudo_noninteractive']=command('/usr/bin/sudo -n true; rc=$?; echo SUDO_EXIT=$rc; exit $rc')
data['network']=command('/usr/local/bin/nexium-network-diagnostics')
data['network_manager']=command('systemctl is-active NetworkManager')
import time,stat,signal
data['runtime_environment']={k:os.environ.get(k) for k in ['HOME','USER','DISPLAY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS']}
data['runtime_paths']=[]
for path in [os.environ.get('HOME',''),os.environ.get('XDG_RUNTIME_DIR',''),'/dev/shm','/tmp']:
    try:
        st=os.stat(path);data['runtime_paths'].append({'path':path,'uid':st.st_uid,'mode':oct(stat.S_IMODE(st.st_mode)),'writable':os.access(path,os.W_OK)})
    except OSError as e:data['runtime_paths'].append({'path':path,'error':str(e)})
data['loader']=command('ldd /opt/ungoogled-chromium/chrome')
data['sandbox']=command('id; ls -l /opt/ungoogled-chromium/chrome*; cat /proc/sys/kernel/unprivileged_userns_clone; df -h /dev/shm; mount | grep shm')
data['browser_trials']=[]
data['browser_processes']=[]
trials=[('direct',['/opt/ungoogled-chromium/chrome','--no-proxy-server','about:blank']),('dock',['/usr/bin/chromium']),('safe',['/opt/ungoogled-chromium/chrome','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--user-data-dir=/tmp/cr-test','about:blank'])]
for label,argv in trials:
    path='/tmp/chromium-'+label+'.log'
    log=open(path,'w');p=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    started=time.monotonic()
    while time.monotonic()-started<60 and p.poll() is None:time.sleep(1)
    log.flush();rc=p.poll()
    trial={'label':label,'argv':argv,'pid':p.pid,'elapsed_seconds':round(time.monotonic()-started,2),'exit_code':rc,'state':'running' if rc is None else 'exited','stdout_stderr':open(path).read(),'windows':command('xwininfo -root -tree'),'processes':command('ps -ef | grep -E "chrome|chromium"')}
    data['browser_trials'].append(trial)
    print('CHROMIUM DIAGNOSTIC',json.dumps(trial,indent=2),flush=True)
    if label!='safe' and p.poll() is None:
        os.killpg(p.pid,signal.SIGTERM)
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    if label=='safe' and rc is None:data['browser_processes'].append({'pid':p.pid,'argv':argv})
    log.close()
data['browser_log']=command('cat /tmp/chromium-direct.log /tmp/chromium-dock.log /tmp/chromium-safe.log')
data['commands']=[command(c) for c in commands]
data['plank_running']=data['commands'][0]['exit']==0 and bool(data['commands'][0]['output'].strip())
data['pass']=data['plank_running'] and data['environment']['XDG_SESSION_TYPE']=='x11' and data['commands'][2]['exit']==0 and 'GoldenGate' in data['commands'][3]['output'] and 'NexiumIOS4' in data['commands'][4]['output']
urllib.request.urlopen(urllib.request.Request('http://10.0.2.2:8888/report',data=json.dumps(data,indent=2).encode(),method='POST')).read()
'''
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200);self.end_headers();self.wfile.write(probe.encode())
    def do_POST(self):
        (O/'live-session.json').write_bytes(self.rfile.read(int(self.headers['Content-Length'])))
        self.send_response(200);self.end_headers();self.wfile.write(b'OK')
server=http.server.HTTPServer(('0.0.0.0',8888),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
iso=str(pathlib.Path('output/nexium-os-1.2-ungoogled-amd64.iso').resolve())
cmd=['qemu-system-x86_64','-name','Nexium headless BIOS dock and cream verification','-machine','pc','-accel','tcg,thread=multi','-cpu','max','-smp','2','-m','3072','-boot','order=d,menu=on','-cdrom',iso,'-vga','std','-display','none','-nic','user,model=e1000','-qmp','unix:/tmp/dock-qmp.sock,server=on,wait=off','-serial','file:'+str(O/'serial.log'),'-no-reboot','-rtc','base=utc']
(O/'qemu-invocation.json').write_text(json.dumps(cmd,indent=2))
p=subprocess.Popen(cmd,stderr=(O/'qemu-stderr.log').open('w'))
sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
for _ in range(60):
    try:sock.connect('/tmp/dock-qmp.sock');break
    except OSError:time.sleep(1)
stream=sock.makefile('rwb',buffering=0);stream.readline()
def qmp(ex,args=None):
    stream.write((json.dumps({'execute':ex,'arguments':args or {}})+'\n').encode())
    while True:
        r=json.loads(stream.readline())
        if 'return' in r or 'error' in r:return r
qmp('qmp_capabilities')
def key(*codes):
    qmp('send-key',{'keys':[{'type':'qcode','data':c} for c in codes],'hold-time':30});time.sleep(.10)
entries=[];ready=None;sent=False
for n in range(300):
    deadline=start+n*2
    time.sleep(max(0,deadline-time.monotonic()))
    if time.monotonic()-start>=12 and not sent:key('ret');sent=True
    qmp('screendump',{'filename':'/tmp/dock-frame.ppm'})
    elapsed=time.monotonic()-start
    im=Image.open('/tmp/dock-frame.ppm').convert('RGB')
    out=Image.new('RGB',(im.width,im.height+42),(20,20,20));out.paste(im)
    ImageDraw.Draw(out).text((12,im.height+12),f'HEADLESS BIOS QEMU - NOT HARDWARE | frame {n:03d} | elapsed {elapsed:.2f}s',fill='white')
    out.save(F/f'bios-{n:03d}.png')
    text=subprocess.run(['tesseract','/tmp/dock-frame.ppm','stdout'],capture_output=True,text=True).stdout
    (F/f'bios-{n:03d}.txt').write_text(text)
    entries.append({'frame':n,'elapsed_seconds':round(elapsed,3),'sha256':hashlib.sha256(im.tobytes()).hexdigest(),'ocr':text})
    if 'Welcome to Nexium OS' in text and ready is None:ready=n
    if ready is not None and n>=ready+15:break
(O/'frames.json').write_text(json.dumps(entries,indent=2))
(O/'before-probe.png').write_bytes((F/f'bios-{len(entries)-1:03d}.png').read_bytes())
splash=[e for e in entries if 'TOMO' in e['ocr'].upper()]
if splash:(O/'cream-splash.png').write_bytes((F/f"bios-{splash[0]['frame']:03d}.png").read_bytes())
print('BIOS_FRAMES',len(entries),'DESKTOP_READY_FRAME',ready,'TOMO_OCR_FRAMES',[e['frame'] for e in splash],flush=True)
if ready is not None:
    key('meta_l','t');time.sleep(8)
    command="python3 -c 'import urllib.request;exec(urllib.request.urlopen(\"http://10.0.2.2:8888/probe.py\").read())'"
    chars={' ':'spc','-':'minus','.':'dot',"'":'apostrophe','/':'slash',';':'semicolon',':':('shift','semicolon'),'(':('shift','9'),')':('shift','0'),'"':('shift','apostrophe')}
    for c in command:
        mapped=chars.get(c,c);key(*(mapped if isinstance(mapped,tuple) else [mapped]))
    key('ret')
    for _ in range(180):
        if (O/'live-session.json').exists():break
        time.sleep(2)
    qmp('screendump',{'filename':'/tmp/dock-live.ppm'});Image.open('/tmp/dock-live.ppm').save(O/'live-probe.png')
status=qmp('query-status');qmp('quit');p.wait(timeout=30)
receipt={'frames':len(entries),'sample_interval_seconds':2,'wall_elapsed_seconds':round(time.monotonic()-start,3),'desktop_ready_frame':ready,'cream_text_ocr_frames':[e['frame'] for e in splash],'vm_before_stop':status,'termination':'desktop capture completed then VM explicitly stopped' if ready is not None else '600s timeout then VM explicitly stopped','iso_bytes':pathlib.Path(iso).stat().st_size,'iso_sha256':hashlib.sha256(pathlib.Path(iso).read_bytes()).hexdigest()}
(O/'receipt.json').write_text(json.dumps(receipt,indent=2))
# All chronological frames, not selected-frame-only evidence.
for offset in range(0,len(entries),20):
    sheet=Image.new('RGB',(1600,1100),(240,240,240))
    for j,e in enumerate(entries[offset:offset+20]):
        image=Image.open(F/f"bios-{e['frame']:03d}.png");image.thumbnail((400,220))
        sheet.paste(image,((j%4)*400,(j//4)*220))
    sheet.save(O/f'bios-all-{offset:03d}-{min(offset+19,len(entries)-1):03d}.jpg',quality=92)
subprocess.run(['ffmpeg','-y','-framerate','12','-i',str(F/'bios-%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','23',str(O/'nexium-dock-cream-bios.mp4')],check=True)
subprocess.run(['ffmpeg','-y','-framerate','12','-i',str(F/'bios-%03d.png'),'-vf','scale=640:-1',str(O/'nexium-dock-cream-bios.gif')],check=True)
live=json.loads((O/'live-session.json').read_text()) if (O/'live-session.json').exists() else {}
print(json.dumps(receipt,indent=2));print(json.dumps(live,indent=2))
assert ready is not None,'FAIL: desktop never reached'
assert splash,'FAIL: made by TOMO! text not observed in BIOS frames'
assert live.get('pass'),'FAIL: running Plank/X11/gsettings not verified in live guest'
assert live.get('sudo_noninteractive',{}).get('exit')==0,'FAIL: sudo -n true failed in live desktop'
assert live.get('network_manager',{}).get('exit')==0,'FAIL: NetworkManager not active in live guest'
assert live.get('browser_processes'),'FAIL: normal-user direct about:blank Chromium process not observed'
print('PASS HEADLESS BIOS: cream TOMO splash observed and live Plank process verified; visual dock review required from frames')
