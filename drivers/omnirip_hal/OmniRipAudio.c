#include "OmniRipAudio.h"
#include <mach/mach_time.h>
#include <string.h>
#include <sys/syslog.h>

// Driver Singleton State
static OmniRipDriverState gDriverState = {
    .host = NULL,
    .ref_count = 1,
    .sample_rate = 48000.0,
    .volume_scalar = 1.0f,
    .is_muted = 0,
    .io_is_running = 0,
    .host_ticks_per_frame = 0.0,
    .number_timestamps = 0,
    .anchor_host_time = 0,
    .previous_ticks = 0.0,
    .io_mutex = PTHREAD_MUTEX_INITIALIZER,
    .ring_buffer = {0}
};

static mach_timebase_info_data_t gTimebaseInfo = {0, 0};

// Forward Declarations
static HRESULT Driver_QueryInterface(void* inDriver, REFIID inUUID, LPVOID* outInterface);
static ULONG   Driver_AddRef(void* inDriver);
static ULONG   Driver_Release(void* inDriver);
static OSStatus Driver_Initialize(AudioServerPlugInDriverRef inDriver, AudioServerPlugInHostRef inHost);
static OSStatus Driver_CreateDevice(AudioServerPlugInDriverRef inDriver, CFDictionaryRef inDescription, const AudioServerPlugInClientInfo* inClientInfo, AudioObjectID* outDeviceObjectID);
static OSStatus Driver_DestroyDevice(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID);
static OSStatus Driver_AddDeviceClient(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, const AudioServerPlugInClientInfo* inClientInfo);
static OSStatus Driver_RemoveDeviceClient(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, const AudioServerPlugInClientInfo* inClientInfo);
static OSStatus Driver_PerformDeviceConfigurationChange(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, UInt64 inChangeAction, void* inChangeInfo);
static OSStatus Driver_AbortDeviceConfigurationChange(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, UInt64 inChangeAction, void* inChangeInfo);

static Boolean  Driver_HasProperty(AudioServerPlugInDriverRef inDriver, AudioObjectID inObjectID, pid_t inClientProcessID, const AudioObjectPropertyAddress* inAddress);
static OSStatus Driver_IsPropertySettable(AudioServerPlugInDriverRef inDriver, AudioObjectID inObjectID, pid_t inClientProcessID, const AudioObjectPropertyAddress* inAddress, Boolean* outIsSettable);
static OSStatus Driver_GetPropertyDataSize(AudioServerPlugInDriverRef inDriver, AudioObjectID inObjectID, pid_t inClientProcessID, const AudioObjectPropertyAddress* inAddress, UInt32 inQualifierDataSize, const void* inQualifierData, UInt32* outDataSize);
static OSStatus Driver_GetPropertyData(AudioServerPlugInDriverRef inDriver, AudioObjectID inObjectID, pid_t inClientProcessID, const AudioObjectPropertyAddress* inAddress, UInt32 inQualifierDataSize, const void* inQualifierData, UInt32 inDataSize, UInt32* outDataSize, void* outData);
static OSStatus Driver_SetPropertyData(AudioServerPlugInDriverRef inDriver, AudioObjectID inObjectID, pid_t inClientProcessID, const AudioObjectPropertyAddress* inAddress, UInt32 inQualifierDataSize, const void* inQualifierData, UInt32 inDataSize, const void* inData);

static OSStatus Driver_StartIO(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, UInt32 inClientID);
static OSStatus Driver_StopIO(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, UInt32 inClientID);
static OSStatus Driver_GetZeroTimeStamp(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, UInt32 inClientID, Float64* outSampleTime, UInt64* outHostTime, UInt64* outSeed);
static OSStatus Driver_WillDoIOOperation(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, UInt32 inClientID, UInt32 inOperationID, Boolean* outWillDo, Boolean* outWillDoInPlace);
static OSStatus Driver_BeginIOOperation(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, UInt32 inClientID, UInt32 inOperationID, UInt32 inIOBufferFrameSize, const AudioServerPlugInIOCycleInfo* inIOCycleInfo);
static OSStatus Driver_DoIOOperation(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, AudioObjectID inStreamObjectID, UInt32 inClientID, UInt32 inOperationID, UInt32 inIOBufferFrameSize, const AudioServerPlugInIOCycleInfo* inIOCycleInfo, void* ioMainBuffer, void* ioSecondaryBuffer);
static OSStatus Driver_EndIOOperation(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, UInt32 inClientID, UInt32 inOperationID, UInt32 inIOBufferFrameSize, const AudioServerPlugInIOCycleInfo* inIOCycleInfo);

// Interface Table
static AudioServerPlugInDriverInterface gDriverInterface = {
    NULL,
    Driver_QueryInterface,
    Driver_AddRef,
    Driver_Release,
    Driver_Initialize,
    Driver_CreateDevice,
    Driver_DestroyDevice,
    Driver_AddDeviceClient,
    Driver_RemoveDeviceClient,
    Driver_PerformDeviceConfigurationChange,
    Driver_AbortDeviceConfigurationChange,
    Driver_HasProperty,
    Driver_IsPropertySettable,
    Driver_GetPropertyDataSize,
    Driver_GetPropertyData,
    Driver_SetPropertyData,
    Driver_StartIO,
    Driver_StopIO,
    Driver_GetZeroTimeStamp,
    Driver_WillDoIOOperation,
    Driver_BeginIOOperation,
    Driver_DoIOOperation,
    Driver_EndIOOperation
};

static AudioServerPlugInDriverInterface* gDriverInterfacePtr = &gDriverInterface;
static AudioServerPlugInDriverRef gDriverRef = &gDriverInterfacePtr;

// Helper: Standard Audio Stream Description
static void GetStreamFormat(Float64 sampleRate, AudioStreamBasicDescription* outDesc) {
    outDesc->mSampleRate = sampleRate;
    outDesc->mFormatID = kAudioFormatLinearPCM;
    outDesc->mFormatFlags = kAudioFormatFlagIsFloat | kAudioFormatFlagsNativeEndian | kAudioFormatFlagIsPacked;
    outDesc->mBytesPerPacket = sizeof(Float32) * kOmniRip_Channels;
    outDesc->mFramesPerPacket = 1;
    outDesc->mBytesPerFrame = sizeof(Float32) * kOmniRip_Channels;
    outDesc->mChannelsPerFrame = kOmniRip_Channels;
    outDesc->mBitsPerChannel = 32;
    outDesc->mReserved = 0;
}

