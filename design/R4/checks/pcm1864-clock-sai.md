# PCM1864 (U601) 时钟与数据通路端到端核查

依据：
- 原生网表 `PKG/engineering/verification/independent/native-netlist.xml`
- 主板 PCB `SmartVio-main-r3-linked.kicad_pcb`
- 实际参与编译的固件：`firmware/stm32/main.c`（build.py:80），以及 `base/stm32/audio_hw.c`、`base/sv_pcm1864.c`、`base/sv_sai_contract.h`、`base/sv_factory.c`
- 契约文件：`base/contracts/{adc-dual-i2s,clocks,pins,power-audio}.json`
- HAL：`vendor-source/stm32h7xx-hal-driver-1.11.4`
- PCM1864 数据手册 TI SLAS831D 全文提取件：`SCRATCH/agents/gap-pcm1864/ds/slas831d.txt`。该文件不在 PKG/references 中，但文本完整，下文页码均为手册页码。
- 辅助脚本：`SCRATCH/agents/pcm1864/*.py`

## (a) 已核查且正确的部分

| 项目 | 结论与证据 |
|---|---|
| 时钟树 | HSE 24.576 MHz（Y801→PH0/PH1）经 PLL2 得到：M=6，参考 4.096 MHz（RGE_2）；N=96，VCO 393.216 MHz；P=8，49.152 MHz；FRACN=0（audio_hw.c:53-57）。SAI1 和 SAI2/3 的内核时钟都取 PLL2P=49.152 MHz（:54-55）。MCO2 取 PLL2P/2=24.576 MHz（:59），即 48 kHz 下的 **512 fs**。:65-71 对 PLLCKSELR/PLLCFGR/PLL2DIVR/D2CCIP1R/CFGR 做了寄存器级断言。SAI 位时钟和 SCKI 来自同一个 PLL，相位锁定，不会漂移。 |
| SAI 分频 | CR1 设 NODIV=1、MCKDIV=16（audio_hw.c:83-84，HAL_SAI_Init 直接使用 Mckdiv）。BCK=49.152/16=3.072 MHz=64 fs，FS=3.072 MHz/64=**48 kHz**。HAL 1.11.4 的 stm32h7xx_hal_sai.c:612-639 注释写明 NODIV=1 时 MCKDIV=ker/(FS·(FRL+1))，与 sv_sai_contract.h:10-21 一致。契约中 CR1 的期望值 0x010822E1/0x010826E3/0x010822E0/0x010826E2 与 sv_sai_cr1() 逐位相符。 |
| PCM1864 对 512 fs 的支持 | SLAS831D p41 Table 10（4 通道器件）在 48 kHz、SCK 512 fs、24.576 MHz 时 PLL 关闭，DSP1=SCK/1，DSP2=SCK/2，ADC=SCK/4。这是最佳工作点。SCKI 为 3.3 V CMOS，范围 1–50 MHz（p16）。 |
| CLK_CFG0 0x20 写 0x41（sv_pcm1864.c:9） | p124 Table 54：bit7:6 SCK_XI_SEL=01 表示只用 SCK；MST_MODE=0 表示从模式；CLKDET_EN=1 表示自动时钟检测。Linux pcm186x.h:176-183 的位定义与此相同。**结论：findings_digest 中的 FW-PCM1864-CLKCFG 不是缺陷，应关闭。** XI 经 R601 接地，选 SCK 后 XI 被忽略。（置信度：高，依据手册原文） |
| 主从关系与比例 | SAI1_A 为主接收端，输出 BCK/LRCK（PE5→R811→U601.17，PE4→R810→U601.16）。SAI1_B 为同步从接收端（audio_hw.c:81-82）。PCM1864 为从模式。BCK/fs=64。状态回读 0x74 应为 0x34（BCK_RATIO=011 对应 64，SCK_RATIO=100 对应 512，p127），0x73=3 表示 32–48 kHz（p126），0x75=0 表示无时钟错误，0x72=0xF 表示 RUN，0x78=7 表示电源正常。sv_pcm1864.c:55-56 和 main.c:299-304 按这组值周期检查，正确。 |
| 时钟沿 | HAL 的 SAI_InitI2S 对 RX 用 RISINGEDGE、对 TX 用 FALLINGEDGE（hal_sai.c:2297-2309），两者都得到 CKSTR=1：输出在 BCK 下降沿变化，输入在上升沿采样。PCM1864 在 BCK 下降沿送出 DOUT，在上升沿采样 LRCK，配合正确。FRCR=0x00051F3F，即 FRL=63、FSALL=31、FSDEF=1、FSPOL=0（低电平为左）、FSOFF=1（1 BCK 延迟），是标准 I2S。SLOTR=0x00030180，即 2 个 32 位 slot，使能 slot 0 和 1。 |
| 引脚与网表 | PE3=SAI1_SD_B←ADC_DATA2←R691←U601.21 GPIO1；PE6=SAI1_SD_A←U601.18 DOUT；PC9=MCO2→R812→U601.15 SCKI；PD11/12/13、PE11 为 SAI2 AF10。PCB 焊盘网络与网表逐一核对一致（U801.2/3/4/5/41/58/59/60/66，R810–R815/R691/R906，U601 各脚）。 |
| I2C | MD0=GND 选 I2C，MS/AD=GND 时 8 位地址为 0x94，即 7 位地址 0x4A（p11、p64）。驱动里 codec 地址为 0x4a（i2c_probe.c:98-99）。ADS1115 地址 0x48，TMP117 的 ADD0 接 V3D 得 0x49，没有冲突。U1902 TMUX1511PW 的引脚 1/2/3/4/5/6=SEL1/S1/D1/SEL2/S2/D2，与 TI 引脚表一致（网络检索，置信度中高）；VDD=V3D，SEL 由 PC13 控制，R1913 下拉。 |
| 输入映射 | VINL1=ADC_PU_AC（拾音）、VINR1=AUX_L、VINL3=AUX_R（网表 U601.3/4/29）。寄存器写入：0x06=VINL1、0x07=VINR1、0x08=VINL3、0x09=0（p91-94，掩码 0xBF 保留 RSV 位）。混音器单位系数写在 0x00/0x07/0x0E/0x15，即 MIX1_CH1L、MIX2_CH1R、MIX3_CH2L、MIX4_CH2R（p69 Table 24），系数 0x100000 在 4.20 格式下等于 1.0。仲裁器的两次哑写和 BUSY/REQ 轮询符合 p68 §9.5.5。DOUT2 由 GPIO1_FUNC=101 输出（0x10=0x5x，p98），0x15 bit5 关闭 GPIO1 下拉。TX_WLEN=00 为 32 位，FMT=I2S（0x0B，p95）。0x71 最终为 0x08，即 4 通道模式、HPF 开、只静音 CH2R（p125）。sv_factory.c:78/88 取高 24 位并做符号扩展；a[2n]=拾音、a[2n+1]=AUX_L、b[2n]=AUX_R，与上述映射一致。 |
| SAI/DMA | DMA1 S0–S3 循环模式、字宽传输，每块 256 字，半块为 64 帧，即 1.333 ms。缓冲放在 .dma 段 0x30000000（D2 SRAM1，链接脚本 stm32h743vi.ld:7/21，map:5321），D-cache 关闭。启动顺序是先使能同步从块 B、再使能主块 A（:115-119），符合 RM 要求。 |
| 播放侧采样率一致 | SAI2_A 为 48 kHz/64 fs/32 位主发送端，驱动 PLAY_BCK/FS/DATA，接到 U701 PCM5102A（SCK 脚 12 接地，用 BCK 内部 PLL；FMT 接地，为 I2S）、U902 MAX98357A 和 U901 ESP32 的 IO26/IO25/IO22。ESP32 侧为 I2S_ROLE_SLAVE、48000、32 位 Philips（pcm_rx.c:30-34）。SAI2_B 为同步发送端，输出 SPK_DATA，只写左 slot（sv_speaker.c）；MAX98357A 的 SD_MODE 由 2k/100k 分压约 3.2 V（>1.4 V），选左声道，两者一致。 |
| 上下电时序 | 上电：PE2 打开 V3LOAD（main.c:281），等 50 ms（:284），PC13 打开 AUDIO_BUS_EN（:287），再启动 MCO2 和 SAI（:288），然后在时钟运行状态下配置 codec（:289）。手册要求 DSP 有时钟才能写系数（p68），满足。下电：先 PC13=0（:104），再停 SAI/PLL2 并把引脚设为模拟态（:105，audio_hw.c:123-130），最后 PE2=0，顺序正确。 |
| 契约与代码 | clocks.json 和 adc-dual-i2s.json 中的 PLL2、MCO2、MCKDIV、FRL、CR1/FRCR/SLOTR 期望值、寄存器意图（0x06–0x0D/0x10/0x15/0x20/0x71）和状态检查值，与代码一致。只有一处文档缺口，见 PCM-06。 |

