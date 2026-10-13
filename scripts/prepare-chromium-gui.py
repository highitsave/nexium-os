#!/usr/bin/env python3
"""Validate landed product fixes and repair the evidenced process-identification bug."""
from pathlib import Path as P
import ast, hashlib, json
page = 'https://github.com/highitsave/nexium-os-releases'
api = 'https://api.github.com/repos/highitsave/nexium-os-releases/releases/latest'
updater = P('scripts/nexium-update-check').read_text()
assert api in updater and page in updater
assert 'Authorization' not in updater and 'github.token' not in updater
ns = {'__name__': 'checker_tests'}
exec(compile(updater, 'update-check', 'exec'), ns)
assert ns['compare']('x', None)['status'] == 'no_releases'
assert ns['compare']('x', {'tag_name': 'x'})['status'] == 'current'
assert ns['compare']('x', {'tag_name': 'y'})['status'] == 'update_available'
prefs = P('scripts/chromium-localhost.py').read_text()
assert page in prefs and '1.2-golden-gate-phase2' in prefs
assert 'assert not forbidden' in prefs and 'assert not bad' in prefs
assert 'initial_preferences' in prefs and '127' in prefs and 'localhost' in prefs
preserved = [p for base in ['desktop', 'branding'] for p in P(base).rglob('*') if p.is_file()]
preserved += [P('scripts/build-phase2.sh'), P('scripts/live-admin-network.py'), P('scripts/verify-phase2-boot.py'), P('scripts/chromium-localhost.py'), P('scripts/nexium-update-check')]
hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in preserved}
p = P('scripts/capture-dock-cream.py')
s = p.read_text()
marker = '# NEXIUM_EXE_PID_GUI_PROBE'
if marker not in s:
    start = s.index('    processes = []\n    for pid in os.listdir')
    end = s.index("    tree = command('xwininfo -root -tree')", start)
    replacement = r'''    # NEXIUM_EXE_PID_GUI_PROBE: executable identity, launch PID, UID, real mapped window.
    processes = []
    proc = '/proc/' + str(browser.pid)
    observed = {'pid': browser.pid, 'launch_poll': browser.poll(), 'uid': os.getuid()}
    try:
        raw = open(proc + '/cmdline', 'rb').read()
        cmd = [part.decode(errors='replace') for part in raw.split(bytes([0])) if part]
        exe = os.readlink(proc + '/exe')
        status = open(proc + '/status').read()
        uid = int(next(line.split()[1] for line in status.splitlines() if line.startswith('Uid:')))
        observed.update({'exe': exe, 'argv': cmd, 'raw_cmdline_repr': repr(raw), 'process_uid': uid})
        expected_exe = os.path.realpath('/opt/ungoogled-chromium/chrome')
        if os.path.realpath(exe) == expected_exe and uid == os.getuid() and uid != 0 and browser.poll() is None and not any(c.startswith('--type=') or c == '--no-sandbox' for c in cmd):
            processes.append(observed)
    except (OSError, ValueError, StopIteration) as e:
        observed['proc_error'] = repr(e)
    data['browser_proc_observed'] = observed
'''
    s = s[:start] + replacement + s[end:]
    old = "        if view['exit'] == 0 and 'Map State: IsViewable' in view['output']:\n            windows.append({'id':m[1], 'title':m[2], 'view':view})"
    new = """        owner = command('xprop -id ' + m[1] + ' _NET_WM_PID')
        match = re.search(r'=\\s*(\\d+)', owner['output'])
        window_pid = int(match[1]) if match else None
        if view['exit'] == 0 and 'Map State: IsViewable' in view['output'] and window_pid == browser.pid:
            windows.append({'id':m[1], 'title':m[2], 'view':view, 'owner':owner, 'pid':window_pid})"""
    assert old in s
    s = s.replace(old, new, 1)
    old = "    data['browser_timeline'].append({'seconds':round(time.monotonic()-began,3),'exit':rc,'processes':processes,'windows':len(windows)})"
    assert old in s
    s = s.replace(old, "    data['browser_timeline'].append({'seconds':round(time.monotonic()-began,3),'exit':rc,'processes':processes,'observed':observed,'windows':len(windows)})", 1)
    old = "data['browser_gui_pass'] = bool(data['browser_processes'] and data['browser_windows']) and browser.poll() is None and 'not found' not in data['browser_ldd']['output']"
    assert old in s
    s = s.replace(old, old + " and data['browser_ldd']['exit'] == 0", 1)
    needle = "assert live.get('browser_gui_pass'),"
    assert needle in s
    s = s.replace(needle, "print('CHROMIUM STDOUT/STDERR BEGIN', flush=True)\nprint(live.get('browser_launch', {}).get('stdout_stderr', '<no guest report>'), flush=True)\nprint('CHROMIUM STDOUT/STDERR END', flush=True)\n" + needle, 1)
    compile(s, str(p), 'exec')
    tree = ast.parse(s)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'probe' for t in node.targets):
            compile(ast.literal_eval(node.value), 'guest-probe', 'exec')
    p.write_text(s)
for path, digest in hashes.items():
    assert hashlib.sha256(P(path).read_bytes()).hexdigest() == digest, path
P('tests/chromium-gui-repair.md').write_text('Run 38323442490 failed capture line142 because browser_processes was empty, despite PID652 still running and mapped Chromium window0x1600003 on the releases page. Loader had no missing libraries. Repair identifies the actual dock launch PID by /proc/PID/exe and non-root UID, requires mapped Chromium window whose _NET_WM_PID equals launch PID, ldd exit0/no missing libs, and running main process without --no-sandbox. Raw cmdline/exe/UID and real stdout/stderr remain diagnostics. No assertion weakened or speculative dependencies added. Startup/public API updater, policy/initial_preferences/localhost guards, X11 dock/libglib, cream regenerated initrd, sudo, Wi-Fi firmware and boot preservation source remain untouched. No release/email.\n')
print('PASS PID/executable/UID/mapped-window repair; product sources and preservation hashes unchanged')
