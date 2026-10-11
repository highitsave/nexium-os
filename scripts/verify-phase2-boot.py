 | tee reports/verification.txt
import pathlib, hashlib, re, json, os, subprocess
P=pathlib.Path
a,b=P('work/original'),P('work/final')
old=P('reports/original-boot.txt').read_text(); new=P('reports/final-boot.txt').read_text()
def schema(text):
    result=[]
    for line in text.splitlines():
        if ':' not in line: continue
        k,v=line.split(':',1); k=k.strip(); v=v.split()
        if k in ['System area summary','El Torito cat path','El Torito img path','El Torito img opts']: result.append((k,v))
        elif k=='El Torito boot img': result.append((k,v[:-1]))
    return result
assert schema(old) and schema(old)==schema(new), 'Original boot schema not reproduced'
assert 'grub2-mbr' in new and 'BIOS' in new and 'UEFI' in new
assert 'NEXIUM_OS' in new
def rows(text, key):
    return [line.split(':',1)[1].split() for line in text.splitlines() if line.split(':',1)[0].strip()==key]
assert rows(old,'System area options')==rows(new,'System area options')
assert [r[:3] for r in rows(old,'MBR partition')]==[r[:3] for r in rows(new,'MBR partition')], 'MBR partition flags/types changed'
def rawpart(path, offset, size):
    with P(path).open('rb') as f:
        f.seek(offset); data=f.read(size)
    assert len(data)==size
    return data
oi,ni=rows(old,'El Torito boot img'),rows(new,'El Torito boot img')
oe,ne=[r for r in oi if r[1]=='UEFI'],[r for r in ni if r[1]=='UEFI']
assert len(oe)==len(ne)==1
efi0=rawpart('work/orig.iso',int(oe[0][-1])*2048,int(oe[0][-2])*512)
efi1=rawpart('output/nexium-os-1.2-ungoogled-amd64.iso',int(ne[0][-1])*2048,int(ne[0][-2])*512)
assert efi0==efi1, 'UEFI boot payload changed'
print('EFI payload: byte-identical;',len(efi1),'bytes; SHA256',hashlib.sha256(efi1).hexdigest())
cat0=bytearray(rawpart('work/orig.iso',int(rows(old,'El Torito catalog')[0][0])*2048,2048))
cat1=bytearray(rawpart('output/nexium-os-1.2-ungoogled-amd64.iso',int(rows(new,'El Torito catalog')[0][0])*2048,2048))
assert len(oi)==len(ni)==2
for pos,o,n in zip([32,96],oi,ni):
    assert int.from_bytes(cat0[pos+8:pos+12],'little')==int(o[-1])
    assert int.from_bytes(cat1[pos+8:pos+12],'little')==int(n[-1])
    cat0[pos+8:pos+12]=bytes(4); cat1[pos+8:pos+12]=bytes(4)
assert cat0==cat1, 'Boot catalog changed beyond required LBA relocation'
print('El Torito catalog: identical except required BIOS/UEFI LBA relocation')
print('System area: MBR grub2-mbr cyl-align-off; original system-area options and MBR partition flags/types unchanged')
orig=rawpart('work/orig.iso',0,32768)
final=rawpart('output/nexium-os-1.2-ungoogled-amd64.iso',0,32768)
assert orig[:432]==final[:432], 'Original hybrid MBR boot code changed'
with P('output/nexium-os-1.2-ungoogled-amd64.iso').open('rb') as f:
    f.seek(16*2048); pvd=f.read(2048)
assert pvd[:7]==b'\x01CD001\x01' and pvd[40:72].decode().strip()=='NEXIUM_OS'
originals={p.relative_to(a):p for p in a.rglob('*') if p.is_file()}
rebuilt={p.relative_to(b):p for p in b.rglob('*') if p.is_file()}
assert originals.keys()==rebuilt.keys()
bootpaths=[P('/'+v.split(':',1)[1].split()[-1].lstrip('/')) for v in old.splitlines() if v.startswith('El Torito img path')]
for name,p in originals.items():
    if name.suffix=='.squashfs' or name.name in ['boot.catalog','boot.cat']: continue
    x,y=p.read_bytes(),rebuilt[name].read_bytes()
    if x!=y:
        assert P('/'+str(name)) in bootpaths, 'Unexpected payload change: '+str(name)
        for start,end in [(8,64),(2548,2556)]:
            x=x[:start]+bytes(end-start)+x[end:]; y=y[:start]+bytes(end-start)+y[end:]
        assert x==y, 'Boot image differs beyond required address/checksum patches: '+str(name)
        print('Boot address/checksum relocation only:',name)
for n in ['live/vmlinuz','live/initrd.img','boot/grub/grub.cfg']:
    assert originals[P(n)].read_bytes()==rebuilt[P(n)].read_bytes()
    print('UNCHANGED:', '/'+n)
print('VALID ISO9660: NEXIUM_OS; original boot catalog, BIOS/UEFI and GRUB2 isohybrid MBR structure verified; original MBR boot code identical')
