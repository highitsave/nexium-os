import sys,json,subprocess
from pathlib import Path
from PIL import Image,ImageStat
root=Path(sys.argv[1]);live=json.loads((root/'live-session.json').read_text())
print('NEXIUM STDOUT/STDERR BEGIN',flush=True)
print(live.get('browser_launch',{}).get('stdout_stderr','<no browser report>'),flush=True)
print('NEXIUM STDOUT/STDERR END',flush=True)
assert live.get('browser_gui_pass'), 'FAIL browser_gui_pass is false; no usable real browser window'
assert live.get('browser_processes'), 'FAIL browser process identity'
windows=live.get('browser_windows',[])
assert windows and all(w['width']>=900 and w['height']>=600 for w in windows), 'FAIL real window geometry'
im=Image.open(root/'browser-window.png').convert('RGB')
colors=len(im.resize((160,100)).getcolors(16000) or [])
variance=sum(ImageStat.Stat(im).var)
ocr=subprocess.run(['tesseract',str(root/'browser-window.png'),'stdout'],capture_output=True,text=True,check=True).stdout
report={'browser_gui_pass':True,'windows':windows,'screenshot_width':im.width,'screenshot_height':im.height,'sample_colors':colors,'pixel_variance_sum':variance,'ocr':ocr,'paint_pass':im.width>=900 and im.height>=600 and colors>=20 and variance>50 and 'Nexium' in ocr,'plank_running':live.get('plank_running'),'sudo_exit':live.get('sudo_noninteractive',{}).get('exit')}
(root/'browser-paint.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
assert report['paint_pass'],'FAIL real browser pixels/geometry/paint OCR'
assert live.get('plank_running') and live.get('sudo_noninteractive',{}).get('exit')==0
print('PASS REAL NEXIUM PAINT: mapped normal-size PID-owned X11 window, nonblank pixels and Nexium OCR',flush=True)
