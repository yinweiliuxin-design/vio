idf_component_register(SRCS "main.c"
                            "audio.c"
                            "params.c"
                            "codec.c"
                            "codec_aic3204.c"
                            "codec_es8388.c"
                            "i2c_bus.c"
                            "console_cmds.c"
                            "ui.c"
                            "ble.c"
                            "btmod.c"
                            "tuner_task.c"
                       INCLUDE_DIRS "."
                       REQUIRES r5dsp esp_driver_i2s esp_driver_i2c esp_driver_gpio esp_driver_pcnt
                                esp_driver_uart console nvs_flash esp_timer bt freertos log)
target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra -Wno-unused-parameter)
