
# -*- coding: utf-8 -*-
import os, re, sys

STORAGE = r'E:\Program Files\Foxmail 7.2\Storage'
OUT = r'C:\Users\xs0409\Desktop\fox_export\fox_pwd.txt'

def decrypt_v7(hash_password):
    hash_password = re.sub(r'[^0-9a-fA-F]', '', hash_password)
    if len(hash_password) < 4 or len(hash_password) % 2:
        return None
    v7_key = [0x7E, 0x46, 0x40, 0x37, 0x25, 0x6D, 0x24, 0x7E]
    fc0 = 0x71
    size = len(hash_password) // 2
    b = [int(hash_password[i*2:(i+1)*2], 16) for i in range(size)]
    c0 = b[0] ^ fc0
    key = (v7_key * ((size // len(v7_key)) + 2))[:size]
    d = [0]*(size-1)
    for i in range(1, size):
        d[i-1] = b[i] ^ key[i-1]
    e = []
    # c chain: c[0]=c0, then typically use previous plaintext? 
    # From common foxmail_password_recovery: e[i] = d[i] - c[i], c[i]=b[i]? Wait use published:
    c = [0]*size
    c[0] = c0
    for i in range(1, size):
        c[i] = b[i]  # as in some snippets - actually wrong
    # Correct from lainzy/securityxploded style used by ryoii:
    # e[i] = (d[i] - c[i]) mod 256 where c[0]=b[0]^0x71 and for i>0 c[i]=b[i]? 
    # Looking at CSDN again: c[0]=b[0]^fc0; then for i in 1..len: c[i]=b[i]  -- they set all c[i]=b[i] for i>=1
    # e[i] = d[i]-c[i]
    e = []
    for i in range(len(d)):
        # c[i] for i==0 is c0; for i>=1 the CSDN uses c[i] which was set to b[i] only in first loop incorrectly
        ci = c0 if i == 0 else b[i]
        # Wait CSDN: for i in range(len(d)-1): temp = d[i]-c[i] with c[0]=c0 and c[i]=b[i] for i>=1
        pass
    c = [0]*size
    c[0] = c0
    for i in range(1, size):
        c[i] = b[i]
    e=[]
    for i in range(len(d)):
        if i >= len(c): break
        temp = d[i] - c[i]
        if temp < 0: temp += 256
        e.append(temp)
    # Actually standard ryoii algorithm from deepwiki/source:
    # I'll implement both variants
    plain1 = ''.join(chr(x) for x in e if 0 < x < 256)
    # Variant 2: c grows with previous e
    e2=[]
    prev=c0
    for i in range(len(d)):
        temp = d[i] - prev
        if temp < 0: temp += 256
        e2.append(temp)
        prev = temp
    plain2 = ''.join(chr(x) for x in e2 if 0 < x < 256)
    # Variant 3 from some blogs: 
    # ch = (encrypted[i+1] ^ key[i]) - (encrypted[0] ^ 0x5A) for v6; v7 first xor 0x71
    e3=[]
    for i in range(len(d)):
        temp = d[i] - c0
        if temp < 0: temp += 256
        e3.append(temp)
    plain3 = ''.join(chr(x) for x in e3 if 0 < x < 256)
    return plain1, plain2, plain3

def find_labeled_hex(data):
    labels = [b'Password', b'POP3Password', b'SMTPPassword', b'ESMTPPassword', b'IMAPPassword',
              b'Account', b'Email', b'SMTPHost', b'POP3Host', b'IMAPHost', b'SMTPUserName', b'POP3UserName']
    found=[]
    for lab in labels:
        start=0
        while True:
            j=data.find(lab, start)
            if j<0: break
            # ensure word boundary-ish: prev byte null or non-alpha
            if j>0 and 65 <= data[j-1] <= 122:
                start=j+1; continue
            k=j+len(lab)
            while k < len(data) and data[k]==0:
                k+=1
            # collect value
            val=bytearray()
            while k < len(data) and 32 <= data[k] < 127:
                val.append(data[k]); k+=1
            s=val.decode('ascii','replace').strip()
            # trim trailing punctuation junk
            if lab.endswith(b'Password') or lab==b'Password':
                m=re.match(r'^([0-9A-Fa-f]+)', s)
                s=m.group(1) if m else s
            if s:
                found.append((lab.decode(), j, s))
            start=j+1
    return found

lines=[]
lines.append('=== Foxmail password recovery v2 ===')
for acc in sorted(os.listdir(STORAGE)):
    rec=os.path.join(STORAGE,acc,'Accounts','Account.rec0')
    if not os.path.isfile(rec):
        continue
    data=open(rec,'rb').read()
    lines.append('')
    lines.append('==== %s (magic=0x%02x size=%d) ====' % (acc, data[0], len(data)))
    items=find_labeled_hex(data)
    seen=set()
    for lab, off, s in items:
        key=(lab,s)
        if key in seen: continue
        seen.add(key)
        lines.append('  [%s] @%d = %s' % (lab, off, s))
        if 'Password' in lab and re.fullmatch(r'[0-9A-Fa-f]+', s):
            p1,p2,p3 = decrypt_v7(s)
            lines.append('    try1: %r' % p1)
            lines.append('    try2: %r' % p2)
            lines.append('    try3: %r' % p3)

open(OUT,'wb').write('\n'.join(lines).encode('utf-8','replace'))
sys.stdout.buffer.write(open(OUT,'rb').read())
