# -*- coding: utf-8 -*-
"""Recover Foxmail 7 saved passwords from Account.rec0 (local account recovery)."""
import os
import re
import sys

STORAGE = r'E:\Program Files\Foxmail 7.2\Storage'
OUT = r'C:\Users\xs0409\Desktop\fox_export\fox_pwd.txt'


def decrypt_v7(hash_password):
    v7_key = [0x7E, 0x46, 0x40, 0x37, 0x25, 0x6D, 0x24, 0x7E]  # ~F@7%m$~
    fc0 = 0x71
    size = len(hash_password) // 2
    b = [int(hash_password[i * 2 : (i + 1) * 2], 16) for i in range(size)]
    if not b:
        return ''
    c = [0] * len(b)
    c[0] = b[0] ^ fc0
    key = list(v7_key)
    while len(key) < len(b):
        key += v7_key
    d = [0] * len(b)
    for i in range(1, len(b)):
        d[i - 1] = b[i] ^ key[i - 1]
    e = []
    for i in range(len(d) - 1):
        temp = d[i] - c[i]
        if temp < 0:
            temp += 256
        e.append(temp)
    # first char chain: also need c[0] used; common impl joins e as password
    try:
        return ''.join(chr(x) for x in e if 32 <= x < 127)
    except Exception:
        return repr(e)


def extract_fields(data):
    """Extract ASCII key/value-ish fields from binary Account.rec0."""
    # Keep printable runs
    text = ''.join(chr(b) if 32 <= b < 127 else '\x00' for b in bytearray(data))
    parts = [p for p in text.split('\x00') if p]
    fields = {}
    interesting = (
        'Account',
        'POP3Account',
        'Password',
        'POP3Password',
        'SMTPPassword',
        'ESMTPPassword',
        'IMAPPassword',
        'SMTPHost',
        'POP3Host',
        'IMAPHost',
        'SMTPPort',
        'POP3Port',
        'IMAPPort',
        'SMTPUserName',
        'POP3UserName',
        'IMAPUserName',
        'Email',
        'MailAddress',
        'DisplayName',
    )
    # Key then next printable token often the value
    for i, p in enumerate(parts):
        if p in interesting and i + 1 < len(parts):
            val = parts[i + 1]
            # skip if next is also a key
            if val in interesting:
                continue
            fields.setdefault(p, []).append(val)
    # Also regex hex after Password labels in raw
    for label in (b'Password', b'POP3Password', b'SMTPPassword', b'ESMTPPassword', b'IMAPPassword'):
        idx = 0
        while True:
            j = data.find(label, idx)
            if j < 0:
                break
            k = j + len(label)
            # skip nulls
            while k < len(data) and data[k] == 0:
                k += 1
            hexchars = []
            while k < len(data) and chr(data[k]) in '0123456789abcdefABCDEF':
                hexchars.append(chr(data[k]))
                k += 1
            hx = ''.join(hexchars)
            if len(hx) >= 4 and len(hx) % 2 == 0:
                fields.setdefault(label.decode() + '_hex', []).append(hx)
            idx = j + 1
    return fields


def main():
    lines = []
    lines.append('=== Foxmail password recovery ===')
    if not os.path.isdir(STORAGE):
        lines.append('missing storage')
        open(OUT, 'wb').write('\n'.join(lines).encode('utf-8'))
        return
    for acc in sorted(os.listdir(STORAGE)):
        rec = os.path.join(STORAGE, acc, 'Accounts', 'Account.rec0')
        if not os.path.isfile(rec):
            # try alternate
            alt = os.path.join(STORAGE, acc, 'Account.rec0')
            rec = alt if os.path.isfile(alt) else None
        if not rec:
            continue
        data = open(rec, 'rb').read()
        lines.append('')
        lines.append('---- %s ----' % acc)
        lines.append('file %s size %s magic=0x%02x' % (rec, len(data), data[0] if data else 0))
        fields = extract_fields(data)
        for k in sorted(fields):
            for v in fields[k]:
                lines.append('  %s = %s' % (k, v))
                if k.endswith('_hex') or k in ('Password', 'POP3Password', 'SMTPPassword', 'ESMTPPassword', 'IMAPPassword'):
                    hx = v if re.fullmatch(r'[0-9a-fA-F]+', v) else None
                    if hx:
                        plain = decrypt_v7(hx)
                        lines.append('  DECRYPTED(%s) = %s' % (k, plain))
    open(OUT, 'wb').write('\n'.join(lines).encode('utf-8', 'replace'))
    # also print ascii-safe summary
    sys.stdout.buffer.write(open(OUT, 'rb').read())


if __name__ == '__main__':
    main()
