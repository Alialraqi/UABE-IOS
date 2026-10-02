#ifndef UABE_API
#define UABE_API __attribute__((visibility("default"), used))
#endif
#include <stdint.h>
#include <stddef.h>

#include "bcn.h"
#include "etc.h"
#include "atc.h"
#include "astc.h"
#include "pvrtc.h"
#include "crunch.h"
#include "unitycrunch.h"

extern "C" {

UABE_API int t2d_decode_bc1(const uint8_t* data, long w, long h, uint32_t* out) { return decode_bc1(data, w, h, out) != 0; }
UABE_API int t2d_decode_bc3(const uint8_t* data, long w, long h, uint32_t* out) { return decode_bc3(data, w, h, out) != 0; }

UABE_API int t2d_decode_bc4(const uint8_t* data, uint32_t w, uint32_t h, uint32_t* out) { return decode_bc4(data, w, h, out) != 0; }
UABE_API int t2d_decode_bc5(const uint8_t* data, uint32_t w, uint32_t h, uint32_t* out) { return decode_bc5(data, w, h, out) != 0; }
UABE_API int t2d_decode_bc6(const uint8_t* data, uint32_t w, uint32_t h, uint32_t* out) { return decode_bc6(data, w, h, out) != 0; }
UABE_API int t2d_decode_bc7(const uint8_t* data, uint32_t w, uint32_t h, uint32_t* out) { return decode_bc7(data, w, h, out) != 0; }

UABE_API int t2d_decode_etc1(const uint8_t* data, long w, long h, uint32_t* out) { return decode_etc1(data, w, h, out) != 0; }
UABE_API int t2d_decode_etc2(const uint8_t* data, long w, long h, uint32_t* out) { return decode_etc2(data, w, h, out) != 0; }
UABE_API int t2d_decode_etc2a1(const uint8_t* data, long w, long h, uint32_t* out) { return decode_etc2a1(data, w, h, out) != 0; }
UABE_API int t2d_decode_etc2a8(const uint8_t* data, long w, long h, uint32_t* out) { return decode_etc2a8(data, w, h, out) != 0; }

UABE_API int t2d_decode_eacr(const uint8_t* data, long w, long h, uint32_t* out) { return decode_eacr(data, w, h, out) != 0; }
UABE_API int t2d_decode_eacr_signed(const uint8_t* data, long w, long h, uint32_t* out) { return decode_eacr_signed(data, w, h, out) != 0; }
UABE_API int t2d_decode_eacrg(const uint8_t* data, long w, long h, uint32_t* out) { return decode_eacrg(data, w, h, out) != 0; }
UABE_API int t2d_decode_eacrg_signed(const uint8_t* data, long w, long h, uint32_t* out) { return decode_eacrg_signed(data, w, h, out) != 0; }

UABE_API int t2d_decode_atc_rgb4(const uint8_t* data, uint32_t w, uint32_t h, uint32_t* out) { return decode_atc_rgb4(data, w, h, out) != 0; }
UABE_API int t2d_decode_atc_rgba8(const uint8_t* data, uint32_t w, uint32_t h, uint32_t* out) { return decode_atc_rgba8(data, w, h, out) != 0; }

UABE_API int t2d_decode_astc(const uint8_t* data, long w, long h, int bw, int bh, uint32_t* out) {
    return decode_astc(data, w, h, bw, bh, out) != 0;
}

UABE_API int t2d_decode_pvrtc(const uint8_t* data, long w, long h, uint32_t* out, int is2bpp) {
    return decode_pvrtc(data, w, h, out, is2bpp) != 0;
}

UABE_API int t2d_unpack_crunch(const uint8_t* data, uint32_t data_size, uint32_t level_index, uint8_t** out_ptr, uint32_t* out_size) {
    void* ret = nullptr;
    uint32_t ret_size = 0;
    bool ok = crunch_unpack_level(data, data_size, level_index, &ret, &ret_size);
    if (!ok || !ret) return 0;
    *out_ptr = (uint8_t*)ret;
    *out_size = ret_size;
    return 1;
}

UABE_API int t2d_unpack_unity_crunch(const uint8_t* data, uint32_t data_size, uint32_t level_index, uint8_t** out_ptr, uint32_t* out_size) {
    void* ret = nullptr;
    uint32_t ret_size = 0;
    bool ok = unity_crunch_unpack_level(data, data_size, level_index, &ret, &ret_size);
    if (!ok || !ret) return 0;
    *out_ptr = (uint8_t*)ret;
    *out_size = ret_size;
    return 1;
}

UABE_API void t2d_free(void* p) {
    if (!p) return;
    delete[] (uint8_t*)p;
}

}
