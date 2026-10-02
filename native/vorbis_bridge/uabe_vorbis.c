#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <vorbis/vorbisfile.h>

#ifndef UABE_API
#define UABE_API __attribute__((visibility("default"), used))
#endif

typedef struct {
    const unsigned char *data;
    long size;
    long pos;
} MemSource;

static size_t mem_read(void *ptr, size_t size, size_t nmemb, void *src) {
    MemSource *m = (MemSource *)src;
    long left = m->size - m->pos;
    if (left <= 0 || size == 0) {
        return 0;
    }
    size_t want = size * nmemb;
    size_t take = want < (size_t)left ? want : (size_t)left;
    memcpy(ptr, m->data + m->pos, take);
    m->pos += (long)take;
    return take / size;
}

static int mem_seek(void *src, ogg_int64_t offset, int whence) {
    MemSource *m = (MemSource *)src;
    ogg_int64_t base;
    switch (whence) {
        case SEEK_SET: base = 0; break;
        case SEEK_CUR: base = m->pos; break;
        case SEEK_END: base = m->size; break;
        default: return -1;
    }
    ogg_int64_t target = base + offset;
    if (target < 0 || target > m->size) {
        return -1;
    }
    m->pos = (long)target;
    return 0;
}

static int mem_close(void *src) {
    (void)src;
    return 0;
}

static long mem_tell(void *src) {
    return ((MemSource *)src)->pos;
}

static int open_mem(OggVorbis_File *vf, MemSource *m) {
    ov_callbacks cb;
    cb.read_func = mem_read;
    cb.seek_func = mem_seek;
    cb.close_func = mem_close;
    cb.tell_func = mem_tell;
    return ov_open_callbacks(m, vf, NULL, 0, cb);
}

UABE_API int uabe_vorbis_info(const unsigned char *data, long size, int *channels, long *rate,
                              long long *frames) {
    MemSource m = { data, size, 0 };
    OggVorbis_File vf;
    if (open_mem(&vf, &m) < 0) {
        return -1;
    }
    vorbis_info *vi = ov_info(&vf, -1);
    if (vi == NULL) {
        ov_clear(&vf);
        return -2;
    }
    *channels = vi->channels;
    *rate = vi->rate;
    *frames = (long long)ov_pcm_total(&vf, -1);
    ov_clear(&vf);
    return 0;
}

UABE_API long long uabe_vorbis_decode(const unsigned char *data, long size, short *out,
                                      long long max_frames) {
    MemSource m = { data, size, 0 };
    OggVorbis_File vf;
    if (open_mem(&vf, &m) < 0) {
        return -1;
    }
    vorbis_info *vi = ov_info(&vf, -1);
    if (vi == NULL) {
        ov_clear(&vf);
        return -2;
    }
    long long frame_bytes = (long long)vi->channels * 2;
    long long frames = 0;
    int bitstream = 0;
    char *dst = (char *)out;
    while (frames < max_frames) {
        long long room = (max_frames - frames) * frame_bytes;
        long want = room > 4096 ? (long)(4096 - (4096 % frame_bytes)) : (long)room;
        long n = ov_read(&vf, dst + frames * frame_bytes, want, 0, 2, 1, &bitstream);
        if (n == 0) {
            break;
        }
        if (n < 0) {
            if (n == OV_HOLE) {
                continue;
            }
            break;
        }
        frames += n / frame_bytes;
    }
    ov_clear(&vf);
    return frames;
}
