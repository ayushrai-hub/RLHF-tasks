#ifndef CAP_LAYOUT_H
#define CAP_LAYOUT_H

#include <stdint.h>

#define CAP_MAX_ROWS 64
#define CAP_HEX_LEN 16

typedef struct {
    uint32_t effective;
    uint32_t bound;
    int nnp_active;
} cap_user_header_t;

typedef enum {
    CAP_FLAG_NONE = 0,
    CAP_FLAG_NNP = 1
} cap_flag_t;

typedef struct {
    char round[8];
    char actor[16];
    char mark[32];
    int class_tag;
    char cap_effective[CAP_HEX_LEN];
    char cap_bound[CAP_HEX_LEN];
    char gap_code[8];
    char launch_mark[32];
    unsigned stamp_code;
    unsigned seq_code;
    char effective_set_hash[65];
    char bound_set_hash[65];
} cap_row_t;

#endif