// Factory Function
__attribute__((visibility("default")))
void* OmniRipAudio_Create(CFAllocatorRef inAllocator, CFUUIDRef inRequestedTypeUUID) {
    (void)inAllocator;
    CFUUIDRef factoryUUID = CFUUIDGetConstantUUIDWithBytes(NULL,
        0xa1, 0xb2, 0xc3, 0xd4, 0xe5, 0xf6, 0x4a, 0x5b,
        0x8c, 0x9d, 0x0e, 0x1f, 0x2a, 0x3b, 0x4c, 0x5d);
    
    if (CFEqual(inRequestedTypeUUID, factoryUUID) || CFEqual(inRequestedTypeUUID, kAudioServerPlugInTypeUUID)) {
        mach_timebase_info(&gTimebaseInfo);
        return gDriverRef;
    }
    return NULL;
}

static HRESULT Driver_QueryInterface(void* inDriver, REFIID inUUID, LPVOID* outInterface) {
    (void)inDriver;
    CFUUIDRef iunknownUUID = CFUUIDGetConstantUUIDWithBytes(NULL,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46);
    CFUUIDBytes iunknownBytes = CFUUIDGetUUIDBytes(iunknownUUID);
    CFUUIDBytes driverBytes   = CFUUIDGetUUIDBytes(kAudioServerPlugInDriverInterfaceUUID);

    if (memcmp(&inUUID, &iunknownBytes, sizeof(CFUUIDBytes)) == 0 ||
        memcmp(&inUUID, &driverBytes, sizeof(CFUUIDBytes)) == 0) {
        Driver_AddRef(inDriver);
        *outInterface = gDriverRef;
        return S_OK;
    }

    *outInterface = NULL;
    return E_NOINTERFACE;
}

static ULONG Driver_AddRef(void* inDriver) {
    (void)inDriver;
    return ++gDriverState.ref_count;
}

static ULONG Driver_Release(void* inDriver) {
    (void)inDriver;
    if (gDriverState.ref_count > 0) {
        return --gDriverState.ref_count;
    }
    return 0;
}

static OSStatus Driver_Initialize(AudioServerPlugInDriverRef inDriver, AudioServerPlugInHostRef inHost) {
    (void)inDriver;
    gDriverState.host = inHost;
    mach_timebase_info(&gTimebaseInfo);
    return kAudioHardwareNoError;
}

static OSStatus Driver_CreateDevice(AudioServerPlugInDriverRef inDriver, CFDictionaryRef inDescription, const AudioServerPlugInClientInfo* inClientInfo, AudioObjectID* outDeviceObjectID) {
    (void)inDriver; (void)inDescription; (void)inClientInfo; (void)outDeviceObjectID;
    return kAudioHardwareUnsupportedOperationError;
}

static OSStatus Driver_DestroyDevice(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID) {
    (void)inDriver; (void)inDeviceObjectID;
    return kAudioHardwareUnsupportedOperationError;
}

static OSStatus Driver_AddDeviceClient(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, const AudioServerPlugInClientInfo* inClientInfo) {
    (void)inDriver; (void)inDeviceObjectID; (void)inClientInfo;
    return kAudioHardwareNoError;
}

static OSStatus Driver_RemoveDeviceClient(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, const AudioServerPlugInClientInfo* inClientInfo) {
    (void)inDriver; (void)inDeviceObjectID; (void)inClientInfo;
    return kAudioHardwareNoError;
}

static OSStatus Driver_PerformDeviceConfigurationChange(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, UInt64 inChangeAction, void* inChangeInfo) {
    (void)inDriver; (void)inDeviceObjectID; (void)inChangeAction; (void)inChangeInfo;
    return kAudioHardwareNoError;
}

static OSStatus Driver_AbortDeviceConfigurationChange(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, UInt64 inChangeAction, void* inChangeInfo) {
    (void)inDriver; (void)inDeviceObjectID; (void)inChangeAction; (void)inChangeInfo;
    return kAudioHardwareNoError;
}

// Property Queries
static Boolean Driver_HasProperty(AudioServerPlugInDriverRef inDriver, AudioObjectID inObjectID, pid_t inClientProcessID, const AudioObjectPropertyAddress* inAddress) {
    (void)inDriver; (void)inClientProcessID;
    if (!inAddress) return false;

    if (inObjectID == kObjectID_PlugIn) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
            case kAudioObjectPropertyClass:
            case kAudioObjectPropertyOwner:
            case kAudioObjectPropertyManufacturer:
            case kAudioObjectPropertyOwnedObjects:
            case kAudioPlugInPropertyDeviceList:
            case kAudioPlugInPropertyTranslateUIDToDevice:
            case kAudioPlugInPropertyResourceBundle:
            case kAudioPlugInPropertyBoxList:
            case kAudioPlugInPropertyTranslateUIDToBox:
                return true;
            default:
                return false;
        }
    } else if (inObjectID == kObjectID_Box) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
            case kAudioObjectPropertyClass:
            case kAudioObjectPropertyOwner:
            case kAudioObjectPropertyName:
            case kAudioObjectPropertyManufacturer:
            case kAudioObjectPropertyOwnedObjects:
            case kAudioBoxPropertyBoxUID:
            case kAudioBoxPropertyTransportType:
            case kAudioBoxPropertyHasAudio:
            case kAudioBoxPropertyHasVideo:
            case kAudioBoxPropertyHasMIDI:
            case kAudioBoxPropertyIsProtected:
            case kAudioBoxPropertyAcquired:
            case kAudioBoxPropertyAcquisitionFailed:
            case kAudioBoxPropertyDeviceList:
                return true;
            default:
                return false;
        }
    } else if (inObjectID == kObjectID_Device) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
            case kAudioObjectPropertyClass:
            case kAudioObjectPropertyOwner:
            case kAudioObjectPropertyName:
            case kAudioObjectPropertyManufacturer:
            case kAudioObjectPropertyOwnedObjects:
            case kAudioDevicePropertyDeviceUID:
            case kAudioDevicePropertyModelUID:
            case kAudioDevicePropertyTransportType:
            case kAudioDevicePropertyRelatedDevices:
            case kAudioDevicePropertyClockDomain:
            case kAudioDevicePropertyDeviceIsAlive:
            case kAudioDevicePropertyDeviceIsRunning:
            case kAudioDevicePropertyDeviceCanBeDefaultDevice:
            case kAudioDevicePropertyDeviceCanBeDefaultSystemDevice:
            case kAudioDevicePropertyLatency:
            case kAudioDevicePropertySafetyOffset:
            case kAudioDevicePropertyNominalSampleRate:
            case kAudioDevicePropertyAvailableNominalSampleRates:
            case kAudioDevicePropertyStreams:
            case kAudioObjectPropertyControlList:
            case kAudioDevicePropertyBufferFrameSize:
            case kAudioDevicePropertyBufferFrameSizeRange:
            case kAudioDevicePropertyIsHidden:
            case kAudioDevicePropertyPreferredChannelsForStereo:
            case kAudioDevicePropertyPreferredChannelLayout:
            case kAudioDevicePropertyZeroTimeStampPeriod:
                return true;
            default:
                return false;
        }
    } else if (inObjectID == kObjectID_Stream_Output || inObjectID == kObjectID_Stream_Input) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
            case kAudioObjectPropertyClass:
            case kAudioObjectPropertyOwner:
            case kAudioObjectPropertyOwnedObjects:
            case kAudioStreamPropertyDirection:
            case kAudioStreamPropertyTerminalType:
            case kAudioStreamPropertyStartingChannel:
            case kAudioStreamPropertyLatency:
            case kAudioStreamPropertyVirtualFormat:
            case kAudioStreamPropertyPhysicalFormat:
            case kAudioStreamPropertyAvailableVirtualFormats:
            case kAudioStreamPropertyAvailablePhysicalFormats:
            case kAudioStreamPropertyIsActive:
                return true;
            default:
                return false;
        }
    } else if (inObjectID == kObjectID_Volume_Output_Master) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
            case kAudioObjectPropertyClass:
            case kAudioObjectPropertyOwner:
            case kAudioObjectPropertyOwnedObjects:
            case kAudioControlPropertyScope:
            case kAudioControlPropertyElement:
            case kAudioLevelControlPropertyScalarValue:
                return true;
            default:
                return false;
        }
    } else if (inObjectID == kObjectID_Mute_Output_Master) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
            case kAudioObjectPropertyClass:
            case kAudioObjectPropertyOwner:
            case kAudioObjectPropertyOwnedObjects:
            case kAudioControlPropertyScope:
            case kAudioControlPropertyElement:
            case kAudioBooleanControlPropertyValue:
                return true;
            default:
                return false;
        }
    }
    return false;
}

