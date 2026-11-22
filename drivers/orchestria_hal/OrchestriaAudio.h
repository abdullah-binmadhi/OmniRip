#ifndef ORCHESTRIA_AUDIO_H
#define ORCHESTRIA_AUDIO_H

#include <CoreAudio/AudioHardware.h>
#include <CoreAudio/AudioServerPlugIn.h>
#include <CoreFoundation/CoreFoundation.h>
#include <pthread.h>
#include <stdalign.h>
#include <stdatomic.h>
#include <stdint.h>

// Orchestria Audio Constants (v2 Output-Only Zero-Dot HAL)
#define kOrchestria_Device_UID "com.orchestria.driver.audio"
#define kOrchestria_Device_Model_UID "com.orchestria.driver.audio.model"
#define kOrchestria_Box_UID "com.orchestria.driver.audio.box"
#define kOrchestria_Device_Name "Orchestria Audio"
#define kOrchestria_Manufacturer "Orchestria Audio Technologies"

#define kOrchestria_RingBufferFrames 32768u
#define kOrchestria_Channels 2u

// POSIX Shared Memory Ring Contract (must match src/dsp/shm_capture.rs)
#define kOrchestria_ShmName "/orchestria_audio_shm"
#define kOrchestria_ShmMagic 0x4F4D5348u // "OMSH"
#define kOrchestria_ShmVersion 2u

// Object IDs (strictly Output-Only: zero Input stream objects so macOS never flags a mic)
enum {
    kObjectID_PlugIn = 1,
    kObjectID_Device = 2,
    kObjectID_Stream_Output = 3,
    kObjectID_Volume_Output_Master = 5,
    kObjectID_Mute_Output_Master = 6,
    kObjectID_Box = 7
};

// Cacheline-aligned shared memory ring buffer between coreaudiod (sole writer) and orchestria (O_RDONLY consumer).
typedef struct __attribute__((aligned(64))) OrchestriaShmRing {
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
    float            frames[kOrchestria_RingBufferFrames * kOrchestria_Channels];
} OrchestriaShmRing;

_Static_assert(sizeof(OrchestriaShmRing) == 64 + (kOrchestria_RingBufferFrames * kOrchestria_Channels * sizeof(float)),
               "OrchestriaShmRing header must be exactly 64 bytes followed by interleaved f32 stereo frames");

// Global Driver State
typedef struct OrchestriaDriverState {
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
    OrchestriaShmRing* shm_ring;
} OrchestriaDriverState;

#endif // ORCHESTRIA_AUDIO_H
