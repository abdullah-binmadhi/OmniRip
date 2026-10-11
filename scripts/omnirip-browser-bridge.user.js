// ==UserScript==
// @name         OmniRip Pure Rust Audio Engine Bridge
// @namespace    https://github.com/omnirip/bridge
// @version      1.0.0
// @description  Routes live YouTube and web video audio directly to OmniRip System EQ on 127.0.0.1:49152
// @match        *://*.youtube.com/*
// @match        *://*.soundcloud.com/*
// @match        *://*.twitch.tv/*
// @match        *://*.bandcamp.com/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    console.log('[OmniRip Bridge] Initializing browser WebAudio capture...');

    let audioCtx = null;
    let sourceNode = null;
    let processorNode = null;
    let ws = null;
    const OMNIRIP_PORT = 49152;

    function initCapture() {
        const mediaEl = document.querySelector('video') || document.querySelector('audio');
        if (!mediaEl || mediaEl._omniripAttached) {
            return;
        }

        mediaEl._omniripAttached = true;
        console.log('[OmniRip Bridge] Found active media element:', mediaEl);

        try {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 48000 });
            sourceNode = audioCtx.createMediaElementSource(mediaEl);
            processorNode = audioCtx.createScriptProcessor(512, 2, 2);

            // Connect to OmniRip TCP/WebSocket Gateway
            const connectWs = () => {
                ws = new WebSocket(`ws://127.0.0.1:${OMNIRIP_PORT}`);
                ws.binaryType = 'arraybuffer';
                ws.onopen = () => console.log('[OmniRip Bridge] Connected to OmniRip Audio Engine!');
                ws.onerror = () => setTimeout(connectWs, 3000);
            };
            connectWs();

            let sequence = 0;
            processorNode.onaudioprocess = (e) => {
                if (!ws || ws.readyState !== WebSocket.OPEN) return;

                const left = e.inputBuffer.getChannelData(0);
                const right = e.inputBuffer.getChannelData(1);
                const frameCount = left.length;

                // Build OmniRip AudioPacketHeader (16 bytes) + Float32 Stereo Payload
                const packetSize = 16 + (frameCount * 8);
                const buffer = new ArrayBuffer(packetSize);
                const view = new DataView(buffer);

                // Header
                view.setUint32(0, 0x4F4D4E49, true); // OMNI magic
                view.setUint32(4, sequence++, true);
                view.setUint32(8, 48000, true);      // 48 kHz
                view.setUint16(12, 2, true);          // 2 channels
                view.setUint16(14, frameCount, true); // frames

                // Payload (interleaved L, R)
                const floatView = new Float32Array(buffer, 16);
                for (let i = 0; i < frameCount; i++) {
                    floatView[i * 2] = left[i];
                    floatView[i * 2 + 1] = right[i];
                }

                ws.send(buffer);
            };

            sourceNode.connect(processorNode);
            processorNode.connect(audioCtx.destination);
            console.log('[OmniRip Bridge] WebAudio capture active and streaming to OmniRip.');
        } catch (err) {
            console.error('[OmniRip Bridge] WebAudio initialization error:', err);
        }
    }

    // Observe DOM for dynamic video element insertion (YouTube single page app navigation)
    const observer = new MutationObserver(() => initCapture());
    observer.observe(document.body, { childList: true, subtree: true });
    initCapture();
})();