时序裕量：BCK 半周期 163 ns，PCM1864 的 tCKDO ≤40 ns，tLRSU ≥50 ns（p19）。PCB 走线长度：ADC_BCK 54 mm，ADC_FS 61 mm，ADC_DATA 15 mm，ADC_DATA2 20 mm，加上源端 33 Ω，传播延迟在 1 ns 量级，建立和保持裕量都大于 90 ns。

## (b) 新发现

### PCM-01 增益级：PGA 固定 0 dB，固件再除以 16，拾音器满幅输入也只能输出约 −24 dBFS（medium）
- 证据：
  - sv_pcm1864.c:6 把 0x01–0x04 写成 0x00，即 PGA 0 dB（p89-90）。
  - 拾音前级 U101A 是单位增益跟随器（U101.1=U101.2=PU_BUF），经 R111/C111 直接接入 VINL1。
  - sv_factory.c:88 对 pickup、rl、rr 都再除以 16（−24 dB）。
  - sv_ui.c:47-48 的音量增益最大为 1.0，之后没有任何增益。
- 后果：以 ADC 满幅 2.1 Vrms 为基准，DAC 输出最大只有 −24 dBFS。压电拾音通常只有几十到几百 mVrms，实际线路和耳机输出会落在 −45 到 −60 dBFS，音量明显不足。ADC 前端只用到 0 dB，也浪费了 PGA 最高 +40 dB 的低噪声增益，SNR 下降。这一点与 SCH-HP-LEVEL（硬件最大幅度）互相独立。
- 修复（固件）：
  - 实测拾音电平后设置 0x01 PGA_VAL_CH1_L，例如 +20 dB 写 0x28，+12 dB 写 0x18。AUX 通道（0x02/0x03）按线路电平保持 0 dB。
  - 去掉 `/16`，改为 `pickup=sv_sample24(a[2n])`。如需为效果预留余量，用 1/2 并在 sv_ui_process 之后加限幅。
  - 如果实测 PGA 增益之后出现削波，可以开启 0x05 AGC_EN 或 DPGA_CLIP_EN。