static OSStatus Driver_IsPropertySettable(AudioServerPlugInDriverRef inDriver, AudioObjectID inObjectID, pid_t inClientProcessID, const AudioObjectPropertyAddress* inAddress, Boolean* outIsSettable) {
    (void)inDriver; (void)inClientProcessID;
    if (!inAddress || !outIsSettable) return kAudioHardwareIllegalOperationError;

    *outIsSettable = false;
    if (inObjectID == kObjectID_Device) {
        if (inAddress->mSelector == kAudioDevicePropertyNominalSampleRate ||
            inAddress->mSelector == kAudioDevicePropertyBufferFrameSize) {
            *outIsSettable = true;
            return kAudioHardwareNoError;
        }
    } else if (inObjectID == kObjectID_Volume_Output_Master) {
        if (inAddress->mSelector == kAudioLevelControlPropertyScalarValue) {
            *outIsSettable = true;
            return kAudioHardwareNoError;
        }
    } else if (inObjectID == kObjectID_Mute_Output_Master) {
        if (inAddress->mSelector == kAudioBooleanControlPropertyValue) {
            *outIsSettable = true;
            return kAudioHardwareNoError;
        }
    }
    return kAudioHardwareNoError;
}

static OSStatus Driver_GetPropertyDataSize(AudioServerPlugInDriverRef inDriver, AudioObjectID inObjectID, pid_t inClientProcessID, const AudioObjectPropertyAddress* inAddress, UInt32 inQualifierDataSize, const void* inQualifierData, UInt32* outDataSize) {
    (void)inDriver; (void)inClientProcessID; (void)inQualifierDataSize; (void)inQualifierData;
    if (!inAddress || !outDataSize) return kAudioHardwareIllegalOperationError;

    if (inObjectID == kObjectID_PlugIn) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
            case kAudioObjectPropertyClass:
            case kAudioObjectPropertyOwner:
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyManufacturer:
            case kAudioPlugInPropertyResourceBundle:
                *outDataSize = sizeof(CFStringRef);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwnedObjects:
                *outDataSize = sizeof(AudioObjectID) * 2;
                return kAudioHardwareNoError;
            case kAudioPlugInPropertyDeviceList:
            case kAudioPlugInPropertyTranslateUIDToDevice:
            case kAudioPlugInPropertyBoxList:
            case kAudioPlugInPropertyTranslateUIDToBox:
                *outDataSize = sizeof(AudioObjectID);
                return kAudioHardwareNoError;
        }
    } else if (inObjectID == kObjectID_Box) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
            case kAudioObjectPropertyClass:
            case kAudioObjectPropertyOwner:
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyName:
            case kAudioObjectPropertyManufacturer:
            case kAudioBoxPropertyBoxUID:
                *outDataSize = sizeof(CFStringRef);
                return kAudioHardwareNoError;
            case kAudioBoxPropertyTransportType:
            case kAudioBoxPropertyHasAudio:
            case kAudioBoxPropertyHasVideo:
            case kAudioBoxPropertyHasMIDI:
            case kAudioBoxPropertyIsProtected:
            case kAudioBoxPropertyAcquired:
            case kAudioBoxPropertyAcquisitionFailed:
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwnedObjects:
            case kAudioBoxPropertyDeviceList:
                *outDataSize = sizeof(AudioObjectID);
                return kAudioHardwareNoError;
        }
    } else if (inObjectID == kObjectID_Device) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
            case kAudioObjectPropertyClass:
            case kAudioObjectPropertyOwner:
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyName:
            case kAudioObjectPropertyManufacturer:
            case kAudioDevicePropertyDeviceUID:
            case kAudioDevicePropertyModelUID:
                *outDataSize = sizeof(CFStringRef);
                return kAudioHardwareNoError;
            case kAudioDevicePropertyTransportType:
            case kAudioDevicePropertyDeviceIsAlive:
            case kAudioDevicePropertyDeviceIsRunning:
            case kAudioDevicePropertyDeviceCanBeDefaultDevice:
            case kAudioDevicePropertyDeviceCanBeDefaultSystemDevice:
            case kAudioDevicePropertyLatency:
            case kAudioDevicePropertySafetyOffset:
            case kAudioDevicePropertyBufferFrameSize:
            case kAudioDevicePropertyClockDomain:
            case kAudioDevicePropertyIsHidden:
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioDevicePropertyPreferredChannelsForStereo:
                *outDataSize = sizeof(UInt32) * 2;
                return kAudioHardwareNoError;
            case kAudioDevicePropertyRelatedDevices:
                *outDataSize = sizeof(AudioObjectID);
                return kAudioHardwareNoError;
            case kAudioDevicePropertyNominalSampleRate:
                *outDataSize = sizeof(Float64);
                return kAudioHardwareNoError;
            case kAudioDevicePropertyBufferFrameSizeRange:
                *outDataSize = sizeof(AudioValueRange);
                return kAudioHardwareNoError;
            case kAudioDevicePropertyAvailableNominalSampleRates:
                *outDataSize = sizeof(AudioValueRange) * 3;
                return kAudioHardwareNoError;
            case kAudioDevicePropertyStreams:
                if (inAddress->mScope == kAudioObjectPropertyScopeGlobal) {
                    *outDataSize = sizeof(AudioObjectID) * 2;
                } else {
                    *outDataSize = sizeof(AudioObjectID);
                }
                return kAudioHardwareNoError;
            case kAudioObjectPropertyControlList:
                *outDataSize = sizeof(AudioObjectID) * 2;
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwnedObjects:
                *outDataSize = sizeof(AudioObjectID) * 4;
                return kAudioHardwareNoError;
            case kAudioDevicePropertyZeroTimeStampPeriod:
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioDevicePropertyPreferredChannelLayout:
                *outDataSize = offsetof(AudioChannelLayout, mChannelDescriptions) + (kOmniRip_Channels * sizeof(AudioChannelDescription));
                return kAudioHardwareNoError;
        }
    } else if (inObjectID == kObjectID_Stream_Output || inObjectID == kObjectID_Stream_Input) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
            case kAudioObjectPropertyClass:
            case kAudioObjectPropertyOwner:
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioStreamPropertyDirection:
            case kAudioStreamPropertyTerminalType:
            case kAudioStreamPropertyStartingChannel:
            case kAudioStreamPropertyIsActive:
            case kAudioStreamPropertyLatency:
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioStreamPropertyVirtualFormat:
            case kAudioStreamPropertyPhysicalFormat:
                *outDataSize = sizeof(AudioStreamBasicDescription);
                return kAudioHardwareNoError;
            case kAudioStreamPropertyAvailableVirtualFormats:
            case kAudioStreamPropertyAvailablePhysicalFormats:
                *outDataSize = sizeof(AudioStreamRangedDescription) * 3;
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwnedObjects:
                *outDataSize = 0;
                return kAudioHardwareNoError;
        }
    } else if (inObjectID == kObjectID_Volume_Output_Master) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
            case kAudioObjectPropertyClass:
            case kAudioObjectPropertyOwner:
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioControlPropertyScope:
                *outDataSize = sizeof(AudioObjectPropertyScope);
                return kAudioHardwareNoError;
            case kAudioControlPropertyElement:
                *outDataSize = sizeof(AudioObjectPropertyElement);
                return kAudioHardwareNoError;
            case kAudioLevelControlPropertyScalarValue:
                *outDataSize = sizeof(Float32);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwnedObjects:
                *outDataSize = 0;
                return kAudioHardwareNoError;
        }
    } else if (inObjectID == kObjectID_Mute_Output_Master) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
            case kAudioObjectPropertyClass:
            case kAudioObjectPropertyOwner:
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioControlPropertyScope:
                *outDataSize = sizeof(AudioObjectPropertyScope);
                return kAudioHardwareNoError;
            case kAudioControlPropertyElement:
                *outDataSize = sizeof(AudioObjectPropertyElement);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwnedObjects:
                *outDataSize = 0;
                return kAudioHardwareNoError;
            case kAudioBooleanControlPropertyValue:
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
        }
    }
    syslog(LOG_NOTICE, "OmniRip UNKNOWN PROP (Size) obj=%u sel=%.4s (0x%08x) scope=%.4s elem=%u",
           inObjectID, (char*)&inAddress->mSelector, inAddress->mSelector, (char*)&inAddress->mScope, inAddress->mElement);
    return kAudioHardwareUnknownPropertyError;
}

