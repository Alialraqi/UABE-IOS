#pragma once
#ifndef UABE_API
#define UABE_API __attribute__((visibility("default"), used))
#endif
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

UABE_API int etcpak_compress_bc1(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size);
UABE_API int etcpak_compress_bc1_dither(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size);
UABE_API int etcpak_compress_bc3(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size);
UABE_API int etcpak_compress_bc4(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size);
UABE_API int etcpak_compress_bc5(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size);

typedef struct etcpak_bc7_params {
    uint32_t m_mode_mask;
    uint32_t m_max_partitions;
    uint32_t m_weights[4];
    uint32_t m_uber_level;
    uint8_t  m_perceptual;
    uint8_t  m_try_least_squares;
    uint8_t  m_mode17_partition_estimation_filterbank;
    uint8_t  m_force_alpha;
    uint8_t  m_force_selectors;
    uint8_t  m_selectors[16];
    uint8_t  m_quant_mode6_endpoints;
    uint8_t  m_bias_mode1_pbits;
    float    m_pbit1_weight;
    float    m_mode1_error_weight;
    float    m_mode5_error_weight;
    float    m_mode6_error_weight;
    float    m_mode7_error_weight;
} etcpak_bc7_params;

UABE_API int etcpak_compress_bc7(const uint8_t* rgba, int w, int h, const etcpak_bc7_params* params, uint8_t* out, int out_size);

UABE_API int etcpak_compress_etc1_rgb(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size);
UABE_API int etcpak_compress_etc1_rgb_dither(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size);
UABE_API int etcpak_compress_etc2_rgb(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size);
UABE_API int etcpak_compress_etc2_rgba(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size);
UABE_API int etcpak_compress_eac_r(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size);
UABE_API int etcpak_compress_eac_rg(const uint8_t* rgba, int w, int h, uint8_t* out, int out_size);

UABE_API int etcpak_decompress_etc1_rgb(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size);
UABE_API int etcpak_decompress_etc2_rgb(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size);
UABE_API int etcpak_decompress_etc2_rgba(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size);
UABE_API int etcpak_decompress_etc2_r11(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size);
UABE_API int etcpak_decompress_etc2_rg11(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size);

UABE_API int etcpak_decompress_bc1(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size);
UABE_API int etcpak_decompress_bc3(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size);
UABE_API int etcpak_decompress_bc4(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size);
UABE_API int etcpak_decompress_bc5(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size);
UABE_API int etcpak_decompress_bc7(const uint8_t* data, int w, int h, uint8_t* out_bgra, int out_size);

#ifdef __cplusplus
}
#endif
