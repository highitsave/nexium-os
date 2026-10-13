from pathlib import Path
import ast
p=Path('desktop/phase2.py');s=p.read_text()
old="    assert len(pins)==10, f'Expected 10 pins, got {len(pins)}'"
new='''    # Retain ALL ten original pins and icons, additionally verify authorized browser pins.
    expected={p.name for p in P('desktop/dock/launchers').glob('*.dockitem')}
    assert len(expected)==10, 'Original ten dock pins must remain intact'
    expected.add('11-chooser.dockitem')
    for key,exe in [('firefox-choice','/usr/bin/firefox-esr'),('brave-choice','/usr/bin/brave-browser')]:
        if (r/exe.lstrip('/')).exists():
            expected.add('11-'+key+'.dockitem')
            output_executable(r,exe)
            assert 'Exec='+exe in (r/f'usr/share/applications/nexium-{key}.desktop').read_text()
    for base in ['etc/skel','home/nexium']:
        actual={p.name for p in (r/base/'.config/plank/dock1/launchers').glob('*.dockitem')}
        assert actual==expected, f'Dock pin mismatch: expected {expected}, got {actual}'
    print('PASS original ten pins plus all installed chooser/browser pins:',sorted(expected))'''
if old in s:s=s.replace(old,new)
else:assert 'Original ten dock pins must remain intact' in s
ast.parse(s);p.write_text(s)
# The earlier dpkg recovery is now present; cover its exact field name as well.
for name in ['scripts/install-nexium-browser.sh','scripts/measure-install-chooser.sh']:
    p=Path(name);s=p.read_text()
    for v in ['k','s','size']:s=s.replace('int('+v+')*1024','int('+v+' or 0)*1024')
    p.write_text(s)
# A new real process per stage tests restart persistence in the final booted guest.
p=Path('scripts/capture-nexium-browser.py');s=p.read_text()
needle="text = open('/usr/share/applications/nexium-browser.desktop').read()"
if 'chooser_restart_test' not in s:
    test=r'''test_path='/tmp/nexium-chooser-live-test.py'
open(test_path,'wb').write(urllib.request.urlopen('http://10.0.2.2:8888/chooser-test.py').read())
data['chooser_restart_test']=[]
for stage in ['add','restart-remove','restart-check']:
    result=subprocess.run(['/opt/nexium-browser/venv/bin/python',test_path,stage],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
    data['chooser_restart_test'].append({'stage':stage,'exit':result.returncode,'stdout_stderr':result.stdout})
    print('CHOOSER LIVE STAGE',stage,result.returncode,result.stdout,flush=True)
    if result.returncode!=0:
        data['browser_gui_pass']=False;data['pass']=False
        urllib.request.urlopen(urllib.request.Request('http://10.0.2.2:8888/report',data=json.dumps(data,indent=2).encode(),method='POST')).read()
        raise AssertionError('FAIL final guest chooser restart test '+stage)
data['chooser_restart_pass']=True
'''
    assert s.count(needle)==1;s=s.replace(needle,test+'\n'+needle)
    needle="self.send_response(200);self.end_headers();self.wfile.write(probe.encode())"
    assert s.count(needle)==1
    s=s.replace(needle,"self.send_response(200);self.end_headers();self.wfile.write(pathlib.Path('scripts/chooser-live-test.py').read_bytes() if self.path=='/chooser-test.py' else probe.encode())")
    s=s.replace('for _ in range(360):','for _ in range(450):')
    s += "\nassert live.get('chooser_restart_pass'), 'FAIL final booted image chooser restart persistence'\n"
    ast.parse(s)
    for node in ast.parse(s).body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='probe' for t in node.targets):compile(ast.literal_eval(node.value),'guest-probe','exec')
    p.write_text(s)
print('PASS exact dock-count fix; ten original pins/icons unchanged; final guest restart assertion added')