static OSStatus Driver_GetPropertyData(AudioServerPlugInDriverRef inDriver, AudioObjectID inObjectID, pid_t inClientProcessID, const AudioObjectPropertyAddress* inAddress, UInt32 inQualifierDataSize, const void* inQualifierData, UInt32 inDataSize, UInt32* outDataSize, void* outData) {
    (void)inDriver; (void)inClientProcessID; (void)inQualifierDataSize; (void)inQualifierData; (void)inDataSize;
    if (!inAddress || !outDataSize || !outData) return kAudioHardwareIllegalOperationError;

    if (inObjectID == kObjectID_PlugIn) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
                *((AudioClassID*)outData) = kAudioObjectClassID;
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyClass:
                *((AudioClassID*)outData) = kAudioPlugInClassID;
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwner:
                *((AudioObjectID*)outData) = kAudioObjectUnknown;
                *outDataSize = sizeof(AudioObjectID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyManufacturer:
                *((CFStringRef*)outData) = CFSTR(kOmniRip_Manufacturer);
                CFRetain(*((CFStringRef*)outData));
                *outDataSize = sizeof(CFStringRef);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwnedObjects: {
                UInt32 count = inDataSize / sizeof(AudioObjectID);
                if (count > 2) count = 2;
                AudioObjectID* list = (AudioObjectID*)outData;
                if (count > 0) list[0] = kObjectID_Box;
                if (count > 1) list[1] = kObjectID_Device;
                *outDataSize = count * sizeof(AudioObjectID);
                return kAudioHardwareNoError;
            }
            case kAudioPlugInPropertyDeviceList:
                *((AudioObjectID*)outData) = kObjectID_Device;
                *outDataSize = sizeof(AudioObjectID);
                return kAudioHardwareNoError;
            case kAudioPlugInPropertyTranslateUIDToDevice:
                if (inQualifierData != NULL && inQualifierDataSize >= sizeof(CFStringRef)) {
                    CFStringRef theUID = *((CFStringRef*)inQualifierData);
                    if (theUID != NULL && CFStringCompare(theUID, CFSTR(kOmniRip_Device_UID), 0) == kCFCompareEqualTo) {
                        *((AudioObjectID*)outData) = kObjectID_Device;
                        *outDataSize = sizeof(AudioObjectID);
                        return kAudioHardwareNoError;
                    }
                }
                *((AudioObjectID*)outData) = kAudioObjectUnknown;
                *outDataSize = sizeof(AudioObjectID);
                return kAudioHardwareNoError;
            case kAudioPlugInPropertyBoxList:
                *((AudioObjectID*)outData) = kObjectID_Box;
                *outDataSize = sizeof(AudioObjectID);
                return kAudioHardwareNoError;
            case kAudioPlugInPropertyTranslateUIDToBox:
                if (inQualifierData != NULL && inQualifierDataSize >= sizeof(CFStringRef)) {
                    CFStringRef theUID = *((CFStringRef*)inQualifierData);
                    if (theUID != NULL && CFStringCompare(theUID, CFSTR(kOmniRip_Box_UID), 0) == kCFCompareEqualTo) {
                        *((AudioObjectID*)outData) = kObjectID_Box;
                        *outDataSize = sizeof(AudioObjectID);
                        return kAudioHardwareNoError;
                    }
                }
                *((AudioObjectID*)outData) = kAudioObjectUnknown;
                *outDataSize = sizeof(AudioObjectID);
                return kAudioHardwareNoError;
            case kAudioPlugInPropertyResourceBundle:
                *((CFStringRef*)outData) = CFSTR("");
                CFRetain(*((CFStringRef*)outData));
                *outDataSize = sizeof(CFStringRef);
                return kAudioHardwareNoError;
        }
    } else if (inObjectID == kObjectID_Box) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
                *((AudioClassID*)outData) = kAudioObjectClassID;
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyClass:
                *((AudioClassID*)outData) = kAudioBoxClassID;
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwner:
                *((AudioObjectID*)outData) = kObjectID_PlugIn;
                *outDataSize = sizeof(AudioObjectID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyName:
                *((CFStringRef*)outData) = CFSTR(kOmniRip_Device_Name);
                CFRetain(*((CFStringRef*)outData));
                *outDataSize = sizeof(CFStringRef);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyManufacturer:
                *((CFStringRef*)outData) = CFSTR(kOmniRip_Manufacturer);
                CFRetain(*((CFStringRef*)outData));
                *outDataSize = sizeof(CFStringRef);
                return kAudioHardwareNoError;
            case kAudioBoxPropertyBoxUID:
                *((CFStringRef*)outData) = CFSTR(kOmniRip_Box_UID);
                CFRetain(*((CFStringRef*)outData));
                *outDataSize = sizeof(CFStringRef);
                return kAudioHardwareNoError;
            case kAudioBoxPropertyTransportType:
                *((UInt32*)outData) = kAudioDeviceTransportTypeVirtual;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioBoxPropertyHasAudio:
                *((UInt32*)outData) = 1;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioBoxPropertyHasVideo:
            case kAudioBoxPropertyHasMIDI:
            case kAudioBoxPropertyIsProtected:
                *((UInt32*)outData) = 0;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioBoxPropertyAcquired:
                *((UInt32*)outData) = 1;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioBoxPropertyAcquisitionFailed:
                *((UInt32*)outData) = 0;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwnedObjects:
            case kAudioBoxPropertyDeviceList:
                if (inDataSize >= sizeof(AudioObjectID)) {
                    *((AudioObjectID*)outData) = kObjectID_Device;
                    *outDataSize = sizeof(AudioObjectID);
                } else {
                    *outDataSize = 0;
                }
                return kAudioHardwareNoError;
        }
    } else if (inObjectID == kObjectID_Device) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
                *((AudioClassID*)outData) = kAudioObjectClassID;
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyClass:
                *((AudioClassID*)outData) = kAudioDeviceClassID;
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwner:
                *((AudioObjectID*)outData) = kObjectID_PlugIn;
                *outDataSize = sizeof(AudioObjectID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyName:
                *((CFStringRef*)outData) = CFSTR(kOmniRip_Device_Name);
                CFRetain(*((CFStringRef*)outData));
                *outDataSize = sizeof(CFStringRef);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyManufacturer:
                *((CFStringRef*)outData) = CFSTR(kOmniRip_Manufacturer);
                CFRetain(*((CFStringRef*)outData));
                *outDataSize = sizeof(CFStringRef);
                return kAudioHardwareNoError;
            case kAudioDevicePropertyDeviceUID:
                *((CFStringRef*)outData) = CFSTR(kOmniRip_Device_UID);
                CFRetain(*((CFStringRef*)outData));
                *outDataSize = sizeof(CFStringRef);
                return kAudioHardwareNoError;
            case kAudioDevicePropertyModelUID:
                *((CFStringRef*)outData) = CFSTR(kOmniRip_Device_Model_UID);
                CFRetain(*((CFStringRef*)outData));
                *outDataSize = sizeof(CFStringRef);
                return kAudioHardwareNoError;
            case kAudioDevicePropertyTransportType:
                *((UInt32*)outData) = kAudioDeviceTransportTypeVirtual;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioDevicePropertyDeviceIsAlive:
            case kAudioDevicePropertyDeviceIsRunning:
            case kAudioDevicePropertyDeviceCanBeDefaultDevice:
            case kAudioDevicePropertyDeviceCanBeDefaultSystemDevice:
                *((UInt32*)outData) = 1;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioDevicePropertyLatency:
            case kAudioDevicePropertySafetyOffset:
                *((UInt32*)outData) = 0;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioDevicePropertyNominalSampleRate:
                *((Float64*)outData) = gDriverState.sample_rate;
                *outDataSize = sizeof(Float64);
                return kAudioHardwareNoError;
            case kAudioDevicePropertyBufferFrameSize:
                *((UInt32*)outData) = 512;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioDevicePropertyBufferFrameSizeRange: {
                AudioValueRange* range = (AudioValueRange*)outData;
                range->mMinimum = 64.0;
                range->mMaximum = 4096.0;
                *outDataSize = sizeof(AudioValueRange);
                return kAudioHardwareNoError;
            }
            case kAudioDevicePropertyAvailableNominalSampleRates: {
                AudioValueRange* ranges = (AudioValueRange*)outData;
                ranges[0].mMinimum = 48000.0; ranges[0].mMaximum = 48000.0;
                ranges[1].mMinimum = 96000.0; ranges[1].mMaximum = 96000.0;
                ranges[2].mMinimum = 192000.0; ranges[2].mMaximum = 192000.0;
                *outDataSize = sizeof(AudioValueRange) * 3;
                return kAudioHardwareNoError;
            }
            case kAudioDevicePropertyStreams: {
                AudioObjectID* streamList = (AudioObjectID*)outData;
                if (inAddress->mScope == kAudioObjectPropertyScopeOutput) {
                    streamList[0] = kObjectID_Stream_Output;
                    *outDataSize = sizeof(AudioObjectID);
                } else if (inAddress->mScope == kAudioObjectPropertyScopeInput) {
                    streamList[0] = kObjectID_Stream_Input;
                    *outDataSize = sizeof(AudioObjectID);
                } else {
                    streamList[0] = kObjectID_Stream_Output;
                    streamList[1] = kObjectID_Stream_Input;
                    *outDataSize = sizeof(AudioObjectID) * 2;
                }
                return kAudioHardwareNoError;
            }
            case kAudioObjectPropertyControlList: {
                AudioObjectID* controlList = (AudioObjectID*)outData;
                controlList[0] = kObjectID_Volume_Output_Master;
                controlList[1] = kObjectID_Mute_Output_Master;
                *outDataSize = sizeof(AudioObjectID) * 2;
                return kAudioHardwareNoError;
            }
            case kAudioObjectPropertyOwnedObjects: {
                UInt32 count = inDataSize / sizeof(AudioObjectID);
                if (count > 4) count = 4;
                AudioObjectID* list = (AudioObjectID*)outData;
                if (count > 0) list[0] = kObjectID_Stream_Output;
                if (count > 1) list[1] = kObjectID_Stream_Input;
                if (count > 2) list[2] = kObjectID_Volume_Output_Master;
                if (count > 3) list[3] = kObjectID_Mute_Output_Master;
                *outDataSize = count * sizeof(AudioObjectID);
                return kAudioHardwareNoError;
            }
            case kAudioDevicePropertyRelatedDevices:
                if (inDataSize >= sizeof(AudioObjectID)) {
                    *((AudioObjectID*)outData) = kObjectID_Device;
                    *outDataSize = sizeof(AudioObjectID);
                } else {
                    *outDataSize = 0;
                }
                return kAudioHardwareNoError;
            case kAudioDevicePropertyClockDomain:
            case kAudioDevicePropertyIsHidden:
                *((UInt32*)outData) = 0;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioDevicePropertyPreferredChannelsForStereo:
                if (inDataSize >= sizeof(UInt32) * 2) {
                    ((UInt32*)outData)[0] = 1;
                    ((UInt32*)outData)[1] = 2;
                    *outDataSize = sizeof(UInt32) * 2;
                } else {
                    *outDataSize = 0;
                }
                return kAudioHardwareNoError;
            case kAudioDevicePropertyZeroTimeStampPeriod:
                *((UInt32*)outData) = kOmniRip_RingBufferFrames;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioDevicePropertyPreferredChannelLayout: {
                UInt32 theACLSize = offsetof(AudioChannelLayout, mChannelDescriptions) + (kOmniRip_Channels * sizeof(AudioChannelDescription));
                if (inDataSize >= theACLSize) {
                    AudioChannelLayout* acl = (AudioChannelLayout*)outData;
                    acl->mChannelLayoutTag = kAudioChannelLayoutTag_UseChannelDescriptions;
                    acl->mChannelBitmap = 0;
                    acl->mNumberChannelDescriptions = kOmniRip_Channels;
                    for (UInt32 i = 0; i < kOmniRip_Channels; i++) {
                        acl->mChannelDescriptions[i].mChannelLabel = kAudioChannelLabel_Left + i;
                        acl->mChannelDescriptions[i].mChannelFlags = 0;
                        acl->mChannelDescriptions[i].mCoordinates[0] = 0;
                        acl->mChannelDescriptions[i].mCoordinates[1] = 0;
                        acl->mChannelDescriptions[i].mCoordinates[2] = 0;
                    }
                    *outDataSize = theACLSize;
                } else {
                    *outDataSize = 0;
                }
                return kAudioHardwareNoError;
            }
        }
    } else if (inObjectID == kObjectID_Stream_Output || inObjectID == kObjectID_Stream_Input) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
                *((AudioClassID*)outData) = kAudioObjectClassID;
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyClass:
                *((AudioClassID*)outData) = kAudioStreamClassID;
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwner:
                *((AudioObjectID*)outData) = kObjectID_Device;
                *outDataSize = sizeof(AudioObjectID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwnedObjects:
                *outDataSize = 0;
                return kAudioHardwareNoError;
            case kAudioStreamPropertyDirection:
                *((UInt32*)outData) = (inObjectID == kObjectID_Stream_Input) ? 1 : 0;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioStreamPropertyTerminalType:
                *((UInt32*)outData) = kAudioStreamTerminalTypeLine;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioStreamPropertyStartingChannel:
                *((UInt32*)outData) = 1;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioStreamPropertyIsActive:
                *((UInt32*)outData) = 1;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioStreamPropertyLatency:
                *((UInt32*)outData) = 0;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
            case kAudioStreamPropertyVirtualFormat:
            case kAudioStreamPropertyPhysicalFormat:
                GetStreamFormat(gDriverState.sample_rate, (AudioStreamBasicDescription*)outData);
                *outDataSize = sizeof(AudioStreamBasicDescription);
                return kAudioHardwareNoError;
            case kAudioStreamPropertyAvailableVirtualFormats:
            case kAudioStreamPropertyAvailablePhysicalFormats: {
                AudioStreamRangedDescription* formats = (AudioStreamRangedDescription*)outData;
                Float64 rates[] = {48000.0, 96000.0, 192000.0};
                for (int i = 0; i < 3; i++) {
                    GetStreamFormat(rates[i], &formats[i].mFormat);
                    formats[i].mSampleRateRange.mMinimum = rates[i];
                    formats[i].mSampleRateRange.mMaximum = rates[i];
                }
                *outDataSize = sizeof(AudioStreamRangedDescription) * 3;
                return kAudioHardwareNoError;
            }
        }
    } else if (inObjectID == kObjectID_Volume_Output_Master) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
                *((AudioClassID*)outData) = kAudioControlClassID;
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyClass:
                *((AudioClassID*)outData) = kAudioVolumeControlClassID;
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwner:
                *((AudioObjectID*)outData) = kObjectID_Device;
                *outDataSize = sizeof(AudioObjectID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwnedObjects:
                *outDataSize = 0;
                return kAudioHardwareNoError;
            case kAudioControlPropertyScope:
                *((AudioObjectPropertyScope*)outData) = kAudioObjectPropertyScopeOutput;
                *outDataSize = sizeof(AudioObjectPropertyScope);
                return kAudioHardwareNoError;
            case kAudioControlPropertyElement:
                *((AudioObjectPropertyElement*)outData) = kAudioObjectPropertyElementMain;
                *outDataSize = sizeof(AudioObjectPropertyElement);
                return kAudioHardwareNoError;
            case kAudioLevelControlPropertyScalarValue:
                *((Float32*)outData) = gDriverState.volume_scalar;
                *outDataSize = sizeof(Float32);
                return kAudioHardwareNoError;
        }
    } else if (inObjectID == kObjectID_Mute_Output_Master) {
        switch (inAddress->mSelector) {
            case kAudioObjectPropertyBaseClass:
                *((AudioClassID*)outData) = kAudioControlClassID;
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyClass:
                *((AudioClassID*)outData) = kAudioMuteControlClassID;
                *outDataSize = sizeof(AudioClassID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwner:
                *((AudioObjectID*)outData) = kObjectID_Device;
                *outDataSize = sizeof(AudioObjectID);
                return kAudioHardwareNoError;
            case kAudioObjectPropertyOwnedObjects:
                *outDataSize = 0;
                return kAudioHardwareNoError;
            case kAudioControlPropertyScope:
                *((AudioObjectPropertyScope*)outData) = kAudioObjectPropertyScopeOutput;
                *outDataSize = sizeof(AudioObjectPropertyScope);
                return kAudioHardwareNoError;
            case kAudioControlPropertyElement:
                *((AudioObjectPropertyElement*)outData) = kAudioObjectPropertyElementMain;
                *outDataSize = sizeof(AudioObjectPropertyElement);
                return kAudioHardwareNoError;
            case kAudioBooleanControlPropertyValue:
                *((UInt32*)outData) = gDriverState.is_muted;
                *outDataSize = sizeof(UInt32);
                return kAudioHardwareNoError;
        }
    }
    syslog(LOG_NOTICE, "OmniRip UNKNOWN PROP (Data) obj=%u sel=%.4s (0x%08x) scope=%.4s elem=%u inDataSize=%u",
           inObjectID, (char*)&inAddress->mSelector, inAddress->mSelector, (char*)&inAddress->mScope, inAddress->mElement, inDataSize);
    return kAudioHardwareUnknownPropertyError;
}

