# Pure C DSP library shared by the firmware and the host unit tests.
idf_component_register(SRCS "src/biquad.c"
                            "src/reverb.c"
                            "src/limiter.c"
                            "src/mixlaw.c"
                            "src/engine.c"
                            "src/tuner.c"
                            "src/clickdet.c"
                       INCLUDE_DIRS "include")
target_compile_options(${COMPONENT_LIB} PRIVATE -O2 -Wall -Wextra)
