import subprocess, datetime, time, os, sys
PY = r'E:\soft\Python\python.exe'
SCRIPT = r'C:\Users\xs0409\Desktop\fox_export\export_gui3.py'
now = datetime.datetime.now()
st = (now + datetime.timedelta(seconds=80)).strftime('%H:%M')
subprocess.call('schtasks /Delete /TN fox_export_it /F', shell=True)
tr = '%s %s' % (PY, SCRIPT)
cmd = 'schtasks /Create /TN fox_export_it /TR "%s" /SC ONCE /ST %s /IT /F' % (tr, st)
print(cmd)
print('create', subprocess.call(cmd, shell=True))
print('run', subprocess.call('schtasks /Run /TN fox_export_it', shell=True))
p = r'C:\Users\xs0409\Desktop\fox_export\export_log3.txt'
for i in range(50):
    time.sleep(1)
    if os.path.exists(p) and b'done3' in open(p, 'rb').read():
        sys.stdout.buffer.write(open(p, 'rb').read())
        sys.stdout.buffer.write(b'\nDIR\n')
        for n in os.listdir(r'C:\Users\xs0409\Desktop\fox_export'):
            fp = os.path.join(r'C:\Users\xs0409\Desktop\fox_export', n)
            if os.path.isfile(fp):
                sys.stdout.buffer.write(('%s %s\n' % (n, os.path.getsize(fp))).encode())
        break
else:
    print('timeout')
    if os.path.exists(p):
        sys.stdout.buffer.write(open(p, 'rb').read())
