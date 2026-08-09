# -*- coding: utf-8 -*-
import os, re, sys

STORAGE = r'E:\Program Files\Foxmail 7.2\Storage'
OUT = r'C:\Users\xs0409\Desktop\fox_export\fox_pwd.txt'


def decrypt_v7(h):
    """Foxmail v7 password decrypt (~F@7%m$~, init 0x71)."""
    h = re.sub(r'[^0-9a-fA-F]', '', h)
    if len(h) < 4 or len(h) % 2:
        return ''
    key = bytearray(b'~F@7%m$~')
    b = bytearray.fromhex(h)
    out = bytearray()
    # Algorithm from multiple public recoveries:
    # first = enc[0] ^ 0x71
    # for i in 1..n-1: out[i-1] = (enc[i] ^ key[i-1]) - first  (mod 256)  -- NO
    # From https://github.com/ryoii and CSDN ports:
    fc0 = 0x71
    c0 = b[0] ^ fc0
    # expand key
    ek = bytearray()
    while len(ek) < len(b):
        ek += key
    d = bytearray()
    for i in range(1, len(b)):
        d.append(b[i] ^ ek[i - 1])
    # e[i] = d[i] - c[i], c[0]=c0, c[i]=b[i] for i>=1  (CSDN)
    e = bytearray()
    for i in range(len(d)):
        ci = c0 if i == 0 else b[i]
        t = d[i] - ci
        if t < 0:
            t += 256
        e.append(t)
    # Also try: all subtract c0
    e2 = bytearray((d[i] - c0) % 256 for i in range(len(d)))
    # Also try chained
    e3 = bytearray()
    prev = c0
    for i in range(len(d)):
        t = (d[i] - prev) % 256
        e3.append(t)
        prev = t

    def as_str(bb):
        try:
            s = bb.decode('utf-8')
            if all(32 <= ord(c) < 127 or ord(c) > 127 for c in s) and bb:
                return s
        except Exception:
            pass
        return ''.join(chr(x) for x in bb if 32 <= x < 127)

    return as_str(e), as_str(e2), as_str(e3), e.hex(), e2.hex()


def extract_hex_after(data, label):
    res = []
    start = 0
    lab = label.encode('ascii')
    while True:
        j = data.find(lab, start)
        if j < 0:
            break
        k = j + len(lab)
        while k < len(data) and data[k] == 0:
            k += 1
        hx = []
        while k < len(data) and chr(data[k]) in '0123456789abcdefABCDEF':
            hx.append(chr(data[k]))
            k += 1
        s = ''.join(hx)
        if len(s) >= 4 and len(s) % 2 == 0:
            res.append((j, s))
        start = j + 1
    return res


def extract_ascii_after(data, label):
    res = []
    start = 0
    lab = label.encode('ascii')
    while True:
        j = data.find(lab, start)
        if j < 0:
            break
        k = j + len(lab)
        while k < len(data) and data[k] == 0:
            k += 1
        val = []
        while k < len(data) and 32 <= data[k] < 127:
            val.append(chr(data[k]))
            k += 1
        s = ''.join(val).strip()
        if s and s not in ('Password', 'Account', 'Email'):
            res.append((j, s))
        start = j + 1
    return res


lines = ['=== Foxmail pwd ===']
for acc in sorted(os.listdir(STORAGE)):
    rec = os.path.join(STORAGE, acc, 'Accounts', 'Account.rec0')
    if not os.path.isfile(rec):
        continue
    data = open(rec, 'rb').read()
    lines.append('')
    lines.append('==== %s ====' % acc)
    for lab in ('Email', 'Account', 'SMTPHost', 'POP3Host', 'IMAPHost', 'SMTPUserName', 'POP3UserName'):
        vals = extract_ascii_after(data, lab)
        seen = set()
        for off, s in vals:
            if s in seen:
                continue
            seen.add(s)
            if len(s) < 80:
                lines.append('  %s: %s' % (lab, s))
    for lab in ('Password', 'POP3Password', 'SMTPPassword', 'ESMTPPassword', 'IMAPPassword'):
        vals = extract_hex_after(data, lab)
        seen = set()
        for off, s in vals:
            if s in seen:
                continue
            seen.add(s)
            lines.append('  %s hex@%d: %s' % (lab, off, s))
            p1, p2, p3, h1, h2 = decrypt_v7(s)
            lines.append('    decrypt1: %r' % p1)
            lines.append('    decrypt2: %r' % p2)
            lines.append('    decrypt3: %r' % p3)

open(OUT, 'wb').write('\n'.join(lines).encode('utf-8', 'replace'))
sys.stdout.buffer.write(open(OUT, 'rb').read())
