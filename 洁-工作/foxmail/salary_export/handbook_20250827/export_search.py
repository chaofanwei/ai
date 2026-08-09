# -*- coding: utf-8 -*-
import ctypes, time, os, sys, shutil
from ctypes import wintypes

LOG = r'C:\Users\xs0409\Desktop\fox_export\export_search.txt'
OUTDIR = r'C:\Users\xs0409\Desktop\fox_export'
logf = open(LOG, 'wb')


def log(s):
    logf.write((s + '\n').encode('utf-8', 'replace'))
    logf.flush()


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
IsWindowVisible = user32.IsWindowVisible
SetForegroundWindow = user32.SetForegroundWindow
ShowWindow = user32.ShowWindow
GetWindowRect = user32.GetWindowRect
keybd_event = user32.keybd_event
mouse_event = user32.mouse_event
SetCursorPos = user32.SetCursorPos

VK_CONTROL = 0x11
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_DOWN = 0x28
KEYEVENTF_KEYUP = 2
SW_MAXIMIZE = 3
WM_CLOSE = 0x0010


class RECT(ctypes.Structure):
    _fields_ = [
        ('left', ctypes.c_long),
        ('top', ctypes.c_long),
        ('right', ctypes.c_long),
        ('bottom', ctypes.c_long),
    ]


def title(hwnd):
    n = GetWindowTextLengthW(hwnd)
    b = ctypes.create_unicode_buffer(n + 1)
    GetWindowTextW(hwnd, b, n + 1)
    return b.value


def list_top():
    out = []

    def cb(h, l):
        if IsWindowVisible(h):
            t = title(h)
            if t:
                out.append((h, t))
        return True

    EnumWindows(EnumWindowsProc(cb), 0)
    return out


def press(vk, down=True):
    keybd_event(vk, 0, 0 if down else KEYEVENTF_KEYUP, 0)


def tap(vk, delay=0.08):
    press(vk, True)
    time.sleep(0.03)
    press(vk, False)
    time.sleep(delay)


def chord(vks, hold=0.05):
    for v in vks:
        press(v, True)
        time.sleep(0.02)
    time.sleep(hold)
    for v in reversed(vks):
        press(v, False)
        time.sleep(0.02)


def click_at(x, y, right=False):
    SetCursorPos(int(x), int(y))
    time.sleep(0.05)
    if right:
        mouse_event(0x0008, 0, 0, 0, 0)
        time.sleep(0.05)
        mouse_event(0x0010, 0, 0, 0, 0)
    else:
        mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.05)
        mouse_event(0x0004, 0, 0, 0, 0)


def set_clip(text):
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    user32.OpenClipboard(None)
    user32.EmptyClipboard()
    data = text.encode('utf-16-le') + b'\x00\x00'
    h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    p = kernel32.GlobalLock(h)
    ctypes.memmove(p, data, len(data))
    kernel32.GlobalUnlock(h)
    user32.SetClipboardData(CF_UNICODETEXT, h)
    user32.CloseClipboard()


def type_unicode(s):
    INPUT_KEYBOARD = 1
    KEYEVENTF_UNICODE = 0x0004
    KEYEVENTF_KEYUP_U = 0x0002

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ('wVk', wintypes.WORD),
            ('wScan', wintypes.WORD),
            ('dwFlags', wintypes.DWORD),
            ('time', wintypes.DWORD),
            ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        class _I(ctypes.Union):
            _fields_ = [('ki', KEYBDINPUT)]

        _anonymous_ = ('i',)
        _fields_ = [('type', wintypes.DWORD), ('i', _I)]

    for ch in s:
        for flags in (KEYEVENTF_UNICODE, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP_U):
            inp = INPUT(type=INPUT_KEYBOARD)
            inp.ki = KEYBDINPUT(0, ord(ch), flags, 0, None)
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
            time.sleep(0.02)


log('=== search export ===')
mail = r'E:\Program Files\Foxmail 7.2\Storage\huijie@bidcenter.cn\Mails\11\16\129547'
log('mail exists %s size %s' % (os.path.exists(mail), os.path.getsize(mail) if os.path.exists(mail) else -1))
ikey = r'E:\Program Files\Foxmail 7.2\Storage\huijie@bidcenter.cn\Mails\Index.key'
log('index.key exists %s' % os.path.exists(ikey))

# close mail viewers
for h, t in list_top():
    if 'TMailViewer' in t or (u'\u60a8\u5b9a\u5236' in t):
        pass
