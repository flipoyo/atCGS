/* atCGS 0.1.1-alpha — monolithic POEX Layer-0 microcode, ISO C11.
 * A quartet is four logical bits, held in the low nibble of a uint8_t.
 * .poe is a stable pointer into SYSTEM, never a pointer to temporary memory.
 * ∆ELTA = current quartet XOR previous quartet (genesis quartet = 0000).
 * This is a live difference report, NOT a cryptographic Proof of Existence.
 */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define MATRIX_BYTES 8192u
#define QUARTETS_PER_PACKET 256u
#define PACKETS 64u
/* POEX's authoritative engine is CGS-ALPHA OPX, not atCGS. */
#define POEX_OWNER "cgitsync"
#define POEX_VERSION "M.m.p"
#define POEX_LAYER "opx"

typedef struct {
    uint8_t last4;            /* exactly four significant bits */
    uint8_t delta4;           /* XOR(current, previous) */
    uint64_t quartets;        /* committed input quartets */
    uint64_t zeros;           /* count of 0 bits */
} POE;

typedef struct {
    POE layer0;               /* POE invariant: owned by System */
    const uint8_t *poe;      /* .poe points into layer0.last4 */
} System;

static System SYSTEM;         /* stable for the life of this process */

static void BIOS(void) {
    memset(&SYSTEM, 0, sizeof SYSTEM);
    SYSTEM.poe = &SYSTEM.layer0.last4;
}

/* OpLayer: one operation, one nibble, pointer to SYSTEM's last 4 bits. */
static const uint8_t *OpLayer(System *s, uint8_t next4) {
    POE *p = &s->layer0;
    next4 &= 0x0fu;
    p->delta4 = (uint8_t)(p->last4 ^ next4);
    p->last4 = next4;
    p->quartets++;
    for (unsigned i = 0; i < 4u; ++i)
        p->zeros += ((next4 >> i) & 1u) == 0u;
    return s->poe;
}

static void bits4(uint8_t value, char out[5]) {
    for (unsigned i = 0; i < 4u; ++i)
        out[i] = (value & (uint8_t)(8u >> i)) ? '1' : '0';
    out[4] = '\0';
}

typedef enum { LIVE, TRACE, PACKET } Display;

static void report(const System *s, Display mode) {
    const POE *p = &s->layer0;
    if (mode == PACKET && p->quartets % QUARTETS_PER_PACKET != 0u)
        return;

    char last[5], delta[5];
    bits4(*s->poe, last);
    bits4(p->delta4, delta);
    uint64_t k = (p->quartets - 1u) / QUARTETS_PER_PACKET;
    const char *end = mode == LIVE ? "\r" : "\n";
    printf("∆ELTA packet=%02" PRIu64 " quartet=%05" PRIu64
           " .poe=%s ∆=%s zeros=%" PRIu64 "%s",
           k, p->quartets, last, delta, p->zeros, end);
    fflush(stdout);             /* immediate synchronous display on input */
}

int main(int argc, char **argv) {
    /* Descriptor-only interface, not an authenticated POEX proof. */
    if (argc == 2 && strcmp(argv[1], "--contract") == 0) {
        puts("poex is " POEX_OWNER " " POEX_VERSION " " POEX_LAYER);
        puts("OpFrontier serves POEX NODE DELTA OPX");
        return 0;
    }
    Display mode = LIVE;
    if (argc > 2 || (argc == 2 && strcmp(argv[1], "--packet") != 0 &&
                     strcmp(argv[1], "--trace") != 0)) {
        fprintf(stderr, "Usage: %s [--trace|--packet] < 256x256.bit\n", argv[0]);
        return 2;
    }
    if (argc == 2)
        mode = strcmp(argv[1], "--packet") == 0 ? PACKET : TRACE;

    BIOS();
    size_t total = 0u;
    int octet;
    while ((octet = fgetc(stdin)) != EOF) {
        if (total == MATRIX_BYTES) {
            fputs("POEX ERROR: input exceeds 8192 bytes\n", stderr);
            return 2;
        }
        const uint8_t value = (uint8_t)octet;
        (void)OpLayer(&SYSTEM, (uint8_t)(value >> 4u));
        report(&SYSTEM, mode);
        (void)OpLayer(&SYSTEM, (uint8_t)(value & 0x0fu));
        report(&SYSTEM, mode);
        total++;
    }
    if (ferror(stdin) || total != MATRIX_BYTES) {
        fprintf(stderr, "POEX ERROR: expected %u bytes, got %zu\n",
                MATRIX_BYTES, total);
        return 2;
    }
    if (SYSTEM.layer0.quartets != PACKETS * QUARTETS_PER_PACKET)
        return 3;
    if (mode == LIVE) putchar('\n');
    printf("POEX FRAMED: %u packets x 4x256 bits; "
           "quartets=%" PRIu64 "; zeros=%" PRIu64 "; evidence=UNVERIFIED\n",
           PACKETS, SYSTEM.layer0.quartets, SYSTEM.layer0.zeros);
    return 0;
}
