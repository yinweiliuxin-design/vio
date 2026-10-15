#ifndef SV_SAFETY_HAL_MODEL_H
#define SV_SAFETY_HAL_MODEL_H
/* GPIO layout comes from pinned ST CMSIS. The HAL/NVIC API below is a host
 * semantic shim, NOT electrical EXTI, NVIC scheduling, or timing simulation. */
#include "i2c-model-device.h"
extern GPIO_TypeDef sv_fake_gpioa,sv_fake_gpioc,sv_fake_gpiod,sv_fake_gpioe;
#define GPIOD (&sv_fake_gpiod)
#define GPIOA (&sv_fake_gpioa)
#define GPIOC (&sv_fake_gpioc)
#define GPIOE (&sv_fake_gpioe)
#define GPIO_PIN_2 (1u<<2)
#define GPIO_PIN_4 (1u<<4)
#define GPIO_MODE_IT_FALLING 1u
#define GPIO_NOPULL 0u
#define EXTI4_IRQn 10
typedef struct {uint32_t Pin,Mode,Pull,Speed,Alternate;} GPIO_InitTypeDef;
extern uint32_t sv_model_pending,sv_model_primask;
void HAL_GPIO_Init(GPIO_TypeDef *,GPIO_InitTypeDef *);
void HAL_NVIC_SetPriority(int,unsigned,unsigned);
void HAL_NVIC_EnableIRQ(int);
void sv_model_disable_irq(void);
#define __HAL_GPIO_EXTI_GET_IT(p) (sv_model_pending&(p))
#define __HAL_GPIO_EXTI_CLEAR_IT(p) (sv_model_pending&=~(p))
#define __get_PRIMASK() sv_model_primask
#define __disable_irq() sv_model_disable_irq()
#define __set_PRIMASK(p) (sv_model_primask=(p))
#define __DMB() ((void)0)
#endif