static OSStatus Driver_SetPropertyData(AudioServerPlugInDriverRef inDriver, AudioObjectID inObjectID, pid_t inClientProcessID, const AudioObjectPropertyAddress* inAddress, UInt32 inQualifierDataSize, const void* inQualifierData, UInt32 inDataSize, const void* inData) {
    (void)inDriver; (void)inClientProcessID; (void)inQualifierDataSize; (void)inQualifierData; (void)inDataSize;
    if (!inAddress || !inData) return kAudioHardwareIllegalOperationError;

    if (inObjectID == kObjectID_Device) {
        if (inAddress->mSelector == kAudioDevicePropertyNominalSampleRate) {
            Float64 newRate = *((const Float64*)inData);
            if (newRate == 48000.0 || newRate == 96000.0 || newRate == 192000.0) {
                gDriverState.sample_rate = newRate;
                if (gDriverState.host && gDriverState.host->PropertiesChanged) {
                    AudioObjectPropertyAddress addr = { kAudioDevicePropertyNominalSampleRate, kAudioObjectPropertyScopeGlobal, kAudioObjectPropertyElementMain };
                    gDriverState.host->PropertiesChanged(gDriverState.host, kObjectID_Device, 1, &addr);
                }
                return kAudioHardwareNoError;
            }
            return kAudioHardwareIllegalOperationError;
        } else if (inAddress->mSelector == kAudioDevicePropertyBufferFrameSize) {
            return kAudioHardwareNoError;
        }
    } else if (inObjectID == kObjectID_Volume_Output_Master) {
        if (inAddress->mSelector == kAudioLevelControlPropertyScalarValue) {
            Float32 vol = *((const Float32*)inData);
            if (vol < 0.0f) vol = 0.0f;
            if (vol > 1.0f) vol = 1.0f;
            gDriverState.volume_scalar = vol;
            if (gDriverState.host && gDriverState.host->PropertiesChanged) {
                AudioObjectPropertyAddress addr = { kAudioLevelControlPropertyScalarValue, kAudioObjectPropertyScopeOutput, kAudioObjectPropertyElementMain };
                gDriverState.host->PropertiesChanged(gDriverState.host, kObjectID_Volume_Output_Master, 1, &addr);
            }
            return kAudioHardwareNoError;
        }
    } else if (inObjectID == kObjectID_Mute_Output_Master) {
        if (inAddress->mSelector == kAudioBooleanControlPropertyValue) {
            gDriverState.is_muted = *((const UInt32*)inData) != 0 ? 1 : 0;
            if (gDriverState.host && gDriverState.host->PropertiesChanged) {
                AudioObjectPropertyAddress addr = { kAudioBooleanControlPropertyValue, kAudioObjectPropertyScopeOutput, kAudioObjectPropertyElementMain };
                gDriverState.host->PropertiesChanged(gDriverState.host, kObjectID_Mute_Output_Master, 1, &addr);
            }
            return kAudioHardwareNoError;
        }
    }
    return kAudioHardwareUnknownPropertyError;
}

