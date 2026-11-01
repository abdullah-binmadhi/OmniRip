# Builds OmniRipAudio.driver, the CoreAudio HAL plug-in. The bundle is universal (arm64 and x86_64),
# so Apple Silicon and Intel Macs both load it.
CC = clang
SYSROOT = $(shell xcrun --sdk macosx --show-sdk-path)
ARCHS = -arch arm64 -arch x86_64
CFLAGS = -O3 -Wall -Wextra $(ARCHS) -isysroot $(SYSROOT) -std=c11
LDFLAGS = -bundle -framework CoreAudio -framework CoreFoundation

DRIVER_NAME = OmniRipAudio
BUNDLE = $(DRIVER_NAME).driver
CONTENTS_DIR = $(BUNDLE)/Contents
MACOS_DIR = $(CONTENTS_DIR)/MacOS

.PHONY: all clean

all: $(BUNDLE)

$(BUNDLE): OmniRipAudio.c OmniRipAudio.h Info.plist
	@mkdir -p $(MACOS_DIR)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $(MACOS_DIR)/$(DRIVER_NAME) OmniRipAudio.c
	cp Info.plist $(CONTENTS_DIR)/Info.plist
	codesign -s - --force --deep $(BUNDLE)
	@echo "Build successful: $(BUNDLE)"

clean:
	rm -rf $(BUNDLE)
