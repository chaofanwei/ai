
# -*- coding: utf-8 -*-
import ctypes, time, os, sys, glob, shutil
from ctypes import wintypes

LOG = r'C:\Users\xs0409\Desktop\fox_export\export_log3.txt'
OUT_DIR = r'C:\Users\xs0409\Desktop\fox_export'
logf = open(LOG, 'wb')

def log(m):
    if not isinstance(m, bytes):
        m = (m + '\n').encode('utf-8', 'replace')
    else:
        m = m + b'\n'
    logf.write(m); logf.flush()

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
EnumWindows = user32.EnumWindows
EnumChildWindows = user32.EnumChildWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
IsWindowVisible = user32.IsWindowVisible
SetForegroundWindow = user32.SetForegroundWindow
ShowWindow = user32.ShowWindow
GetClassNameW = user32.GetClassNameW
GetWindowRect = user32.GetWindowRect
SendMessageW = user32.SendMessageW
PostMessageW = user32.PostMessageW
keybd_event = user32.keybd_event
mouse_event = user32.mouse_event
SetCursorPos = user32.SetCursorPos
IsWindowEnabled = user32.IsWindowEnabled

WM_SETTEXT = 0x000C
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102
BM_CLICK = 0x00F5
VK_CONTROL=0x11; VK_SHIFT=0x10; VK_RETURN=0x0D; VK_ESCAPE=0x1B; VK_DOWN=0x28
KEYEVENTF_KEYUP=2
SW_MAXIMIZE=3

class RECT(ctypes.Structure):
    _fields_=[('left',ctypes.c_long),('top',ctypes.c_long),('right',ctypes.c_long),('bottom',ctypes.c_long)]

def title(hwnd):
    n=GetWindowTextLengthW(hwnd)
    b=ctypes.create_unicode_buffer(n+1)
    GetWindowTextW(hwnd,b,n+1)
    return b.value

def klass(hwnd):
    b=ctypes.create_unicode_buffer(256)
    GetClassNameW(hwnd,b,256)
    return b.value

def rect(hwnd):
    r=RECT(); GetWindowRect(hwnd, ctypes.byref(r)); return r

def list_top():
    out=[]
    def cb(h,l):
        if IsWindowVisible(h):
            out.append((h, klass(h), title(h)))
        return True
    EnumWindows(EnumWindowsProc(cb),0)
    return out

def list_children(parent, depth=0, max_depth=4):
    out=[]
    def cb(h,l):
        out.append((h, klass(h), title(h), rect(h)))
        return True
    EnumChildWindows(parent, EnumWindowsProc(cb), 0)
    return out

def press(vk, down=True):
    keybd_event(vk,0,0 if down else KEYEVENTF_KEYUP,0)

def tap(vk, delay=0.08):
    press(vk,True); time.sleep(0.03); press(vk,False); time.sleep(delay)

def chord(vks, hold=0.05):
    for v in vks: press(v,True); time.sleep(0.02)
    time.sleep(hold)
    for v in reversed(vks): press(v,False); time.sleep(0.02)

def type_unicode(s):
    INPUT_KEYBOARD=1; KEYEVENTF_UNICODE=4; KEYEVENTF_KEYUP_U=2
    class KEYBDINPUT(ctypes.Structure):
        _fields_=[('wVk',wintypes.WORD),('wScan',wintypes.WORD),('dwFlags',wintypes.DWORD),('time',wintypes.DWORD),('dwExtraInfo',ctypes.POINTER(ctypes.c_ulong))]
    class INPUT(ctypes.Structure):
        class _I(ctypes.Union):
            _fields_=[('ki',KEYBDINPUT)]
        _anonymous_=('i',)
        _fields_=[('type',wintypes.DWORD),('i',_I)]
    for ch in s:
        for flags in (KEYEVENTF_UNICODE, KEYEVENTF_UNICODE|KEYEVENTF_KEYUP_U):
            inp=INPUT(type=INPUT_KEYBOARD)
            inp.ki=KEYBDINPUT(0, ord(ch), flags, 0, None)
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
            time.sleep(0.015)