// Real-Time IO Engine
static OSStatus Driver_StartIO(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, UInt32 inClientID) {
    (void)inDriver; (void)inDeviceObjectID; (void)inClientID;
    pthread_mutex_lock(&gDriverState.io_mutex);
    if (gDriverState.io_is_running == 0) {
        mach_timebase_info_data_t tb;
        mach_timebase_info(&tb);
        Float64 ticksPerSec = (1000000000.0 * (Float64)tb.denom) / (Float64)tb.numer;
        gDriverState.host_ticks_per_frame = ticksPerSec / gDriverState.sample_rate;
        gDriverState.number_timestamps = 0;
        gDriverState.anchor_host_time = mach_absolute_time();
        gDriverState.previous_ticks = 0.0;
        memset(gDriverState.ring_buffer, 0, sizeof(gDriverState.ring_buffer));
    }
    gDriverState.io_is_running++;
    pthread_mutex_unlock(&gDriverState.io_mutex);
    return kAudioHardwareNoError;
}

static OSStatus Driver_StopIO(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, UInt32 inClientID) {
    (void)inDriver; (void)inDeviceObjectID; (void)inClientID;
    pthread_mutex_lock(&gDriverState.io_mutex);
    if (gDriverState.io_is_running > 0) {
        gDriverState.io_is_running--;
    }
    pthread_mutex_unlock(&gDriverState.io_mutex);
    return kAudioHardwareNoError;
}

