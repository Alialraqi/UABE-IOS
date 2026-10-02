class ASTCProfile:

    LDR_SRGB = 0
    LDR = 1
    HDR_RGB_LDR_A = 2
    HDR = 3


class ASTCType:

    U8 = 0
    F16 = 1
    F32 = 2


class ASTCConfigFlags:
    NONE = 0


    USE_DECODE_UNORM8 = 1 << 0

    DECOMPRESS_ONLY = 1 << 1
