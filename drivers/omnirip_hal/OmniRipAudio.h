#ifndef OMNIRIP_AUDIO_H
#define OMNIRIP_AUDIO_H

#include <CoreAudio/AudioHardware.h>
#include <CoreAudio/AudioServerPlugIn.h>
#include <CoreFoundation/CoreFoundation.h>
#include <pthread.h>
#include <stdalign.h>
#include <stdatomic.h>
#include <stdint.h>

// OmniRip Audio Constants (v2 Output-Only Zero-Dot HAL)
#define kOmniRip_Device_UID "com.omnirip.driver.audio"
#define kOmniRip_Device_Model_UID "com.omnirip.driver.audio.model"
#define kOmniRip_Box_UID "com.omnirip.driver.audio.box"
#define kOmniRip_Device_Name "OmniRip Audio"
#define kOmniRip_Manufacturer "OmniRip Audio Technologies"

#define kOmniRip_RingBufferFrames 32768u
#define kOmniRip_Channels 2u

// POSIX Shared Memory Ring Contract (must match src/dsp/shm_capture.rs)
#define kOmniRip_ShmName "/omnirip_audio_shm"
#define kOmniRip_ShmMagic 0x4F4D5348u // "OMSH"
#define kOmniRip_ShmVersion 2u

// Object IDs (strictly Output-Only: zero Input stream objects so macOS never flags a mic)
enum {
    kObjectID_PlugIn = 1,
    kObjectID_Device = 2,
    kObjectID_Stream_Output = 3,
    kObjectID_Volume_Output_Master = 5,
    kObjectID_Mute_Output_Master = 6,
    kObjectID_Box = 7
};

// Cacheline-aligned shared memory ring buffer between coreaudiod (sole writer) and omnirip (O_RDONLY consumer).
typedef struct __attribute__((aligned(64))) OmniRipShmRing {
    uint32_t         magic;
    uint32_t         version;
    uint32_t         channels;
    uint32_t         capacity_frames;
    _Atomic uint32_t sample_rate_hz;
    _Atomic uint32_t volume_bits;
    _Atomic uint32_t is_muted;
    _Atomic uint32_t io_running;
    _Atomic uint64_t write_cursor;
    _Atomic uint64_t heartbeat_ns;
    uint8_t          _pad[16];
    float            frames[kOmniRip_RingBufferFrames * kOmniRip_Channels];
} OmniRipShmRing;

_Static_assert(sizeof(OmniRipShmRing) == 64 + (kOmniRip_RingBufferFrames * kOmniRip_Channels * sizeof(float)),
               "OmniRipShmRing header must be exactly 64 bytes followed by interleaved f32 stereo frames");

// Global Driver State
typedef struct OmniRipDriverState {
    AudioServerPlugInHostRef host;
    UInt32 ref_count;

    // Sample Rate
    Float64 sample_rate;

    // Volume & Mute Controls
    Float32 volume_scalar;
    UInt32 is_muted;

    // CoreAudio Synchronous Real-Time IO State
    UInt32 io_is_running;
    Float64 host_ticks_per_frame;
    UInt64 number_timestamps;
    UInt64 anchor_host_time;
    Float64 previous_ticks;
    pthread_mutex_t io_mutex;

    // Shared memory ring mapped inside coreaudiod
    int shm_fd;
    OmniRipShmRing* shm_ring;
} OmniRipDriverState;

#endif // OMNIRIP_AUDIO_H
