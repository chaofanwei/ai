/*
 * Call FoxCryptoPP.dll ipc_decrypt (MSVC stdcall, 3 args / ret 0xC).
 * Build: i686-w64-mingw32-gcc -o fox_ipc_decrypt.exe fox_ipc_decrypt.c
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

/* MSVC x86 std::string layout (VS2015+) */
typedef struct {
    union {
        char buf[16];
        char *ptr;
    } bx;
    size_t size;
    size_t res;
} msvc_string;

/* Must use same CRT heap as FoxCryptoPP (msvcrt), not mingw malloc */
static void *(*crt_malloc)(size_t) = NULL;
static void (*crt_free)(void *) = NULL;

static void crt_init(void) {
    HMODULE m = LoadLibraryA("msvcrt.dll");
    if (!m) { fprintf(stderr, "msvcrt missing\n"); exit(1); }
    crt_malloc = (void *(*)(size_t))GetProcAddress(m, "malloc");
    crt_free = (void (*)(void *))GetProcAddress(m, "free");
    if (!crt_malloc || !crt_free) { fprintf(stderr, "msvcrt malloc/free missing\n"); exit(1); }
}

static char *msvc_data(msvc_string *s) {
    return (s->res < 16) ? s->bx.buf : s->bx.ptr;
}

static void msvc_init(msvc_string *s) {
    memset(s, 0, sizeof(*s));
    s->res = 15;
}

static void msvc_set(msvc_string *s, const void *data, size_t n) {
    msvc_init(s);
    if (n < 16) {
        memcpy(s->bx.buf, data, n);
        s->bx.buf[n] = 0;
        s->size = n;
        s->res = 15;
    } else {
        char *p = (char *)crt_malloc(n + 1);
        if (!p) { fprintf(stderr, "oom\n"); exit(1); }
        memcpy(p, data, n);
        p[n] = 0;
        s->bx.ptr = p;
        s->size = n;
        s->res = n;
    }
}

static void msvc_free(msvc_string *s) {
    if (s->res >= 16 && s->bx.ptr) crt_free(s->bx.ptr);
    msvc_init(s);
}

/* stdcall: cleans 12 bytes => 3 pointer args */
typedef msvc_string *(__stdcall *ipc_decrypt_fn)(msvc_string *out, msvc_string *key, msvc_string *data);
typedef msvc_string *(__stdcall *ipc_encrypt_fn)(msvc_string *out, msvc_string *key, msvc_string *data);

static int read_file(const char *path, unsigned char **out, size_t *out_len) {
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (n < 0) { fclose(f); return -1; }
    unsigned char *buf = (unsigned char *)malloc((size_t)n);
    if (!buf) { fclose(f); return -1; }
    if (fread(buf, 1, (size_t)n, f) != (size_t)n) { free(buf); fclose(f); return -1; }
    fclose(f);
    *out = buf;
    *out_len = (size_t)n;
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 5) {
        fprintf(stderr,
            "Usage: %s <FoxCryptoPP.dll> <Index.key|hex16> <in.bin> <out.bin>\n",
            argv[0]);
        return 2;
    }
    crt_init();
    const char *dll_path = argv[1];
    const char *key_arg = argv[2];
    const char *in_path = argv[3];
    const char *out_path = argv[4];

    unsigned char key[64];
    size_t key_len = 0;
    /* key file or hex */
    FILE *kf = fopen(key_arg, "rb");
    if (kf) {
        key_len = fread(key, 1, sizeof(key), kf);
        fclose(kf);
    } else {
        size_t hexlen = strlen(key_arg);
        if (hexlen % 2 || hexlen > sizeof(key) * 2) {
            fprintf(stderr, "bad key\n");
            return 1;
        }
        for (size_t i = 0; i < hexlen; i += 2) {
            unsigned int b;
            if (sscanf(key_arg + i, "%02x", &b) != 1) {
                fprintf(stderr, "bad hex key\n");
                return 1;
            }
            key[key_len++] = (unsigned char)b;
        }
    }
    printf("key_len=%u key=", (unsigned)key_len);
    for (size_t i = 0; i < key_len; i++) printf("%02x", key[i]);
    printf("\n");

    unsigned char *in = NULL;
    size_t in_len = 0;
    if (read_file(in_path, &in, &in_len) != 0) {
        fprintf(stderr, "cannot read %s\n", in_path);
        return 1;
    }
    printf("in_len=%u\n", (unsigned)in_len);

    HMODULE mod = LoadLibraryA(dll_path);
    if (!mod) {
        fprintf(stderr, "LoadLibrary failed: %lu\n", GetLastError());
        return 1;
    }
    ipc_decrypt_fn decrypt = (ipc_decrypt_fn)GetProcAddress(mod, "ipc_decrypt");
    if (!decrypt) {
        fprintf(stderr, "GetProcAddress ipc_decrypt failed\n");
        return 1;
    }
    printf("ipc_decrypt=%p\n", (void *)decrypt);

    msvc_string out, kstr, dstr;
    msvc_init(&out);
    msvc_set(&kstr, key, key_len);
    msvc_set(&dstr, in, in_len);

    printf("calling...\n");
    fflush(stdout);
    msvc_string *ret = decrypt(&out, &kstr, &dstr);
    printf("returned %p out.size=%u out.res=%u\n", (void *)ret, (unsigned)out.size, (unsigned)out.res);

    if (out.size == 0) {
        fprintf(stderr, "empty output\n");
        return 1;
    }
    char *pdata = msvc_data(&out);
    FILE *of = fopen(out_path, "wb");
    if (!of) {
        fprintf(stderr, "cannot write %s\n", out_path);
        return 1;
    }
    fwrite(pdata, 1, out.size, of);
    fclose(of);
    printf("wrote %s (%u bytes)\n", out_path, (unsigned)out.size);
    printf("head:");
    for (size_t i = 0; i < out.size && i < 32; i++) printf(" %02x", (unsigned char)pdata[i]);
    printf("\n");
    if (out.size >= 4)
        printf("ascii head: %.80s\n", pdata);

    msvc_free(&out);
    msvc_free(&kstr);
    msvc_free(&dstr);
    free(in);
    FreeLibrary(mod);
    return 0;
}
