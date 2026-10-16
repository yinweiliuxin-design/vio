idf_component_register(SRCS "smartvio_rf.c" "r2shared/pcm_rx.c"
    "r2shared/sv_control.c" "r2shared/sv_radio_core.c"
    INCLUDE_DIRS "." "r2shared"
    REQUIRES bt nvs_flash esp_driver_uart esp_driver_i2s esp_timer)
