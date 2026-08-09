# -*- coding: utf-8 -*-
import os
import re
import struct
import sys

STORAGE = r'E:\Program Files\Foxmail 7.2\Storage'
OUT = r'C:\Users\xs0409\Desktop\fox_export\fox_pwd.txt'


def decrypt_v7(h):
    h = re.sub(r'[^0-9a-fA-F]', '', h)
    key = bytearray(b'~F@7%m$~')
    b = bytearray.fromhex(h)
    if len(b) < 2:
        return ''
    s = sum(key) % 255
    c0 = s ^ b[0]
    d = bytearray(b[i + 1] ^ key[i % len(key)] for i in range(len(b) - 1))
    e = bytearray()
    for i in range(len(d)):
        ci = c0 if i == 0 else b[i]
        if d[i] < ci:
            e.append((0x100 - ci + d[i]) & 0xFF)
        else:
            e.append(d[i] - ci)
    try:
        return e.decode('utf-8')
    except Exception:
        return ''.join(chr(x) for x in e if 32 <= x < 127)


def parse_rec0(data):
    results = []
    keys = [
        'Password',
        'Account',
        'Email',
        'SMTPHost',
        'POP3Host',
        'IMAPHost',
        'SMTPUserName',
        'POP3UserName',
        'IMAPUserName',
        'SMTPPassword',
        'POP3Password',
        'ESMTPPassword',
        'IMAPPassword',
        'DisplayName',
    ]
    for key in keys:
        kb = key.encode('ascii')
        start = 0
        while True:
            p = data.find(kb, start)
            if p < 0:
                break
            q = p + len(kb)
            if q >= len(data) or data[q] != 0:
                start = p + 1
                continue
            q += 1
            if q + 8 > len(data) or data[q : q + 4] != b'\x01\x00\x00\x00':
                start = p + 1
                continue
            ln = struct.unpack_from('<I', data, q + 4)[0]
            if ln > 500 or q + 8 + ln > len(data):
                start = p + 1
                continue
            val = data[q + 8 : q + 8 + ln]
            if val.endswith(b'!'):
                val = val[:-1]
            results.append((key, val))
            start = p + 1
    return results


def main():
    lines = ['=== Foxmail passwords (ryoii alg) ===']
    for acc in sorted(os.listdir(STORAGE)):
        rec = os.path.join(STORAGE, acc, 'Accounts', 'Account.rec0')
        if not os.path.isfile(rec):
            continue
        data = open(rec, 'rb').read()
        lines.append('')
        lines.append('==== %s ====' % acc)
        seen = set()
        for key, val in parse_rec0(data):
            try:
                s = val.decode('ascii')
            except Exception:
                s = repr(val)
            item = (key, s)
            if item in seen:
                continue
            seen.add(item)
            if 'Password' in key and re.fullmatch(r'[0-9A-Fa-f]+', s or ''):
                plain = decrypt_v7(s)
                lines.append('  %s => %s' % (key, plain))
            elif len(s) < 120:
                lines.append('  %s: %s' % (key, s))
    blob = '\n'.join(lines).encode('utf-8', 'replace')
    open(OUT, 'wb').write(blob)
    sys.stdout.buffer.write(blob)


if __name__ == '__main__':
    main()
