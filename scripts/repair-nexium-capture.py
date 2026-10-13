"""Test-only guest provisioning and strict paint gate; does not modify ISO or browser."""
import ast
from pathlib import Path
p=Path('scripts/capture-nexium-browser.py')
s=p.read_text()
if '# NEXIUM_STRICT_PAINT_PROBE' in s:
    print('Strict capture repair already present')
    raise SystemExit(0)
needle="text = open('/usr/share/applications/nexium-browser.desktop').read()"
provision=r'''# NEXIUM_STRICT_PAINT_PROBE
# X helpers must exist INSIDE the guest running this probe, not only on the host.
data['test_only_guest_packages'] = []
try:
    for setup in [['sudo','-n','apt-get','update'], ['sudo','-n','env','DEBIAN_FRONTEND=noninteractive','apt-get','install','-y','--no-install-recommends','xdotool','wmctrl','scrot','x11-utils']]:
        result=subprocess.run(setup,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
        record={'argv':setup,'exit':result.returncode,'output':result.stdout}
        data['test_only_guest_packages'].append(record)
        print(json.dumps(record),flush=True)
        assert result.returncode==0, 'FAIL guest X helper installation'
    data['test_helpers']=command('command -v xdotool; command -v wmctrl; command -v scrot; command -v xwininfo; command -v xprop')
    assert data['test_helpers']['exit']==0
except Exception as e:
    data['setup_error']=repr(e);data['browser_gui_pass']=False;data['pass']=False
    urllib.request.urlopen(urllib.request.Request('http://10.0.2.2:8888/report',data=json.dumps(data,indent=2).encode(),method='POST')).read()
    raise
'''
assert s.count(needle)==1
s=s.replace(needle,provision+'\n'+needle)
begin=s.index('# Accept the actual Terms widget through X11 input; no shipped bypass.')
end=s.index('began = time.monotonic()',begin)
terms=r'''# Accept only the real mapped Terms window's bottom-right I Agree button.
# No test bypass is introduced into the shipped browser source.
terms_started=time.monotonic()
data['terms_interaction']=[]
while time.monotonic()-terms_started<90 and browser.poll() is None:
    terms=command("xdotool search --onlyvisible --name '^Nexium Browser.*Terms of Service$'")
    data['terms_window']=terms
    if terms['exit']==0 and terms['output'].strip():
        wid=terms['output'].splitlines()[0]
        geometry=command('xdotool getwindowgeometry --shell '+wid)
        values=dict(re.findall(r'^(WIDTH|HEIGHT)=(\d+)$',geometry['output'],re.M))
        if int(values.get('WIDTH',0))>=720 and int(values.get('HEIGHT',0))>=570:
            data['terms_geometry']=geometry
            data['terms_interaction'].append(command('wmctrl -ia '+wid))
            time.sleep(2)
            # Contents margins: right 34px, bottom 30px; button centre is ~84,49px inward.
            x=int(values['WIDTH'])-84;y=int(values['HEIGHT'])-49
            data['terms_interaction'].append(command('xdotool mousemove --window '+wid+' '+str(x)+' '+str(y)+' click 1'))
            time.sleep(15)
            data['terms_after_accept']=command("xdotool search --onlyvisible --name '^Nexium Browser.*Terms of Service$'")
            break
    time.sleep(2)
'''
s=s[:begin]+terms+s[end:]
s=s.replace("int(m[3]) < 100 or int(m[4]) < 100", "int(m[3]) < 900 or int(m[4]) < 600")
s=s.replace("'pid':window_pid}", "'pid':window_pid, 'width':int(m[3]), 'height':int(m[4])}")
needle="browser_log.flush()"
paint=r'''data['browser_paint_capture']=None
if data['browser_processes'] and data['browser_windows'] and browser.poll() is None:
    wid=data['browser_windows'][0]['id']
    data['browser_activate']=command('wmctrl -ia '+wid)
    time.sleep(8)
    data['browser_paint_capture']=command('scrot --overwrite -u /tmp/nexium-browser-window.png')
    if data['browser_paint_capture']['exit']==0:
        urllib.request.urlopen(urllib.request.Request('http://10.0.2.2:8888/browser-window.png',data=open('/tmp/nexium-browser-window.png','rb').read(),method='POST')).read()
'''
assert s.count(needle)==1
s=s.replace(needle,paint+'\n'+needle)
s=s.replace("data['browser_gui_pass'] = bool(data['browser_processes'] and data['browser_windows'])", "data['browser_gui_pass'] = bool(data['browser_processes'] and data['browser_windows'] and data.get('browser_paint_capture',{}).get('exit')==0)")
s=s.replace("data['pass']=data['plank_running']", "data['pass']=data['browser_gui_pass'] and data['plank_running']")
needle="(O/'live-session.json').write_bytes(self.rfile.read(int(self.headers['Content-Length'])))"
assert s.count(needle)==1
s=s.replace(needle,"target = O/('browser-window.png' if self.path=='/browser-window.png' else 'live-session.json')\n        target.write_bytes(self.rfile.read(int(self.headers['Content-Length'])))")
s=s.replace('for _ in range(180):','for _ in range(360):')
# Emit browser logs BEFORE any assertion, including failures of the combined pass flag.
begin=s.index("print('NEXIUM STDOUT/STDERR BEGIN'")
end=s.index("assert live.get('browser_gui_pass')",begin)
logging=s[begin:end]
s=s[:begin]+s[end:]
gate="assert ready is not None,'FAIL: desktop never reached'"
assert s.count(gate)==1
s=s.replace(gate,logging+'\n'+gate)
s += "\nsubprocess.run(['python3','scripts/assert-nexium-capture.py',str(O)],check=True)\n"
tree=ast.parse(s)
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='probe' for t in node.targets):
        compile(ast.literal_eval(node.value),'real-guest-probe','exec')
compile(s,str(p),'exec')
p.write_text(s)
print('PASS strict guest probe syntax, real geometry threshold, stdout/stderr before assertions')
