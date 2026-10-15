"""Remove nopersistence veto, append persistence; preserve all other GRUB bytes."""
import os, pathlib, re, tempfile

def patch(data):
    lines = data.splitlines(keepends=True); changed = 0
    for i, line in enumerate(lines):
        if not (re.match(rb"^\s*linux(?:efi|16)?\s", line) and b"boot=live" in line.split()): continue
        tokens = line.split()
        assert not (b"persistence" in tokens and b"nopersistence" in tokens), "FAIL conflicting persistence and nopersistence in GRUB"
        assert b"persistence" not in tokens, "Unexpected preexisting persistence option"
        assert not any(t.startswith(b"persistence=") for t in tokens), "Unexpected persistence option"
        newline = b"\r\n" if line.endswith(b"\r\n") else b"\n" if line.endswith(b"\n") else b""
        body = line[:-len(newline)] if newline else line
        matches = list(re.finditer(rb"[ \t]+nopersistence(?=[ \t]|$)", body))
        assert len(matches) == tokens.count(b"nopersistence"), "FAIL non-token-safe nopersistence removal"
        clean = re.sub(rb"[ \t]+nopersistence(?=[ \t]|$)", b"", body)
        restored = clean
        for m in matches: restored = restored[:m.start()] + m.group() + restored[m.start():]
        assert restored == body, "FAIL GRUB bytes changed beyond veto token removal"
        lines[i] = clean + b" persistence" + newline
        assert lines[i].split().count(b"persistence") == 1 and b"nopersistence" not in lines[i].split(), "FAIL ambiguous final GRUB persistence tokens"
        changed += 1
    assert changed > 0, "No live GRUB entries found"
    return b"".join(lines)

if __name__ == "__main__":
    import sys
    path = pathlib.Path(sys.argv[1]); original = path.read_bytes(); result = patch(original)
    mode = path.stat().st_mode & 0o7777
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(result); out.flush(); os.fsync(out.fileno()); os.fchmod(out.fileno(), mode)
        assert path.read_bytes() == original, "GRUB changed concurrently"
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    assert path.read_bytes() == result and path.stat().st_mode & 0o7777 == mode
    print("PASS only nopersistence veto removed and persistence appended; every other GRUB byte preserved")