- 置信度：中。寄存器和代码事实确定；拾音器实际电平未知。

### PCM-02 没有软件复位：PCM186x 没有复位脚，也没有掉电检测，配置完全依赖上电复位（low）
- 证据：
  - SLAS831D p79 §11.3 原文："do not have a brownout detector, or a reset pin"；p85："Reset registers by writing 0xFE to register 0x00"。
  - sv_pcm1864.c:23 第 0 步只写了 page=0，没有写 0xFE；配置采用读-改-写（:27-29），会保留未知的旧位。
  - Linux 驱动 pcm186x.c:677-678 探测时第一步就写 0xFE。
- 后果：如果 V3LOAD 关断时被跨域引脚反灌，没有完全掉到 0（见 SCH-XDOMAIN-DIRECT 和 PCM-03），PCM1864 就不会重新上电复位。配置列表之外的寄存器（0x19 增益映射、0x70 电源状态、page3 OSC 等）会保留旧值。下电与再上电之间的间隔不足（V3LOAD 放电约 1k×数十 µF）也有同样问题。
- 修复（固件）：phase 0 改为先写 `0x00=0xFE`，等待 ≥1 ms，再写 `0x00=0x00`，然后进入 phase 1。例如在 sv_pcm1864.c:23 增加一个子步骤。
- 置信度：中。

### PCM-03 HardFault/NMI 只关了 PE2，MCO2（24.576 MHz）和 SAI1/SAI2 时钟仍在驱动已断电的 V3LOAD 域，最长约 2 s（low）
- 证据：
  - main.c:231 的 HardFault_Handler 只做了 emergency_mute、PC13=0、PE2=0，然后 `for(;;)`，没有停 PLL2 和 MCO2，也没有把 PC9/PE3-6/PD11-13/PE11 设为模拟态。
  - 看门狗按 main.c:235 的 IWDG 预分频 256、重载 249 计算，约 2.0 s 后才复位。
- 后果：SCKI、BCK、LRCK 方波经 33 Ω 和 ESD 二极管灌入 U601、U701 和 ESP32 的 IO25/26/22，V3LOAD 被抬到中间电平。这会加重 PCM-02（器件得不到干净的 POR），也有闩锁风险。属于 SCH-XDOMAIN-DIRECT 在时钟线上的具体实例。
- 修复（固件）：在 HardFault_Handler 开头先执行 `RCC->CR&=~RCC_CR_PLL2ON;`（SAI 内核时钟和 MCO2 同时停止），再把 `GPIOC->MODER|=3u<<18; GPIOE->MODER|=(0xffu<<6)|(3u<<22); GPIOD->MODER|=0x3fu<<22;` 设为模拟态，最后才拉低 PE2。
- 置信度：高（代码事实）。反灌幅度未实测。

