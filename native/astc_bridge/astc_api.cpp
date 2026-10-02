#include "astc_api.h"
#include "astcenc.h"

struct astc_android_ctx {
    astcenc_config config{};
    astcenc_context* context = nullptr;
    int block_x = 4, block_y = 4, block_z = 1;
    int profile = ASTCENC_PRF_LDR;
};

static astcenc_profile to_profile(int p) {
    switch (p) {
        case 0: return ASTCENC_PRF_LDR_SRGB;
        case 1: return ASTCENC_PRF_LDR;
        case 2: return ASTCENC_PRF_HDR_RGB_LDR_A;
        case 3: return ASTCENC_PRF_HDR;
        default: return ASTCENC_PRF_LDR;
    }
}

astc_android_ctx* astc_create(int profile, int bx, int by, int bz, float quality, int flags) {
    auto* ctx = new astc_android_ctx();
    ctx->profile = profile;
    ctx->block_x = bx; ctx->block_y = by; ctx->block_z = bz;

    astcenc_error err = astcenc_config_init(
            to_profile(profile),
            bx, by, bz,
            quality,
            flags,
            &ctx->config
    );

    if (err != ASTCENC_SUCCESS) {
        delete ctx;
        return nullptr;
    }

    err = astcenc_context_alloc(&ctx->config, 1, &ctx->context, nullptr);
    if (err != ASTCENC_SUCCESS) {
        delete ctx;
        return nullptr;
    }

    return ctx;
}

void astc_destroy(astc_android_ctx* ctx) {
    if (!ctx) return;
    if (ctx->context) astcenc_context_free(ctx->context);
    delete ctx;
}

int astc_compress_rgba8(astc_android_ctx* ctx,
                        const uint8_t* rgba, int w, int h,
                        uint8_t* out_astc, int out_size) {
    if (!ctx || !ctx->context || !rgba || !out_astc) return 1;

    astcenc_image img{};
    img.dim_x = w;
    img.dim_y = h;
    img.dim_z = 1;
    img.data_type = ASTCENC_TYPE_U8;

    void* slice0 = (void*)rgba;
    img.data = &slice0;

    astcenc_swizzle swz { ASTCENC_SWZ_R, ASTCENC_SWZ_G, ASTCENC_SWZ_B, ASTCENC_SWZ_A };

    astcenc_error err = astcenc_compress_image(
            ctx->context,
            &img,
            &swz,
            out_astc,
            out_size,
            0
    );

    return (err == ASTCENC_SUCCESS) ? 0 : 2;
}

int astc_decompress_rgba8(astc_android_ctx* ctx,
                          const uint8_t* blocks, int blocks_size,
                          int w, int h,
                          uint8_t* out_rgba, int out_rgba_size) {
    if (!ctx || !ctx->context || !blocks || !out_rgba) return 1;

    astcenc_image img{};
    img.dim_x = w;
    img.dim_y = h;
    img.dim_z = 1;
    img.data_type = ASTCENC_TYPE_U8;

    void* slice0 = (void*)out_rgba;
    img.data = &slice0;

    astcenc_swizzle swz { ASTCENC_SWZ_R, ASTCENC_SWZ_G, ASTCENC_SWZ_B, ASTCENC_SWZ_A };

    astcenc_error err = astcenc_decompress_image(
            ctx->context,
            blocks,
            blocks_size,
            &img,
            &swz,
            0
    );

    return (err == ASTCENC_SUCCESS) ? 0 : 2;
}
