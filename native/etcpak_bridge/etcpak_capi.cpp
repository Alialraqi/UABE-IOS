#include "etcpak_capi.h"

#include <vector>
#include <cstring>
#include <cstdlib>

#include "ProcessDxtc.hpp"
#include "ProcessRGB.hpp"
#include "Decode.hpp"
#include "bc7enc.h"

static inline bool valid_dims(int w, int h) {
    return (w > 0 && h > 0 && (w % 4 == 0) && (h % 4 == 0));
}

static inline void rgba_to_bgra_u32(std::vector<uint32_t>& px) {

    for (size_t i = 0; i < px.size(); i++) {
        uint32_t p = px[i];
        px[i] = (p & 0xFF00FF00u) | ((p & 0x00FF0000u) >> 16) | ((p & 0x000000FFu) << 16);
    }
}

static inline int expect_out_4bpp(int w, int h) { return (w * h) / 2; }
static inline int expect_out_8bpp(int w, int h) { return (w * h); }
static inline int expect_out_rgba(int w, int h) { return (w * h) * 4; }

template <typename CompressFn>
static int compress_generic(
        const uint8_t* rgba,
        int w, int h,
        bool swap_rgba_to_bgra,
        int expected_out_bytes,
        CompressFn fn,
        uint8_t* out,
        int out_size
) {
    if (!rgba || !out) return 0;
    if (!valid_dims(w, h)) return 0;
    if (out_size < expected_out_bytes) return 0;

    const size_t pixels = (size_t)w * (size_t)h;

    std::vector<uint32_t> src(pixels);
    std::memcpy(src.data(), rgba, pixels * 4);

    if (swap_rgba_to_bgra) {
        rgba_to_bgra_u32(src);
    }

    std::vector<uint64_t> dst((size_t)expected_out_bytes / 8);
    fn(src.data(), dst.data(), (uint32_t)(pixels / 16), (size_t)w);

    std::memcpy(out, dst.data(), (size_t)expected_out_bytes);
    return 1;
}

template <typename DecodeFn>
static int decompress_generic(
        const uint8_t* data,
        int w, int h,
        int expected_in_bytes,
        DecodeFn fn,
        uint8_t* out_bgra,
        int out_size
) {
    if (!data || !out_bgra) return 0;
    if (!valid_dims(w, h)) return 0;
    if (out_size < expect_out_rgba(w, h)) return 0;

    std::vector<uint64_t> src((size_t)expected_in_bytes / 8);
    std::memcpy(src.data(), data, (size_t)expected_in_bytes);

    std::vector<uint32_t> dst((size_t)w * (size_t)h);
    fn(src.data(), dst.data(), w, h);

    std::memcpy(out_bgra, dst.data(), (size_t)expect_out_rgba(w, h));
    return 1;
}

static inline void bc7_init_once() {
    static bool inited = false;
    if (!inited) {
        bc7enc_compress_block_init();
        inited = true;
    }
}

int etcpak_compress_bc1(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size) {
    return compress_generic(rgba, w, h, false, expect_out_4bpp(w, h), CompressBc1, out, out_size);
}

int etcpak_compress_bc1_dither(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size) {
    return compress_generic(rgba, w, h, false, expect_out_4bpp(w, h), CompressBc1Dither, out, out_size);
}

int etcpak_compress_bc3(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size) {
    return compress_generic(rgba, w, h, false, expect_out_8bpp(w, h), CompressBc3, out, out_size);
}

int etcpak_compress_bc4(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size) {
    return compress_generic(rgba, w, h, false, expect_out_4bpp(w, h), CompressBc4, out, out_size);
}

int etcpak_compress_bc5(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size) {
    return compress_generic(rgba, w, h, false, expect_out_8bpp(w, h), CompressBc5, out, out_size);
}