for h, t in list_top():
    # close viewer forms by title containing known wrong subjects is hard; Esc later
    if t and ('2022-06-08' in t or u'\u6700\u65b0\u9879\u76ee' in t):
        log('close viewer %s' % t[:60])
        user32.PostMessageW(h, WM_CLOSE, 0, 0)

fox = None
for h, t in list_top():
    if t == 'Foxmail':
        fox = h
        break
if not fox:
    log('NO FOX')
    sys.exit(1)

ShowWindow(fox, SW_MAXIMIZE)
SetForegroundWindow(fox)
time.sleep(0.4)
r = RECT()
GetWindowRect(fox, ctypes.byref(r))
log('rect %s %s %s %s' % (r.left, r.top, r.right, r.bottom))
fw = r.right - r.left
fh = r.bottom - r.top

for _ in range(2):
    tap(VK_ESCAPE)
    time.sleep(0.15)

# search box from successful Mac coords ratio: ~82% width, ~y=top+45 for non-neg; maximized top=-8
sx = r.left + int(fw * 0.82)
sy = r.top + 45
log('click search %s %s' % (sx, sy))
click_at(sx, sy)
time.sleep(0.35)
chord([VK_CONTROL, ord('A')])
time.sleep(0.1)
q = u'\u5458\u5de5\u624b\u518c'  # 员工手册
set_clip(q)
chord([VK_CONTROL, ord('V')])
time.sleep(0.4)
# also type unicode as backup
# type_unicode(q)
tap(VK_RETURN)
time.sleep(5.0)

log('wins after search:')
for h, t in list_top():
    log('  %s' % t[:90])

# click first result rows and look for 2025 / handbook in viewer title
for ratio in (0.20, 0.24, 0.28, 0.32, 0.36):
    click_at(r.left + int(fw * 0.45), r.top + int(fh * ratio))
    time.sleep(0.5)
    tap(VK_RETURN)
    time.sleep(1.2)
    for h, t in list_top():
        if t and t != 'Foxmail' and ('Foxmail' not in t or len(t) > 10):
            if any(x in t for x in (u'\u5458\u5de5', u'\u8003\u52e4', '2025', 'Catch', u'\u5468\u6d77')):
                log('CANDIDATE VIEWER %s' % t[:100])

# After search results, try save first selected via right-click menu
click_at(r.left + int(fw * 0.45), r.top + int(fh * 0.24))
time.sleep(0.3)
click_at(r.left + int(fw * 0.45), r.top + int(fh * 0.24), right=True)
time.sleep(1.0)
# navigate menu - try type 另 (unicode) won't select; use downs
# Foxmail context: often 打开, 回复..., 另存为 is further
for i in range(15):
    tap(VK_DOWN, delay=0.1)
    # periodically hit enter? no
tap(VK_RETURN)
time.sleep(1.2)

log('wins after menu:')
for h, t in list_top():
    log('  %s' % t[:90])

out_eml = os.path.join(OUTDIR, 'handbook_129547.eml')
set_clip(out_eml)
# if save dialog (#32770)
for h, t in list_top():
    # class check skipped; look for 另存/保存
    if any(x in t for x in (u'\u53e6\u5b58', u'\u4fdd\u5b58', 'Save')):
        log('save dlg %s' % t)
        chord([VK_CONTROL, ord('V')])
        time.sleep(0.2)
        tap(VK_RETURN)

time.sleep(1.0)

# Scan temp for Catch after opening
for root in [
    os.environ.get('TEMP', ''),
    r'C:\Users\xs0409\AppData\Local\Temp',
    r'E:\Program Files\Foxmail 7.2',
]:
    if not root or not os.path.isdir(root):
        continue
    for dp, dns, fns in os.walk(root):
        if dp.count(os.sep) - root.count(os.sep) > 4:
            dns[:] = []
            continue
        for f in fns:
            if 'Catch' in f or (f.lower().endswith('.jpg') and '08-27' in f):
                p = os.path.join(dp, f)
                try:
                    sz = os.path.getsize(p)
                except Exception:
                    continue
                log('FOUND %s %s' % (sz, p))
                try:
                    shutil.copy2(p, os.path.join(OUTDIR, os.path.basename(p)))
                    log('COPIED')
                except Exception as e:
                    log('copy err %s' % e)

log('outdir:')
for n in os.listdir(OUTDIR):
    p = os.path.join(OUTDIR, n)
    if os.path.isfile(p) and not n.endswith('.b64'):
        log('  %s %s' % (n, os.path.getsize(p)))
log('=== done search ===')
logf.close()
