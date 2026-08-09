/* Probe FoxCryptoPP ipc_encrypt/ipc_decrypt ABIs */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

typedef struct {
    union { char buf[16]; char *ptr; } bx;
    size_t size;
    size_t res;
} msvc_string;

static void *(*crt_malloc)(size_t);
static void (*crt_free)(void *);

static void crt_init(void) {
    HMODULE m = LoadLibraryA("msvcrt.dll");
    crt_malloc = (void *(*)(size_t))GetProcAddress(m, "malloc");
    crt_free = (void (*)(void *))GetProcAddress(m, "free");
}

static void msvc_init(msvc_string *s) { memset(s, 0, sizeof(*s)); s->res = 15; }

static void msvc_set(msvc_string *s, const void *data, size_t n) {
    msvc_init(s);
    if (n < 16) {
        memcpy(s->bx.buf, data, n);
        s->bx.buf[n] = 0;
        s->size = n; s->res = 15;
    } else {
        char *p = (char *)crt_malloc(n + 1);
        memcpy(p, data, n); p[n] = 0;
        s->bx.ptr = p; s->size = n; s->res = n;
    }
}

static char *msvc_data(msvc_string *s) { return s->res < 16 ? s->bx.buf : s->bx.ptr; }

typedef msvc_string *(__stdcall *fn3)(msvc_string *, msvc_string *, msvc_string *);
typedef msvc_string *(__cdecl *fn3c)(msvc_string *, msvc_string *, msvc_string *);
typedef void (__stdcall *fn3v)(msvc_string *, msvc_string *, msvc_string *);

static void dump(const char *tag, msvc_string *s) {
    printf("%s size=%u res=%u head=", tag, (unsigned)s->size, (unsigned)s->res);
    char *p = msvc_data(s);
    for (size_t i = 0; i < s->size && i < 24; i++) printf("%02x", (unsigned char)p[i]);
    printf("\n");
    fflush(stdout);
}

int main(int argc, char **argv) {
    const char *dll = argc > 1 ? argv[1] : "FoxCryptoPP.dll";
    unsigned char key[16];
    if (argc > 2) {
        for (int i = 0; i < 16; i++) sscanf(argv[2] + i * 2, "%02x", (unsigned *)&key[i]);
    } else {
        memset(key, 0x41, 16);
    }
    crt_init();
    HMODULE mod = LoadLibraryA(dll);
    printf("mod=%p err=%lu\n", (void *)mod, GetLastError());
    fn3 enc = (fn3)GetProcAddress(mod, "ipc_encrypt");
    fn3 dec = (fn3)GetProcAddress(mod, "ipc_decrypt");
    printf("enc=%p dec=%p\n", (void *)enc, (void *)dec);
    fflush(stdout);

    const char *plain = "From: test@example.com\r\nSubject: hi\r\n\r\nhello foxmail\r\n";
    msvc_string out, k, d, out2;
    msvc_init(&out); msvc_init(&out2);
    msvc_set(&k, key, 16);
    msvc_set(&d, plain, strlen(plain));

    printf("encrypt(out,key,data)...\n"); fflush(stdout);
    msvc_string *r = enc(&out, &k, &d);
    printf("enc ret=%p\n", (void *)r);
    dump("enc_out", &out);

    if (out.size > 0) {
        msvc_string cipher;
        msvc_set(&cipher, msvc_data(&out), out.size);
        printf("decrypt...\n"); fflush(stdout);
        r = dec(&out2, &k, &cipher);
        printf("dec ret=%p\n", (void *)r);
        dump("dec_out", &out2);
        if (out2.size) fwrite(msvc_data(&out2), 1, out2.size, stdout);
        printf("\n");
    }
    return 0;
}