static OSStatus Driver_GetZeroTimeStamp(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, UInt32 inClientID, Float64* outSampleTime, UInt64* outHostTime, UInt64* outSeed) {
    (void)inDriver; (void)inDeviceObjectID; (void)inClientID;
    if (!outSampleTime || !outHostTime || !outSeed) return kAudioHardwareIllegalOperationError;

    pthread_mutex_lock(&gDriverState.io_mutex);
    uint64_t currentHostTime = mach_absolute_time();
    Float64 theHostTicksPerRingBuffer = gDriverState.host_ticks_per_frame * (Float64)kOmniRip_RingBufferFrames;
    Float64 theNextTickOffset = gDriverState.previous_ticks + theHostTicksPerRingBuffer;
    uint64_t theNextHostTime = gDriverState.anchor_host_time + (uint64_t)theNextTickOffset;

    if (theNextHostTime <= currentHostTime) {
        ++gDriverState.number_timestamps;
        gDriverState.previous_ticks = theNextTickOffset;
    }

    *outSampleTime = (Float64)(gDriverState.number_timestamps * kOmniRip_RingBufferFrames);
    *outHostTime = gDriverState.anchor_host_time + (uint64_t)gDriverState.previous_ticks;
    *outSeed = 1;
    pthread_mutex_unlock(&gDriverState.io_mutex);
    return kAudioHardwareNoError;
}

