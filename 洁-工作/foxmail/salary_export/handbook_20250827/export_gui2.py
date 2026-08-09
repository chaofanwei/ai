# -*- coding: utf-8 -*-
import ctypes, time, os, sys
from ctypes import wintypes

logf = open(r'C:\Users\xs0409\Desktop\fox_export\export_log2.txt', 'w')

def log(m):
    logf.write(m + '\n')
    logf.flush()
    print(m)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
IsWindowVisible = user32.IsWindowVisible
SetForegroundWindow = user32.SetForegroundWindow
ShowWindow = user32.ShowWindow
GetClassNameW = user32.GetClassNameW
PostMessageW = user32.PostMessageW
keybd_event = user32.keybd_event
mouse_event = user32.mouse_event
SetCursorPos = user32.SetCursorPos
GetWindowRect = user32.GetWindowRect

WM_CLOSE = 0x0010
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
KEYEVENTF_KEYUP = 2
SW_RESTORE = 9
SW_MAXIMIZE = 3


class RECT(ctypes.Structure):
    _fields_ = [
        ('left', ctypes.c_long),
        ('top', ctypes.c_long),
        ('right', ctypes.c_long),
        ('bottom', ctypes.c_long),
    ]


def win_title(hwnd):
    n = GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def win_class(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    GetClassNameW(hwnd, buf, 256)
    return buf.value


def list_wins():
    out = []

    def cb(hwnd, lparam):
        if IsWindowVisible(hwnd):
            t = win_title(hwnd)
            c = win_class(hwnd)
            if t or c:
                out.append((hwnd, c, t))
        return True

    EnumWindows(EnumWindowsProc(cb), 0)
    return out


def press(vk, down=True):
    keybd_event(vk, 0, 0 if down else KEYEVENTF_KEYUP, 0)


def tap(vk, times=1, delay=0.08):
    for _ in range(times):
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
            time.sleep(0.01)


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


OUT = r'C:\Users\xs0409\Desktop\fox_export\handbook_129547.eml'
OUT_DIR = r'C:\Users\xs0409\Desktop\fox_export'
for old in [
    OUT,
    OUT.replace('.eml', '.txt'),
    os.path.join(OUT_DIR, 'Catch(08-27-10-27-42).jpg'),
]:
    try:
        if os.path.exists(old):
            os.remove(old)
    except Exception:
        pass

log('=== start2 ===')
wins = list_wins()
for h, c, t in wins:
    if t:
        log('W %s | %s | %s' % (h, c, t[:80]))

for h, c, t in wins:
    if ('拨打' in t) or ('153808' in t):
        log('close dialer %s %s' % (h, t))
        PostMessageW(h, WM_CLOSE, 0, 0)
time.sleep(0.5)

fox = None
for h, c, t in list_wins():
    if t == 'Foxmail' or (t and 'Foxmail' in t):
        fox = h
        break
if not fox:
    log('NO FOXMAIL')
    sys.exit(1)
log('fox hwnd %s' % fox)

ShowWindow(fox, SW_RESTORE)
time.sleep(0.2)
ShowWindow(fox, SW_MAXIMIZE)
time.sleep(0.3)
SetForegroundWindow(fox)
time.sleep(0.5)

rc = RECT()
GetWindowRect(fox, ctypes.byref(rc))
log('fox rect %s %s %s %s' % (rc.left, rc.top, rc.right, rc.bottom))
fw = rc.right - rc.left
fh = rc.bottom - rc.top

for _ in range(3):
    tap(VK_ESCAPE)
    time.sleep(0.15)

sx = rc.left + fw - 160
sy = rc.top + 42
log('click search %s %s' % (sx, sy))
click_at(sx, sy)
time.sleep(0.4)

chord([VK_CONTROL, ord('A')])
time.sleep(0.1)
set_clip(u'员工手册')
chord([VK_CONTROL, ord('V')])
time.sleep(0.4)
tap(VK_RETURN)
time.sleep(4.0)

log('after search:')
for h, c, t in list_wins():
    if t and ('Foxmail' in t or '搜索' in t or '另存' in t or '保存' in t):
        log('  %s | %s' % (c, t[:80]))

mx = rc.left + int(fw * 0.45)
my = rc.top + int(fh * 0.28)
log('click mail row %s %s' % (mx, my))
click_at(mx, my)
time.sleep(0.8)

set_clip(OUT)
chord([VK_CONTROL, ord('S')])
time.sleep(1.5)

log('after ctrl+s:')
for h, c, t in list_wins():
    if t:
        log('  %s | %s | %s' % (h, c, t[:90]))

chord([VK_CONTROL, ord('V')])
time.sleep(0.3)
tap(VK_RETURN)
time.sleep(1.0)
tap(ord('Y'))
time.sleep(0.5)
tap(VK_RETURN)
time.sleep(1.5)

click_at(mx, my)
time.sleep(0.3)
click_at(mx, my, right=True)
time.sleep(0.8)
log('after rightclick:')
for h, c, t in list_wins():
    if t:
        log('  %s | %s' % (c, t[:80]))

# Context menu: arrow down to 另存为 / save - try several downs + enter
for i in range(8):
    tap(0x28)  # VK_DOWN
    time.sleep(0.12)
tap(VK_RETURN)
time.sleep(1.2)

set_clip(OUT)
chord([VK_CONTROL, ord('V')])
time.sleep(0.3)
tap(VK_RETURN)
time.sleep(1.5)

log('files:')
for n in os.listdir(OUT_DIR):
    p = os.path.join(OUT_DIR, n)
    log('  %s %s' % (n, os.path.getsize(p) if os.path.isfile(p) else 'DIR'))

desk = r'C:\Users\xs0409\Desktop'
for root, dirs, files in os.walk(desk):
    for f in files:
        if f.lower().endswith(('.eml', '.jpg', '.png', '.htm', '.html')):
            p = os.path.join(root, f)
            try:
                m = os.path.getmtime(p)
            except Exception:
                continue
            if m > time.time() - 180:
                log('RECENT %s %s' % (p, os.path.getsize(p)))

log('=== done2 ===')
logf.close()
