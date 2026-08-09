/* Probe with old MSVC string (12-byte) and multiple conventions */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

typedef struct { char *ptr; size_t size; size_t cap; } str12;
typedef struct {
    union { char buf[16]; char *ptr; } bx;
    size_t size; size_t res;
} str24;

static void *(*crt_malloc)(size_t);
static void (*crt_free)(void *);
static void crt_init(void) {
    HMODULE m = LoadLibraryA("msvcrt.dll");
    crt_malloc = (void *(*)(size_t))GetProcAddress(m, "malloc");
    crt_free = (void (*)(void *))GetProcAddress(m, "free");
}

static void s12_set(str12 *s, const void *d, size_t n) {
    s->ptr = (char *)crt_malloc(n + 1);
    memcpy(s->ptr, d, n); s->ptr[n] = 0;
    s->size = n; s->cap = n;
}
static void s24_set(str24 *s, const void *d, size_t n) {
    memset(s, 0, sizeof(*s));
    if (n < 16) {
        memcpy(s->bx.buf, d, n); s->bx.buf[n]=0; s->size=n; s->res=15;
    } else {
        s->bx.ptr=(char*)crt_malloc(n+1); memcpy(s->bx.ptr,d,n); s->bx.ptr[n]=0;
        s->size=n; s->res=n;
    }
}

int main(int argc, char **argv) {
    crt_init();
    HMODULE mod = LoadLibraryA(argc>1?argv[1]:"FoxCryptoPP.dll");
    void *enc = GetProcAddress(mod, "ipc_encrypt");
    void *dec = GetProcAddress(mod, "ipc_decrypt");
    printf("mod=%p enc=%p dec=%p\n", mod, enc, dec); fflush(stdout);

    unsigned char key[16];
    for (int i=0;i<16;i++) sscanf((argc>2?argv[2]:"41414141414141414141414141414141")+i*2, "%02x", (unsigned*)&key[i]);
    const char *plain = "hello";

    /* Variant A: str12 by ptr, stdcall */
    {
        str12 out={0}, k={0}, d={0};
        s12_set(&k, key, 16); s12_set(&d, plain, 5);
        printf("A: stdcall str12 ptrs\n"); fflush(stdout);
        typedef str12*(__stdcall *F)(str12*,str12*,str12*);
        str12 *r = ((F)enc)(&out, &k, &d);
        printf("A ret=%p out.size=%u\n", r, (unsigned)out.size); fflush(stdout);
        if (out.size && out.ptr) {
            printf("A data: "); fwrite(out.ptr,1,out.size>40?40:out.size,stdout); printf("\n");
        }
    }

    /* Variant B: str24 by ptr */
    {
        str24 out={0}, k, d;
        out.res=15;
        s24_set(&k, key, 16); s24_set(&d, plain, 5);
        printf("B: stdcall str24 ptrs\n"); fflush(stdout);
        typedef str24*(__stdcall *F)(str24*,str24*,str24*);
        str24 *r = ((F)enc)(&out, &k, &d);
        printf("B ret=%p out.size=%u\n", r, (unsigned)out.size); fflush(stdout);
    }

    /* Variant C: cdecl str12 */
    {
        str12 out={0}, k={0}, d={0};
        s12_set(&k, key, 16); s12_set(&d, plain, 5);
        printf("C: cdecl str12 ptrs\n"); fflush(stdout);
        typedef str12*(__cdecl *F)(str12*,str12*,str12*);
        str12 *r = ((F)enc)(&out, &k, &d);
        printf("C ret=%p out.size=%u\n", r, (unsigned)out.size); fflush(stdout);
        if (out.size && out.ptr) {
            printf("C data: "); fwrite(out.ptr,1,out.size>40?40:out.size,stdout); printf("\n");
        }
    }

    /* Variant D: only 2 args stdcall - key, data inout */
    {
        str12 k={0}, d={0};
        s12_set(&k, key, 16); s12_set(&d, plain, 5);
        printf("D: stdcall 2-arg (k,d) str12\n"); fflush(stdout);
        typedef void(__stdcall *F)(str12*,str12*);
        ((F)enc)(&k, &d);
        printf("D d.size=%u\n", (unsigned)d.size); fflush(stdout);
    }

    printf("done\n");
    return 0;
}
