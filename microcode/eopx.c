/* atCGS 1.1.0-alpha — monolithic EOPX microcode (Existence of Proof), ISO C11.
 * The birth protocol: stdin is a SEED, a square .bit of at least 256x256 bits;
 * stdout is its GLYPH, 256x256 bits = 8192 bytes, written to the wallet's pipe:
 *     GLYPH := SHAKE-256(SHA-256(SEED) || SEED)
 * Deterministic, from the initial value hash(SEED). It always compresses, even a
 * 256x256 SEED, so hash(GLYPH) != hash(SEED). Neither SEED nor GLYPH is stored.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define GLYPH_SIDE 256u
#define GLYPH_BYTES (GLYPH_SIDE * GLYPH_SIDE / 8u)
#define MAX_SEED_BYTES (8192u * 8192u / 8u) /* 8192x8192 bits = 8 MiB */
#define SHAKE256_RATE 136u

/* ---- SHA-256 (FIPS 180-4) ---- */

static const uint32_t K256[64] = {
    0x428a2f98u, 0x71374491u, 0xb5c0fbcfu, 0xe9b5dba5u, 0x3956c25bu, 0x59f111f1u, 0x923f82a4u, 0xab1c5ed5u,
    0xd807aa98u, 0x12835b01u, 0x243185beu, 0x550c7dc3u, 0x72be5d74u, 0x80deb1feu, 0x9bdc06a7u, 0xc19bf174u,
    0xe49b69c1u, 0xefbe4786u, 0x0fc19dc6u, 0x240ca1ccu, 0x2de92c6fu, 0x4a7484aau, 0x5cb0a9dcu, 0x76f988dau,
    0x983e5152u, 0xa831c66du, 0xb00327c8u, 0xbf597fc7u, 0xc6e00bf3u, 0xd5a79147u, 0x06ca6351u, 0x14292967u,
    0x27b70a85u, 0x2e1b2138u, 0x4d2c6dfcu, 0x53380d13u, 0x650a7354u, 0x766a0abbu, 0x81c2c92eu, 0x92722c85u,
    0xa2bfe8a1u, 0xa81a664bu, 0xc24b8b70u, 0xc76c51a3u, 0xd192e819u, 0xd6990624u, 0xf40e3585u, 0x106aa070u,
    0x19a4c116u, 0x1e376c08u, 0x2748774cu, 0x34b0bcb5u, 0x391c0cb3u, 0x4ed8aa4au, 0x5b9cca4fu, 0x682e6ff3u,
    0x748f82eeu, 0x78a5636fu, 0x84c87814u, 0x8cc70208u, 0x90befffau, 0xa4506cebu, 0xbef9a3f7u, 0xc67178f2u,
};

#define ROR32(x, n) (((x) >> (n)) | ((x) << (32u - (n))))

