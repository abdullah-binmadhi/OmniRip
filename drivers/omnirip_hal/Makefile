CC = clang
SYSROOT = $(shell xcrun --sdk macosx --show-sdk-path)
CFLAGS = -O3 -Wall -Wextra -arch arm64 -isysroot $(SYSROOT) -std=c11
LDFLAGS = -bundle -framework CoreAudio -framework CoreFoundation

DRIVER_NAME = OmniRipAudio
BUNDLE = $(DRIVER_NAME).driver
CONTENTS_DIR = $(BUNDLE)/Contents
MACOS_DIR = $(CONTENTS_DIR)/MacOS

.PHONY: all clean install

all: $(BUNDLE)

$(BUNDLE): OmniRipAudio.c OmniRipAudio.h Info.plist
	@mkdir -p $(MACOS_DIR)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $(MACOS_DIR)/$(DRIVER_NAME) OmniRipAudio.c
	cp Info.plist $(CONTENTS_DIR)/Info.plist
	codesign -s - --force --deep $(BUNDLE)
	@echo "Build successful: $(BUNDLE)"

clean:
	rm -rf $(BUNDLE)
