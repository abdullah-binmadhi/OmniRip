#ifndef OMNIRIP_AUDIO_H
#define OMNIRIP_AUDIO_H

#include <CoreAudio/AudioHardware.h>
#include <CoreAudio/AudioServerPlugIn.h>
#include <CoreFoundation/CoreFoundation.h>
#include <stdalign.h>
#include <stdatomic.h>
#include <stdint.h>

// OmniRip Audio Constants
#define kOmniRip_Device_UID "com.omnirip.driver.audio"
#define kOmniRip_Device_Model_UID "com.omnirip.driver.audio.model"
#define kOmniRip_Box_UID "com.omnirip.driver.audio.box"
#define kOmniRip_Device_Name "OmniRip Audio"
#define kOmniRip_Manufacturer "OmniRip Audio Technologies"

#define kOmniRip_RingBufferFrames 32768
#define kOmniRip_Channels 2

// Object IDs
enum {
    kObjectID_PlugIn = 1,
    kObjectID_Device = 2,
    kObjectID_Stream_Output = 3,
    kObjectID_Stream_Input = 4,
    kObjectID_Volume_Output_Master = 5,
    kObjectID_Mute_Output_Master = 6,
    kObjectID_Box = 7
};

#include <pthread.h>

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

    // Ring Buffer for Global Audio Loopback (aligned to sample times)
    Float32 ring_buffer[kOmniRip_RingBufferFrames * kOmniRip_Channels];
} OmniRipDriverState;

#endif // OMNIRIP_AUDIO_H
