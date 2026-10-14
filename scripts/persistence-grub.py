"""Only add Debian live persistence to linux boot=live lines; no other GRUB edit."""
import re
from pathlib import Path
def patch(data):
    lines=data.decode().splitlines(keepends=True);count=0
    for i,line in enumerate(lines):
        if re.match(r'^\s*linux(?:efi|16)?\s',line) and re.search(r'\bboot=live\b',line):
            assert not re.search(r'\bpersistence(?:=|\b)',line),'Unexpected preexisting persistence option'
            newline='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
            body=line[:-len(newline)] if newline else line
            lines[i]=body+' persistence'+newline;count+=1
    assert count>0,'No live GRUB entries found'
    return ''.join(lines).encode()
if __name__=='__main__':
    import sys
    p=Path(sys.argv[1]);p.write_bytes(patch(p.read_bytes()))
    print('PASS only persistence appended to each live linux line')