static OSStatus Driver_WillDoIOOperation(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, UInt32 inClientID, UInt32 inOperationID, Boolean* outWillDo, Boolean* outWillDoInPlace) {
    (void)inDriver; (void)inDeviceObjectID; (void)inClientID;
    if (!outWillDo || !outWillDoInPlace) return kAudioHardwareIllegalOperationError;

    if (inOperationID == kAudioServerPlugInIOOperationWriteMix ||
        inOperationID == kAudioServerPlugInIOOperationReadInput) {
        *outWillDo = true;
        *outWillDoInPlace = true;
        return kAudioHardwareNoError;
    }

    *outWillDo = false;
    *outWillDoInPlace = true;
    return kAudioHardwareNoError;
}

static OSStatus Driver_BeginIOOperation(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, UInt32 inClientID, UInt32 inOperationID, UInt32 inIOBufferFrameSize, const AudioServerPlugInIOCycleInfo* inIOCycleInfo) {
    (void)inDriver; (void)inDeviceObjectID; (void)inClientID; (void)inOperationID; (void)inIOBufferFrameSize; (void)inIOCycleInfo;
    return kAudioHardwareNoError;
}

static OSStatus Driver_DoIOOperation(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, AudioObjectID inStreamObjectID, UInt32 inClientID, UInt32 inOperationID, UInt32 inIOBufferFrameSize, const AudioServerPlugInIOCycleInfo* inIOCycleInfo, void* ioMainBuffer, void* ioSecondaryBuffer) {
    (void)inDriver; (void)inDeviceObjectID; (void)inStreamObjectID; (void)inClientID; (void)ioSecondaryBuffer;
    if (!ioMainBuffer || !inIOCycleInfo) return kAudioHardwareNoError;

    Float32* buffer = (Float32*)ioMainBuffer;
    UInt64 mSampleTime = (inOperationID == kAudioServerPlugInIOOperationReadInput)
        ? (UInt64)inIOCycleInfo->mInputTime.mSampleTime
        : (UInt64)inIOCycleInfo->mOutputTime.mSampleTime;

    UInt32 ringBufferFrameStart = (UInt32)(mSampleTime % kOmniRip_RingBufferFrames);
    UInt32 firstPartFrames = kOmniRip_RingBufferFrames - ringBufferFrameStart;
    UInt32 secondPartFrames = 0;

    if (firstPartFrames >= inIOBufferFrameSize) {
        firstPartFrames = inIOBufferFrameSize;
    } else {
        secondPartFrames = inIOBufferFrameSize - firstPartFrames;
    }

    if (inOperationID == kAudioServerPlugInIOOperationWriteMix) {
        memcpy(gDriverState.ring_buffer + (ringBufferFrameStart * kOmniRip_Channels), buffer, firstPartFrames * kOmniRip_Channels * sizeof(Float32));
        if (secondPartFrames > 0) {
            memcpy(gDriverState.ring_buffer, buffer + (firstPartFrames * kOmniRip_Channels), secondPartFrames * kOmniRip_Channels * sizeof(Float32));
        }
        return kAudioHardwareNoError;
    } else if (inOperationID == kAudioServerPlugInIOOperationReadInput) {
        if (gDriverState.is_muted) {
            memset(buffer, 0, inIOBufferFrameSize * kOmniRip_Channels * sizeof(Float32));
        } else {
            memcpy(buffer, gDriverState.ring_buffer + (ringBufferFrameStart * kOmniRip_Channels), firstPartFrames * kOmniRip_Channels * sizeof(Float32));
            if (secondPartFrames > 0) {
                memcpy(buffer + (firstPartFrames * kOmniRip_Channels), gDriverState.ring_buffer, secondPartFrames * kOmniRip_Channels * sizeof(Float32));
            }
            if (gDriverState.volume_scalar < 0.999f) {
                for (UInt32 i = 0; i < inIOBufferFrameSize * kOmniRip_Channels; i++) {
                    buffer[i] *= gDriverState.volume_scalar;
                }
            }
        }
        return kAudioHardwareNoError;
    }

    return kAudioHardwareNoError;
}

static OSStatus Driver_EndIOOperation(AudioServerPlugInDriverRef inDriver, AudioObjectID inDeviceObjectID, UInt32 inClientID, UInt32 inOperationID, UInt32 inIOBufferFrameSize, const AudioServerPlugInIOCycleInfo* inIOCycleInfo) {
    (void)inDriver; (void)inDeviceObjectID; (void)inClientID; (void)inOperationID; (void)inIOBufferFrameSize; (void)inIOCycleInfo;
    return kAudioHardwareNoError;
}
