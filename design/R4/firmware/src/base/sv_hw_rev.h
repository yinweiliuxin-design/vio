#ifndef SV_HW_REV_H
#define SV_HW_REV_H
/* Single board-revision switch (design/R4/eco/ECO-R4-schematic.md).
 * SV_HW_REV_R4=1 (default): R4 board with ECO E-02/E-03/E-04/E-11 fitted.
 * SV_HW_REV_R4=0: R3 board (behaviour of the R3 hardware stays reachable).
 * Build with EXTRA_CFLAGS="-DSV_HW_REV_R4=0" for an R3 board. */
#ifndef SV_HW_REV_R4
#define SV_HW_REV_R4 1
#endif
#if SV_HW_REV_R4
/* E-02: PACK/SYS dividers 2.2M/1.5M with 10M buffer load: 3.504/1.304 = 2.687.
 * USB divider (R1701/R1702/R1703) is unchanged at 2.65. High-Z input: settle >=100 ms. */
#define SV_MON_DIV_USB_X1000 2650
#define SV_MON_DIV_PACK_X1000 2687
#define SV_MON_SETTLE_MS 100u
/* E-03: PhotoMOS groups. PD14 HP_PORT_ENABLE (K1201/K1202), PD15 RET_PORT_ENABLE
 * (K1206/K1207); PA3 PORT_ENABLE keeps LINE L/R + FX SEND (K1203-K1205). */
#define SV_HAS_GROUPED_PORTS 1
/* E-04: R590 pulls EN1 up (USB500 default); firmware never sets EN2=1. */
#define SV_EN1_DEFAULT_HIGH 1
/* E-11: PB12 = PWR_PB_SENSE (BAS116 to PWR_PB), internal pull-up, active low. */
#define SV_HAS_PWR_PB_SENSE 1
#else
#define SV_MON_DIV_USB_X1000 2650
#define SV_MON_DIV_PACK_X1000 2650
#define SV_MON_SETTLE_MS 20u
#define SV_HAS_GROUPED_PORTS 0
#define SV_EN1_DEFAULT_HIGH 0
#define SV_HAS_PWR_PB_SENSE 0
#endif
#endif