def click_at(x,y,right=False):
    SetCursorPos(int(x),int(y)); time.sleep(0.05)
    if right:
        mouse_event(0x0008,0,0,0,0); time.sleep(0.05); mouse_event(0x0010,0,0,0,0)
    else:
        mouse_event(0x0002,0,0,0,0); time.sleep(0.05); mouse_event(0x0004,0,0,0,0)

def set_clip(text):
    CF_UNICODETEXT=13; GMEM_MOVEABLE=2
    if not user32.OpenClipboard(None):
        return False
    user32.EmptyClipboard()
    data=text.encode('utf-16-le')+b'\x00\x00'
    h=kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    p=kernel32.GlobalLock(h)
    ctypes.memmove(p, data, len(data))
    kernel32.GlobalUnlock(h)
    user32.SetClipboardData(CF_UNICODETEXT, h)
    user32.CloseClipboard()
    return True

def snapshot_temps():
    paths=[]
    for root in [os.environ.get('TEMP',''), os.environ.get('TMP',''),
                 r'C:\Users\xs0409\AppData\Local\Temp',
                 r'C:\Users\xs0409\AppData\Roaming\Foxmail',
                 r'E:\Program Files\Foxmail 7.2\Temp',
                 r'E:\Program Files\Foxmail 7.2\Global']:
        if not root or not os.path.isdir(root):
            continue
        for dirpath, dirs, files in os.walk(root):
            # limit depth
            rel = os.path.relpath(dirpath, root)
            if rel.count(os.sep) > 3:
                dirs[:] = []
                continue
            for f in files:
                if f.lower().endswith(('.jpg','.jpeg','.png','.eml','.tmp','.dat')):
                    p=os.path.join(dirpath,f)
                    try:
                        st=os.stat(p)
                    except Exception:
                        continue
                    paths.append((st.st_mtime, st.st_size, p))
    return paths

log('=== start3 ===')
fox=None
for h,c,t in list_top():
    if t=='Foxmail' or (t and 'Foxmail' in t):
        fox=h; break
if not fox:
    log('NO FOX'); sys.exit(1)
log('fox %s' % fox)
ShowWindow(fox, SW_MAXIMIZE)
SetForegroundWindow(fox)
time.sleep(0.4)
r=rect(fox)
log('rect %s %s %s %s' % (r.left,r.top,r.right,r.bottom))

# dump interesting children
children=list_children(fox)
log('child count %d' % len(children))
edits=[]
for h,c,t,rc in children:
    interesting = any(x in c for x in ('Edit','Combo','Button','TEdit','TButton','Thunder','Rich','List')) or (t and len(t)<40)
    if interesting and IsWindowVisible(h):
        w=rc.right-rc.left; hgt=rc.bottom-rc.top
        if w>20 and hgt>10:
            log('CH %s | %s | %s | %s,%s-%s,%s' % (h,c,t[:40], rc.left,rc.top,rc.right,rc.bottom))
            if 'Edit' in c or 'Combo' in c:
                edits.append((h,c,t,rc))

log('edits %d' % len(edits))
# Prefer top-right edit as search box
search=None
if edits:
    edits_sorted=sorted(edits, key=lambda e: (-e[3].left, e[3].top))
    for e in edits_sorted:
        rc=e[3]
        if rc.top < 80 and rc.left > 800:
            search=e; break
    if not search:
        search=edits_sorted[0]
    log('search candidate %s %s' % (search[0], search[1]))

before=snapshot_temps()
before_set=set(p for _,_,p in before)

for _ in range(2):
    tap(VK_ESCAPE); time.sleep(0.1)

SetForegroundWindow(fox)
time.sleep(0.2)

