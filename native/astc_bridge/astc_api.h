#pragma once
#ifndef UABE_API
#define UABE_API __attribute__((visibility("default"), used))
#endif
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct astc_android_ctx astc_android_ctx;

UABE_API astc_android_ctx* astc_create(
        int profile, int block_x, int block_y, int block_z,
        float quality, int flags);

UABE_API void astc_destroy(astc_android_ctx* ctx);

UABE_API int astc_compress_rgba8(
        astc_android_ctx* ctx,
        const uint8_t* rgba, int width, int height,
        uint8_t* out_astc, int out_size_bytes);

UABE_API int astc_decompress_rgba8(
        astc_android_ctx* ctx,
        const uint8_t* astc_blocks, int astc_size_bytes,
        int width, int height,
        uint8_t* out_rgba, int out_rgba_size_bytes);

#ifdef __cplusplus
}
#endif
