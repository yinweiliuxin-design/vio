#include "pcm_rx.h"
#include "sv_resample.h"
#include "driver/i2s_std.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"
#include <string.h>
/* DMA input48kHz stereo32 ->44.1kHz stereo16 for default SBC source.
 * Linear147/160 converter is diagnostic, not a production anti-alias filter. */
static i2s_chan_handle_t rx;
static portMUX_TYPE lock=portMUX_INITIALIZER_UNLOCKED;
static int16_t ring[4096][2],previous[2],next[2];
static unsigned head,count,fraction;static bool enabled,primed;
static uint32_t underflows,last_input,overflows,read_errors,frames;
static void count_up(uint32_t *n,uint32_t amount){*n=UINT32_MAX-*n<amount?UINT32_MAX:*n+amount;}
static int16_t sample(uint32_t w){uint32_t v=w>>16;return (v&0x8000)?(int32_t)v-65536:(int16_t)v;}
void sv_esp_pcm_gate(bool on){portENTER_CRITICAL(&lock);if(enabled!=on){head=count=fraction=0;primed=false;}enabled=on;portEXIT_CRITICAL(&lock);}
static bool pop(int16_t *p){if(!count)return false;p[0]=ring[head][0];p[1]=ring[head][1];head=(head+1)%4096;count--;return true;}
static void reader(void *unused){
    (void)unused;uint32_t words[256];size_t n;
    for(;;){
        if(i2s_channel_read(rx,words,sizeof(words),&n,20)!=ESP_OK || !n || n>sizeof(words) || n%8){portENTER_CRITICAL(&lock);count_up(&read_errors,1);count=0;primed=false;portEXIT_CRITICAL(&lock);continue;}
        portENTER_CRITICAL(&lock);last_input=(uint32_t)(esp_timer_get_time()/1000);
        count_up(&frames,(uint32_t)(n/8));
        if(enabled){for(unsigned i=0;i+1<n/4;i+=2){if(count==4096){count_up(&overflows,1);count=0;primed=false;break;}unsigned at=(head+count)%4096;ring[at][0]=sample(words[i]);ring[at][1]=sample(words[i+1]);count++;}}
        portEXIT_CRITICAL(&lock);
    }
}
bool sv_esp_pcm_start(void){
    i2s_chan_config_t c=I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0,I2S_ROLE_SLAVE);c.dma_desc_num=4;c.dma_frame_num=128;
    if(i2s_new_channel(&c,NULL,&rx)!=ESP_OK)return false;
    i2s_std_config_t s={.clk_cfg=I2S_STD_CLK_DEFAULT_CONFIG(48000),
        .slot_cfg=I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT,I2S_SLOT_MODE_STEREO),
        .gpio_cfg={.mclk=I2S_GPIO_UNUSED,.bclk=26,.ws=25,.dout=I2S_GPIO_UNUSED,.din=22,.invert_flags={0}}};
    if(i2s_channel_init_std_mode(rx,&s)!=ESP_OK || i2s_channel_enable(rx)!=ESP_OK)return false;
    return xTaskCreate(reader,"sv_pcm",3072,NULL,8,NULL)==pdPASS;
}
int32_t sv_esp_pcm_read(uint8_t *out,int32_t bytes){
    if(!out || bytes<=0 || bytes>4096 || bytes%4)return 0;
    memset(out,0,(size_t)bytes);
    portENTER_CRITICAL(&lock);
    if(!enabled || (uint32_t)(esp_timer_get_time()/1000)-last_input>50){primed=false;count=0;portEXIT_CRITICAL(&lock);return bytes;}
    for(int i=0;i+3<bytes;i+=4){
        if(!primed){if(count<2){count_up(&underflows,1);break;}pop(previous);pop(next);fraction=0;primed=true;}
        for(unsigned ch=0;ch<2;ch++){
            int16_t v=sv_resample_lerp(previous[ch],next[ch],fraction);
            out[i+2*ch]=(uint8_t)v;out[i+2*ch+1]=(uint8_t)((uint16_t)v>>8);
        }
        fraction+=160;
        while(fraction>=147){fraction-=147;previous[0]=next[0];previous[1]=next[1];if(!pop(next)){primed=false;count_up(&underflows,1);break;}}
    }
    portEXIT_CRITICAL(&lock);return bytes;
}
uint32_t sv_esp_pcm_underflows(void){portENTER_CRITICAL(&lock);uint32_t n=underflows;portEXIT_CRITICAL(&lock);return n;}
void sv_esp_pcm_snapshot(sv_esp_pcm_stats *s){
    if(!s)return;
    portENTER_CRITICAL(&lock);
    *s=(sv_esp_pcm_stats){1,frames,underflows,overflows,read_errors,count,last_input,enabled};
    portEXIT_CRITICAL(&lock);
}
