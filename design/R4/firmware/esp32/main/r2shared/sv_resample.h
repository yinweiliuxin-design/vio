#ifndef SV_RESAMPLE_H
#define SV_RESAMPLE_H
#include <stdint.h>
static inline int16_t sv_resample_lerp(int16_t a,int16_t b,unsigned fraction){
    if(fraction>=147)return 0;
    return (int16_t)(((int32_t)a*(int32_t)(147-fraction)+(int32_t)b*(int32_t)fraction)/147);
}
#endif
