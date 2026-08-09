# -*- coding: utf-8 -*-
import ctypes, os, sys, subprocess
from ctypes import wintypes

OUT = r'C:\Users\xs0409\Desktop\fox_export\mem_scan.txt'
OUTDIR = r'C:\Users\xs0409\Desktop\fox_export'
logf = open(OUT, 'wb')


def log(s):
    logf.write((s + '\n').encode('utf-8', 'replace'))
    logf.flush()


kernel32 = ctypes.windll.kernel32
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_READABLE = 0x02 | 0x04 | 0x08 | 0x10 | 0x20 | 0x40 | 0x80


class SYSTEM_INFO(ctypes.Structure):
    _fields_ = [
        ('wProcessorArchitecture', wintypes.WORD),
        ('wReserved', wintypes.WORD),
        ('dwPageSize', wintypes.DWORD),
        ('lpMinimumApplicationAddress', ctypes.c_void_p),
        ('lpMaximumApplicationAddress', ctypes.c_void_p),
        ('dwActiveProcessorMask', ctypes.c_size_t),
        ('dwNumberOfProcessors', wintypes.DWORD),
        ('dwProcessorType', wintypes.DWORD),
        ('dwAllocationGranularity', wintypes.DWORD),
        ('wProcessorLevel', wintypes.WORD),
        ('wProcessorRevision', wintypes.WORD),
    ]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('BaseAddress', ctypes.c_void_p),
        ('AllocationBase', ctypes.c_void_p),
        ('AllocationProtect', wintypes.DWORD),
        ('RegionSize', ctypes.c_size_t),
        ('State', wintypes.DWORD),
        ('Protect', wintypes.DWORD),
        ('Type', wintypes.DWORD),
    ]


def pids_by_name(name):
    out = subprocess.check_output(
        'tasklist /FI "IMAGENAME eq %s" /FO CSV /NH' % name, shell=True
    )
    pids = []
    for line in out.decode('gbk', 'replace').splitlines():
        parts = line.strip().strip('"').split('","')
        if len(parts) >= 2:
            try:
                pids.append(int(parts[1]))
            except Exception:
                pass
    return pids


needles = [
    b'Catch(08-27-10-27-42).jpg',
    'Catch(08-27-10-27-42).jpg'.encode('utf-16le'),
    u'\u5458\u5de5\u624b\u518c'.encode('utf-8'),
    u'\u5458\u5de5\u624b\u518c'.encode('utf-16le'),
    b'bjxingzheng@bidcenter.cn',
    'bjxingzheng@bidcenter.cn'.encode('utf-16le'),
    b'NextPart505316115474',
    b'129547',
]

log('=== mem scan ===')
pids = pids_by_name('Foxmail.exe')
log('pids %s' % pids)
si = SYSTEM_INFO()
kernel32.GetSystemInfo(ctypes.byref(si))
max_addr = si.lpMaximumApplicationAddress
min_addr = si.lpMinimumApplicationAddress or 0
log('addr range %s %s' % (min_addr, max_addr))

found_files = []
for pid in pids:
    h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        log('open fail pid %s err %s' % (pid, kernel32.GetLastError()))
        continue
    log('scanning pid %s' % pid)
    addr = ctypes.c_size_t(min_addr)
    mbi = MEMORY_BASIC_INFORMATION()
    hits = 0
    jpeg_saved = 0
    while addr.value < (max_addr or 0x7FFF0000):
        ret = kernel32.VirtualQueryEx(
            h, ctypes.c_void_p(addr.value), ctypes.byref(mbi), ctypes.sizeof(mbi)
        )
        if ret == 0:
            break
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0
        if size == 0:
            break
        prot = mbi.Protect & 0xFF
        if (mbi.State == MEM_COMMIT) and (prot in (0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80)) and not (
            mbi.Protect & 0x100
        ):
            read_size = size if size <= 16 * 1024 * 1024 else 16 * 1024 * 1024
            buf = (ctypes.c_char * read_size)()
            nread = ctypes.c_size_t(0)
            ok = kernel32.ReadProcessMemory(
                h, ctypes.c_void_p(base), buf, read_size, ctypes.byref(nread)
            )
            if ok and nread.value:
                data = bytes(buf[: nread.value])
                for n in needles:
                    pos = 0
                    while True:
                        i = data.find(n, pos)
                        if i < 0:
                            break
                        hits += 1
                        ctx = data[max(0, i - 32) : i + len(n) + 64]
                        log(
                            'HIT pid=%s va=0x%X needle=%r ctx=%r'
                            % (pid, base + i, n[:40], ctx[:100])
                        )
                        if b'Catch' in n:
                            win = data[max(0, i - 200000) : i + 400000]
                            j = win.find(b'\xff\xd8\xff')
                            if j >= 0:
                                k = win.find(b'\xff\xd9', j + 2)
                                if k > j and (k - j) < 800000:
                                    jpeg = win[j : k + 2]
                                    if 50 * 1024 < len(jpeg) < 600 * 1024:
                                        fn = os.path.join(
                                            OUTDIR, 'mem_catch_%s_%d.jpg' % (pid, jpeg_saved)
                                        )
                                        open(fn, 'wb').write(jpeg)
                                        log('SAVEDJPEG %s %s' % (len(jpeg), fn))
                                        found_files.append(fn)
                                        jpeg_saved += 1
                        pos = i + 1
                if jpeg_saved < 3:
                    pos = 0
                    while jpeg_saved < 5:
                        j = data.find(b'\xff\xd8\xff', pos)
                        if j < 0:
                            break
                        k = data.find(b'\xff\xd9', j + 2)
                        if k > j:
                            ln = k - j + 2
                            if 200000 <= ln <= 350000:
                                fn = os.path.join(
                                    OUTDIR, 'mem_jpeg_%s_%d.jpg' % (pid, jpeg_saved)
                                )
                                open(fn, 'wb').write(data[j : k + 2])
                                log('SAVEDSIZEJPEG %s -> %s' % (ln, fn))
                                found_files.append(fn)
                                jpeg_saved += 1
                            pos = k + 2
                        else:
                            pos = j + 3
        next_addr = base + size
        if next_addr <= addr.value:
            break
        addr = ctypes.c_size_t(next_addr)
    kernel32.CloseHandle(h)
    log('pid %s hits=%s jpeg_saved=%s' % (pid, hits, jpeg_saved))

log('files %s' % found_files)
log('=== done mem ===')
logf.close()