if search:
    h=search[0]
    rc=search[3]
    click_at((rc.left+rc.right)//2, (rc.top+rc.bottom)//2)
    time.sleep(0.2)
    SendMessageW(h, WM_SETTEXT, 0, u'员工手册')
    time.sleep(0.2)
    # verify
    ln = SendMessageW(h, WM_GETTEXTLENGTH, 0, 0)
    buf=ctypes.create_unicode_buffer(ln+1)
    SendMessageW(h, WM_GETTEXT, ln+1, buf)
    log('search text now: %s' % buf.value)
    tap(VK_RETURN)
else:
    # Ctrl+Shift+F
    chord([VK_CONTROL, VK_SHIFT, ord('F')])
    time.sleep(0.8)
    type_unicode(u'员工手册')
    time.sleep(0.2)
    tap(VK_RETURN)

time.sleep(4.0)
log('after search top wins:')
for h,c,t in list_top():
    if t: log('  %s | %s' % (c, t[:60]))

# click likely first result row
fw=r.right-r.left; fh=r.bottom-r.top
for my_ratio in (0.22, 0.26, 0.30, 0.34):
    click_at(r.left+int(fw*0.42), r.top+int(fh*my_ratio))
    time.sleep(0.4)

# open / preview: Enter
tap(VK_RETURN)
time.sleep(2.5)

# After open, look for new temp images ~200-400KB
time.sleep(1.0)
after=snapshot_temps()
new=[]
for m,sz,p in after:
    if p not in before_set and m > time.time()-120:
        new.append((m,sz,p))
        log('NEWTEMP %s %s' % (sz, p))
# also any Catch
for m,sz,p in after:
    if 'Catch' in p or '08-27' in p or '员工' in p:
        log('CATCHHIT %s %s' % (sz, p))
        new.append((m,sz,p))

# Copy promising jpgs
copied=0
for m,sz,p in sorted(new, reverse=True):
    if p.lower().endswith(('.jpg','.jpeg','.png')) and 50*1024 < sz < 2*1024*1024:
        dst=os.path.join(OUT_DIR, os.path.basename(p))
        try:
            shutil.copy2(p, dst)
            log('COPIED %s -> %s' % (p, dst))
            copied += 1
        except Exception as e:
            log('copy fail %s %s' % (p, e))

# Try save as via menu key / Alt
SetForegroundWindow(fox)
time.sleep(0.3)
# Alt+F may not work on Chinese; try app menu button
# Foxmail: Ctrl+S sometimes saves attachments? try
out_eml = os.path.join(OUT_DIR, 'handbook_129547.eml')
set_clip(out_eml)
# Application key / Shift+F10 context menu on list
click_at(r.left+int(fw*0.42), r.top+int(fh*0.28))
time.sleep(0.2)
tap(0x5D)  # VK_APPS
time.sleep(0.8)
# type first letters unlikely; navigate: often 另存为 near top
for _ in range(12):
    tap(VK_DOWN, delay=0.1)
tap(VK_RETURN)
time.sleep(1.0)
# if save dlg, paste
log('wins after apps menu:')
for h,c,t in list_top():
    if t: log('  %s | %s' % (c,t[:70]))
chord([VK_CONTROL, ord('V')]); time.sleep(0.2); tap(VK_RETURN); time.sleep(1.0)

# Enum all #32770 dialogs
for h,c,t in list_top():
    if c=='#32770':
        log('DIALOG %s' % t)
        # set filename edit child
        kids=list_children(h)
        for ch,cc,ct,cr in kids:
            if 'Edit' in cc:
                SendMessageW(ch, WM_SETTEXT, 0, out_eml)
                log('set dialog edit %s' % cc)
        tap(VK_RETURN)

time.sleep(1.0)
log('OUTDIR:')
for n in os.listdir(OUT_DIR):
    p=os.path.join(OUT_DIR,n)
    if os.path.isfile(p):
        log('  %s %s' % (n, os.path.getsize(p)))

# Also search Storage for recent Catch in CommintAttachs
att=r'E:\Program Files\Foxmail 7.2\Storage\huijie@bidcenter.cn\CommintAttachs'
if os.path.isdir(att):
    hits=[]
    for dirpath,_,files in os.walk(att):
        for f in files:
            if 'Catch' in f or '08-27' in f:
                hits.append(os.path.join(dirpath,f))
    log('attach hits %d' % len(hits))
    for p in hits[:20]:
        log('  ATT %s %s' % (os.path.getsize(p), p))
        if 'Catch' in p:
            shutil.copy2(p, os.path.join(OUT_DIR, os.path.basename(p)))
            log('COPIED ATT')

log('=== done3 copied=%d ===' % copied)
logf.close()