static void sha256_block(uint32_t h[8], const uint8_t block[64]) {
    uint32_t w[64];
    for (unsigned i = 0; i < 16u; ++i)
        w[i] = (uint32_t)block[4 * i] << 24 | (uint32_t)block[4 * i + 1] << 16 |
               (uint32_t)block[4 * i + 2] << 8 | (uint32_t)block[4 * i + 3];
    for (unsigned i = 16; i < 64u; ++i) {
        uint32_t s0 = ROR32(w[i - 15], 7u) ^ ROR32(w[i - 15], 18u) ^ (w[i - 15] >> 3);
        uint32_t s1 = ROR32(w[i - 2], 17u) ^ ROR32(w[i - 2], 19u) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    uint32_t a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], k = h[7];
    for (unsigned i = 0; i < 64u; ++i) {
        uint32_t t1 = k + (ROR32(e, 6u) ^ ROR32(e, 11u) ^ ROR32(e, 25u)) + ((e & f) ^ (~e & g)) + K256[i] + w[i];
        uint32_t t2 = (ROR32(a, 2u) ^ ROR32(a, 13u) ^ ROR32(a, 22u)) + ((a & b) ^ (a & c) ^ (b & c));
        k = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += k;
}

static void sha256(const uint8_t *data, size_t len, uint8_t out[32]) {
    uint32_t h[8] = {0x6a09e667u, 0xbb67ae85u, 0x3c6ef372u, 0xa54ff53au,
                     0x510e527fu, 0x9b05688cu, 0x1f83d9abu, 0x5be0cd19u};
    size_t full = len / 64u;
    for (size_t i = 0; i < full; ++i)
        sha256_block(h, data + 64u * i);
    uint8_t tail[128] = {0};
    size_t rest = len % 64u;
    memcpy(tail, data + 64u * full, rest);
    tail[rest] = 0x80u;
    size_t blocks = rest < 56u ? 1u : 2u;
    uint64_t bits = (uint64_t)len * 8u;
    for (unsigned i = 0; i < 8u; ++i)
        tail[64u * blocks - 1u - i] = (uint8_t)(bits >> (8u * i));
    for (size_t i = 0; i < blocks; ++i)
        sha256_block(h, tail + 64u * i);
    for (unsigned i = 0; i < 8u; ++i)
        for (unsigned j = 0; j < 4u; ++j)
            out[4u * i + j] = (uint8_t)(h[i] >> (24u - 8u * j));
}

/* ---- SHAKE-256 (FIPS 202): Keccak-f[1600], rate 136, suffix 0x1F ---- */

static const uint64_t RC[24] = {
    0x0000000000000001u, 0x0000000000008082u, 0x800000000000808au, 0x8000000080008000u,
    0x000000000000808bu, 0x0000000080000001u, 0x8000000080008081u, 0x8000000000008009u,
    0x000000000000008au, 0x0000000000000088u, 0x0000000080008009u, 0x000000008000000au,
    0x000000008000808bu, 0x800000000000008bu, 0x8000000000008089u, 0x8000000000008003u,
    0x8000000000008002u, 0x8000000000000080u, 0x000000000000800au, 0x800000008000000au,
    0x8000000080008081u, 0x8000000000008080u, 0x0000000080000001u, 0x8000000080008008u,
};
static const unsigned ROTC[24] = {1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 2, 14,
                                  27, 41, 56, 8, 25, 43, 62, 18, 39, 61, 20, 44};
static const unsigned PILN[24] = {10, 7, 11, 17, 18, 3, 5, 16, 8, 21, 24, 4,
                                  15, 23, 19, 13, 12, 2, 20, 14, 22, 9, 6, 1};

#define ROL64(x, n) (((x) << (n)) | ((x) >> (64u - (n))))

static void keccakf(uint64_t st[25]) {
    uint64_t bc[5], t;
    for (unsigned r = 0; r < 24u; ++r) {
        for (unsigned i = 0; i < 5u; ++i)
            bc[i] = st[i] ^ st[i + 5] ^ st[i + 10] ^ st[i + 15] ^ st[i + 20];
        for (unsigned i = 0; i < 5u; ++i) {
            t = bc[(i + 4u) % 5u] ^ ROL64(bc[(i + 1u) % 5u], 1u);
            for (unsigned j = 0; j < 25u; j += 5u)
                st[j + i] ^= t;
        }
        t = st[1];
        for (unsigned i = 0; i < 24u; ++i) {
            unsigned j = PILN[i];
            bc[0] = st[j];
            st[j] = ROL64(t, ROTC[i]);
            t = bc[0];
        }
        for (unsigned j = 0; j < 25u; j += 5u) {
            for (unsigned i = 0; i < 5u; ++i)
                bc[i] = st[j + i];
            for (unsigned i = 0; i < 5u; ++i)
                st[j + i] ^= (~bc[(i + 1u) % 5u]) & bc[(i + 2u) % 5u];
        }
        st[0] ^= RC[r];
    }
}

typedef struct {
    uint64_t st[25];
    unsigned pos;
} Shake;

static void shake_xor(Shake *s, unsigned pos, uint8_t byte) {
    s->st[pos / 8u] ^= (uint64_t)byte << (8u * (pos % 8u));
}

static void shake_absorb(Shake *s, const uint8_t *data, size_t len) {
    for (size_t i = 0; i < len; ++i) {
        shake_xor(s, s->pos++, data[i]);
        if (s->pos == SHAKE256_RATE) {
            keccakf(s->st);
            s->pos = 0;
        }
    }
}

static void shake_squeeze(Shake *s, uint8_t *out, size_t len) {
    shake_xor(s, s->pos, 0x1fu);
    shake_xor(s, SHAKE256_RATE - 1u, 0x80u);
    keccakf(s->st);
    s->pos = 0;
    for (size_t i = 0; i < len; ++i) {
        if (s->pos == SHAKE256_RATE) {
            keccakf(s->st);
            s->pos = 0;
        }
        out[i] = (uint8_t)(s->st[s->pos / 8u] >> (8u * (s->pos % 8u)));
        s->pos++;
    }
}

/* ---- birth ---- */

static uint64_t isqrt(uint64_t n) {
    uint64_t lo = 0, hi = 1u << 24; /* MAX_SEED_BYTES * 8 < 2^48 */
    while (lo < hi) {
        uint64_t mid = (lo + hi + 1u) / 2u;
        if (mid * mid <= n) lo = mid; else hi = mid - 1u;
    }
    return lo;
}

int main(int argc, char **argv) {
    if (argc != 1) {
        fprintf(stderr, "Usage: %s < SEED.bit > GLYPH (square SEED of at least 256x256 bits)\n", argv[0]);
        return 2;
    }
    uint8_t *seed = malloc(MAX_SEED_BYTES + 1u);
    if (!seed) {
        fputs("EOPX ERROR: out of memory\n", stderr);
        return 2;
    }
    size_t len = fread(seed, 1u, MAX_SEED_BYTES + 1u, stdin);
    int status = 0;
    uint64_t bits = (uint64_t)len * 8u, side = isqrt(bits);
    if (ferror(stdin) || len > MAX_SEED_BYTES) {
        fputs("EOPX ERROR: SEED exceeds 8192x8192 bits\n", stderr);
        status = 2;
    } else if (side < GLYPH_SIDE || side * side != bits) {
        fprintf(stderr, "EOPX ERROR: SEED must be a square .bit of at least 256x256 bits, got %zu bytes\n", len);
        status = 2;
    } else {
        uint8_t h0[32], glyph[GLYPH_BYTES];
        Shake s = {{0}, 0};
        sha256(seed, len, h0);
        shake_absorb(&s, h0, sizeof h0);
        shake_absorb(&s, seed, len);
        shake_squeeze(&s, glyph, sizeof glyph);
        if (fwrite(glyph, 1u, sizeof glyph, stdout) != sizeof glyph || fflush(stdout) != 0)
            status = 2;
        memset(glyph, 0, sizeof glyph);
        memset(&s, 0, sizeof s);
    }
    memset(seed, 0, len);
    free(seed);
    return status;
}