### PCM-04 版图：真正的 24.576 MHz 主时钟走线较长，XI 用一根 46.7 mm 的线接到远处的 0R 接地（low）
- 证据（脚本 seg.py/xt.py 扫描主板）：
  - ADC_SCK_SRC 12.4 mm 加 ADC_SCK 44.7 mm，共约 57 mm、7 个过孔，其中 In3/In4 段约 16 mm（与 PCB-09 一致：In3/In4 没有相邻参考平面）。ADC_SCK 与 V3A（PCM1864 AVDD 一路）同层平行约 6.8 mm。ADC_DATA2 与 SEND_BUF 同层平行约 8.2 mm。
  - R601 在 (4.8, 31.8) B.Cu，U601 在 (12, 7.8)，两者相距约 25 mm。ADC_XI 长 46.7 mm、6 个过孔，大部分在 In2。
- 后果：XI 不是一个干净的地。在 0x20 写入 SCK_XI_SEL=01 之前（上电后约 50 ms 内，默认是 "SCK or XTAL" 相或），XI 上的感应噪声理论上可能叠加到时钟上；配置完成后无影响。时钟谐波耦合到 AVDD 走线属于底噪风险。这一条是对 PCB-09 复核结论（"ADC_XI 起屏蔽作用"）的修正，并给出了真正的时钟走线。
- 修复（ECO，下一版版图）：XI 在 U601.10 旁直接打孔接 DGND，或把 R601 挪到 XI 脚旁；ADC_SCK 改走 F 层或 In2/In5（紧邻 GND 平面），缩短并远离 V3A 和模拟线；ADC_DATA2 与 SEND_BUF 拉开 ≥3W。当前版本靠固件把 0x20 写成 0x41 已足够，可以把这条写进 bring-up 检查项。
- 置信度：中。

### PCM-05 MCO2 作 ADC 主时钟，抖动没有任何规格或验证（info）
- 证据：
  - clocks.json 的 "unverified" 列表包括 "MCO loading and EMC at 24.576MHz"。
  - PLL2 为整数模式（FRACN=0，audio_hw.c:57）。HAL_RCC_MCOConfig 把 PC9 设为 VERY_HIGH 驱动。
  - 512 fs 时 PCM1864 关闭内部 PLL，ADC 时钟直接取 SCKI/4（p41），SCKI 的抖动会直接进入采样。
- 后果：估算在 30–50 ps rms 时，20 kHz 处的抖动极限 SNR 约为 104–108 dB，与 PCM1864 的 103 dB 相当，可能吃掉 1–3 dB 指标。VERY_HIGH 驱动加 57 mm 走线也会增大 EMI。
- 修复：bring-up 时测 SCKI 的相位噪声和 ADC 空闲 SNR。如果不达标，下一版改用独立的 24.576 MHz 有源晶振，同时供 SCKI 和 STM32 HSE（bypass）。固件可以在 MCOConfig 之后把 PC9 的 OSPEEDR 降为 MEDIUM 来减小边沿陡度。
- 置信度：低到中（STM32 PLL 抖动数据未在包内核实）。

### PCM-06 契约文档漏记 PGA 和 0x05 的写入（info）
- 证据：代码 sv_pcm1864.c:6 写入 0x01–0x04=0x00，并对 0x05 按掩码 0x41 写 0（关闭 LINK 和 AGC）；但 adc-dual-i2s.json:208-275 和 power-audio.json 的 pcm1864RoutingCandidate.page0 都没有列出这几项。
- 修复：把 0x01–0x05 补进契约。若按 PCM-01 调整增益，也要同步更新契约。
- 置信度：高。

## 对既有发现的处理
- **FW-PCM1864-CLKCFG（info，未定）**：关闭。0x41 的含义是 SCK_XI_SEL=01，即只用 SCKI，与硬件接法一致（p124）。
- **PCB-09**："ADC_XI 是屏蔽"的说法不准确，实际时钟是 ADC_SCK，见 PCM-04。
- **SCH-XDOMAIN-DIRECT**：在时钟线上的补充见 PCM-03。
