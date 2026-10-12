#!/usr/bin/env python3
"""Materialize only the authorized Chromium GUI/startup/updater repair."""
from pathlib import Path as P
import hashlib, json

d = json.loads(P('tests/chromium-diagnosis/38321280499/live-session.json').read_text())
assert 'not found' not in d['loader']['output']
for t in d['browser_trials']:
    assert t['state'] == 'running' and t['exit_code'] is None
    assert 'about:blank - Chromium' in t['windows']['output']
    print('EXACT FAILED ISO DIAGNOSIS', t['label'], t['elapsed_seconds'], t['exit_code'], repr(t['stdout_stderr']))
preserved = [p for base in ['desktop', 'branding'] for p in P(base).rglob('*') if p.is_file()]
preserved += [P('scripts/build-phase2.sh'), P('scripts/live-admin-network.py'), P('scripts/verify-phase2-boot.py')]
hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in preserved}
page = 'https://github.com/highitsave/nexium-os-releases'
updater = r'''#!/usr/bin/env python3
import json, os, subprocess, urllib.request, urllib.error
from pathlib import Path
PAGE = 'https://github.com/highitsave/nexium-os-releases'
API = 'https://api.github.com/repos/highitsave/nexium-os-releases/releases/latest'
def compare(local, release):
    tag = (release.get('tag_name') or release.get('name')) if release else None
    return {'status': 'no_releases' if not tag else 'current' if tag == local else 'update_available', 'current_version': local, 'latest_tag': tag, 'page': PAGE}
def main():
    try:
        local = Path('/etc/nexium-version').read_text().strip()
        request = urllib.request.Request(API, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Nexium-public-update-check'})
        try:
            with urllib.request.urlopen(request, timeout=12) as r:
                release = json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            release = None
        result = compare(local, release)
    except (OSError, ValueError, urllib.error.URLError) as e:
        result = {'status': 'unavailable', 'error': str(e), 'page': PAGE}
    print(json.dumps(result, indent=2), flush=True)
    if result['status'] == 'update_available' and '--notify' in __import__('sys').argv and os.environ.get('DISPLAY'):
        text = 'Nexium update available: ' + result['latest_tag'] + chr(10) + PAGE
        try:
            subprocess.run(['/usr/bin/zenity', '--info', '--title=Nexium update available', '--text=' + text, '--timeout=30'], timeout=35)
        except (OSError, subprocess.TimeoutExpired):
            pass
if __name__ == '__main__':
    main()
'''
compile(updater, 'update-check', 'exec')
ns = {}
exec(compile(updater, 'update-check', 'exec'), ns)
assert ns['compare']('x', None)['status'] == 'no_releases'
assert ns['compare']('x', {'tag_name': 'x'})['status'] == 'current'
assert ns['compare']('x', {'tag_name': 'y'})['status'] == 'update_available'
P('scripts/nexium-update-check').write_text(updater)
p = P('scripts/chromium-localhost.py')
s = p.read_text().replace('about:blank', page)
old = 'exec /opt/ungoogled-chromium/chrome --no-proxy-server'
assert s.count(old) == 1
s = s.replace(old, 'exec /opt/ungoogled-chromium/chrome', 1)
old = "assert '--no-proxy-server' in text and 'set -- " + page + "' in text"
assert old in s
s = s.replace(old, "assert 'set -- " + page + "' in text and '--no-sandbox' not in text and '--no-proxy-server' not in text", 1)
install = r'''
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
'''
needle = '    guard(root)' + chr(10) + '    tracked='
assert needle in s
s = s.replace(needle, install + needle, 1)
checks = '''    assert (root/'usr/local/bin/nexium-update-check').read_bytes() == P('scripts/nexium-update-check').read_bytes()
    assert (root/'etc/nexium-version').read_text().strip() == '1.2-golden-gate-phase2'
    for name in ['etc/xdg/autostart/nexium-update-check.desktop', 'usr/share/applications/nexium-update-check.desktop']:
        assert 'Exec=/usr/local/bin/nexium-update-check --notify' in (root/name).read_text()
    for base in ['etc/skel', 'home/nexium']:
        prefs = json.loads((root/base/'.config/chromium/Default/Preferences').read_text())
        assert prefs['homepage'] == 'https://github.com/highitsave/nexium-os-releases'
        assert prefs['session']['startup_urls'] == ['https://github.com/highitsave/nexium-os-releases']
    print('PASS public update checker/version/autostart/startup; no credentials', flush=True)
'''
needle = 'def verify(root):' + chr(10)
assert needle in s
s = s.replace(needle, needle + checks, 1)
compile(s, str(p), 'exec')
p.write_text(s)
p = P('scripts/capture-dock-cream.py')
s = p.read_text()
start = s.index("browser_log=open('/tmp/nexium-browser.log','w')")
end = s.index("data['commands']=[command(c) for c in commands]", start)
probe = r'''import time, re, shlex
data['browser_runtime'] = {k: os.environ.get(k) for k in ['HOME','DISPLAY','XDG_RUNTIME_DIR']}
data['browser_ldd'] = command('ldd /opt/ungoogled-chromium/chrome')
data['browser_paths'] = command('ls -ld "$HOME" "$XDG_RUNTIME_DIR" /dev/shm; df -h /dev/shm')
text = open('/usr/share/applications/nexium-browser.desktop').read()
argv = shlex.split(next(line[5:] for line in text.splitlines() if line.startswith('Exec=')))
log_path = '/tmp/nexium-browser.log'
browser_log = open(log_path, 'w')
browser = subprocess.Popen(argv, stdout=browser_log, stderr=subprocess.STDOUT)
began = time.monotonic()
data['browser_timeline'] = []
data['browser_processes'] = []
data['browser_windows'] = []
while time.monotonic() - began < 150:
    processes = []
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            cmd = [part.decode() for part in open('/proc/'+pid+'/cmdline','rb').read().split(bytes([0])) if part]
        except (OSError, UnicodeError):
            continue
        if cmd and cmd[0] == '/opt/ungoogled-chromium/chrome' and not any(c.startswith('--type=') for c in cmd):
            processes.append({'pid':pid, 'argv':cmd})
    tree = command('xwininfo -root -tree')
    windows = []
    for line in tree['output'].splitlines():
        m = re.search(r'(0x[0-9a-f]+) "([^"]*)": .*?(\d+)x(\d+)', line)
        if not m or 'Chromium' not in m[2] or int(m[3]) < 100 or int(m[4]) < 100:
            continue
        view = command('xwininfo -id ' + m[1])
        if view['exit'] == 0 and 'Map State: IsViewable' in view['output']:
            windows.append({'id':m[1], 'title':m[2], 'view':view})
    rc = browser.poll()
    data['browser_timeline'].append({'seconds':round(time.monotonic()-began,3),'exit':rc,'processes':processes,'windows':len(windows)})
    data['browser_processes'] = processes
    data['browser_windows'] = windows
    data['browser_window_tree'] = tree
    if (processes and windows) or rc is not None:
        break
    time.sleep(2)
browser_log.flush()
data['browser_launch'] = {'dock_exec':argv,'pid':browser.pid,'exit_code':browser.poll(),'seconds':round(time.monotonic()-began,3),'stdout_stderr':open(log_path).read()}
data['browser_gui_pass'] = bool(data['browser_processes'] and data['browser_windows']) and browser.poll() is None and 'not found' not in data['browser_ldd']['output']
data['browser_log'] = command('cat ' + log_path)
data['update_check'] = command('/usr/local/bin/nexium-update-check')
data['image_version'] = command('cat /etc/nexium-version')
print('REAL CHROMIUM GUI', json.dumps({k:v for k,v in data.items() if k.startswith('browser_')}, indent=2), flush=True)
'''
s = s[:start] + probe + s[end:]
needle = 'for _ in range(60):' + chr(10) + '        if (O/'
assert needle in s
s = s.replace(needle, 'for _ in range(180):' + chr(10) + '        if (O/', 1)
old = "assert live.get('browser_processes'),'FAIL: normal-user direct about:blank Chromium process not observed'"
assert old in s
s = s.replace(old, "assert live.get('browser_gui_pass'),'FAIL: dock Chromium GUI; exit/stdout/stderr/loader/window timeline printed above'", 1)
compile(s, str(p), 'exec')
p.write_text(s)
for path, digest in hashes.items():
    assert hashlib.sha256(P(path).read_bytes()).hexdigest() == digest, path
P('tests/chromium-gui-repair.md').write_text('Exact failed ISO diagnosis 38321280499: direct and dock opened GUI windows and ran after 60 seconds, with no missing loader libraries. No speculative runtime packages or no-sandbox flags. Original failure cause remains unestablished; bounded 150s actual dock GUI/process poll with real exit/stdout/stderr replaces 12s snapshot. Public releases startup and token-free API updater use /etc/nexium-version=1.2-golden-gate-phase2; 404=no_releases, offline=unavailable, differing tag=nonblocking update notice. Policy/initial_preferences/localhost assertions unchanged. Desktop, branding, sudo, network, build and preservation source hashes unchanged. No release/email.' + chr(10))
print('PASS authorized source repair; original policy guards and other source preserved')
