"""Only append Debian live persistence to live linux lines; preserve all other bytes."""
import os
import re
import stat
import tempfile
from pathlib import Path


def patch(data):
    lines = data.splitlines(keepends=True)
    count = 0
    for i, line in enumerate(lines):
        if re.match(rb'^\s*linux(?:efi|16)?\s', line) and re.search(rb'\bboot=live\b', line):
            assert not re.search(rb'\bpersistence(?:=|\b)', line), 'Unexpected preexisting persistence option'
            newline = b'\r\n' if line.endswith(b'\r\n') else b'\n' if line.endswith(b'\n') else b''
            body = line[:-len(newline)] if newline else line
            lines[i] = body + b' persistence' + newline
            count += 1
    assert count > 0, 'No live GRUB entries found'
    result = b''.join(lines)
    # Reverse exactly our insertion and require byte-for-byte boot structure preservation.
    restored = []
    for old, new in zip(data.splitlines(keepends=True), result.splitlines(keepends=True)):
        if old != new:
            newline = b'\r\n' if new.endswith(b'\r\n') else b'\n' if new.endswith(b'\n') else b''
            body = new[:-len(newline)] if newline else new
            assert body.endswith(b' persistence'), 'Unexpected GRUB mutation'
            restored.append(body[:-len(b' persistence')] + newline)
        else:
            restored.append(new)
    assert b''.join(restored) == data, 'GRUB structure changed'
    return result


def write_patched(path):
    path = Path(path)
    assert not path.is_symlink(), 'Refusing to replace a GRUB symlink'
    original = path.read_bytes()
    result = patch(original)
    mode = stat.S_IMODE(path.stat().st_mode)
    # Extracted GRUB files can be root-owned. Replace through the writable work
    # directory, rather than opening that inode for writing or loosening permissions.
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(result)
            out.flush()
            os.fsync(out.fileno())
            os.fchmod(out.fileno(), mode)
        assert path.read_bytes() == original, 'GRUB changed concurrently'
        os.replace(tmp, path)
        assert path.read_bytes() == result, 'Persistence GRUB write did not verify'
        assert stat.S_IMODE(path.stat().st_mode) == mode, 'GRUB mode changed'
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


if __name__ == '__main__':
    import sys
    write_patched(sys.argv[1])
    print('PASS only persistence appended to each live linux line')