int etcpak_compress_bc7(const uint8_t* rgba, int w, int h, const etcpak_bc7_params* params, uint8_t* out, int out_size) {
    if (!rgba || !out) return 0;
    if (!valid_dims(w, h)) return 0;

    const int expected = expect_out_8bpp(w, h);
    if (out_size < expected) return 0;

    bc7_init_once();

    const size_t pixels = (size_t)w * (size_t)h;
    std::vector<uint32_t> src(pixels);
    std::memcpy(src.data(), rgba, pixels * 4);

    std::vector<uint64_t> dst((size_t)expected / 8);

    if (params) {

        const bc7enc_compress_block_params* p = reinterpret_cast<const bc7enc_compress_block_params*>(params);
        CompressBc7(src.data(), dst.data(), (uint32_t)(pixels / 16), (size_t)w, p);
    } else {
        bc7enc_compress_block_params p;
        bc7enc_compress_block_params_init(&p);
        CompressBc7(src.data(), dst.data(), (uint32_t)(pixels / 16), (size_t)w, &p);
    }

    std::memcpy(out, dst.data(), (size_t)expected);
    return 1;
}

int etcpak_compress_etc1_rgb(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size) {

    return compress_generic(rgba, w, h, true, expect_out_4bpp(w, h), CompressEtc1Rgb, out, out_size);
}

int etcpak_compress_etc1_rgb_dither(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size) {
    return compress_generic(rgba, w, h, true, expect_out_4bpp(w, h), CompressEtc1RgbDither, out, out_size);
}

int etcpak_compress_etc2_rgb(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size) {
    auto fn = [](const uint32_t* src, uint64_t* dst, uint32_t blocks, size_t width) {
        CompressEtc2Rgb(src, dst, blocks, width, true );
    };
    return compress_generic(rgba, w, h, true, expect_out_4bpp(w, h), fn, out, out_size);
}

int etcpak_compress_etc2_rgba(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size) {
    auto fn = [](const uint32_t* src, uint64_t* dst, uint32_t blocks, size_t width) {
        CompressEtc2Rgba(src, dst, blocks, width, true );
    };
    return compress_generic(rgba, w, h, true, expect_out_8bpp(w, h), fn, out, out_size);
}

int etcpak_compress_eac_r(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size) {
    return compress_generic(rgba, w, h, true, expect_out_4bpp(w, h), CompressEacR, out, out_size);
}

int etcpak_compress_eac_rg(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size) {
    return compress_generic(rgba, w, h, true, expect_out_8bpp(w, h), CompressEacRg, out, out_size);
}

int etcpak_decompress_etc1_rgb(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size) {
    return decompress_generic(data, w, h, expect_out_4bpp(w, h), DecodeRGB, out_bgra, out_size);
}

int etcpak_decompress_etc2_rgb(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size) {
    return decompress_generic(data, w, h, expect_out_4bpp(w, h), DecodeRGB, out_bgra, out_size);
}

int etcpak_decompress_etc2_rgba(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size) {
    return decompress_generic(data, w, h, expect_out_8bpp(w, h), DecodeRGBA, out_bgra, out_size);
}

int etcpak_decompress_etc2_r11(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size) {
    auto fn = [](const uint64_t* src, uint32_t* dst, int32_t width, int32_t height) {
        DecodeR(src, dst, width, height);
    };
    return decompress_generic(data, w, h, expect_out_4bpp(w, h), fn, out_bgra, out_size);
}

int etcpak_decompress_etc2_rg11(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size) {
    auto fn = [](const uint64_t* src, uint32_t* dst, int32_t width, int32_t height) {
        DecodeRG(src, dst, width, height);
    };
    return decompress_generic(data, w, h, expect_out_8bpp(w, h), fn, out_bgra, out_size);
}

int etcpak_decompress_bc1(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size) {
    return decompress_generic(data, w, h, expect_out_4bpp(w, h), DecodeBc1, out_bgra, out_size);
}

int etcpak_decompress_bc3(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size) {
    return decompress_generic(data, w, h, expect_out_8bpp(w, h), DecodeBc3, out_bgra, out_size);
}

int etcpak_decompress_bc4(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size) {
    return decompress_generic(data, w, h, expect_out_4bpp(w, h), DecodeBc4, out_bgra, out_size);
}

int etcpak_decompress_bc5(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size) {
    return decompress_generic(data, w, h, expect_out_8bpp(w, h), DecodeBc5, out_bgra, out_size);
}

int etcpak_decompress_bc7(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size) {
    return decompress_generic(data, w, h, expect_out_8bpp(w, h), DecodeBc7, out_bgra, out_size);
}
