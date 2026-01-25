// Whisper voice input module
// Elements are defined in index.html, this just handles recording logic

(function() {
    'use strict';

    let mediaRecorder = null;
    let audioChunks = [];
    let audioContext = null;
    let analyser = null;
    let animationId = null;
    let stream = null;

    // DOM elements (from HTML)
    let micBtn = null;
    let waveformContainer = null;
    let canvas = null;
    let canvasCtx = null;
    let chatInput = null;

    async function startRecording() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert('Microphone access not available.');
            return;
        }

        try {
            stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            analyser = audioContext.createAnalyser();
            analyser.fftSize = 128;
            analyser.smoothingTimeConstant = 0.85;

            const source = audioContext.createMediaStreamSource(stream);
            source.connect(analyser);

            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) audioChunks.push(e.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                await transcribeAudio(audioBlob);
            };

            mediaRecorder.start();

            // Show recording UI
            micBtn.classList.add('recording');
            waveformContainer.classList.add('visible');

            // Set canvas size for retina
            const rect = waveformContainer.getBoundingClientRect();
            const dpr = window.devicePixelRatio || 1;
            canvas.width = rect.width * dpr;
            canvas.height = rect.height * dpr;
            canvasCtx.scale(dpr, dpr);

            drawWaveform(rect.width, rect.height);
        } catch (error) {
            console.error('Failed to start recording:', error);
            alert('Could not access microphone.');
        }
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
        }

        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }

        if (animationId) {
            cancelAnimationFrame(animationId);
            animationId = null;
        }

        if (audioContext) {
            audioContext.close();
            audioContext = null;
        }

        micBtn.classList.remove('recording');
        waveformContainer.classList.remove('visible');
    }

    function drawWaveform(width, height) {
        if (!analyser || !canvasCtx) return;

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        function draw() {
            if (!analyser) return;

            animationId = requestAnimationFrame(draw);
            analyser.getByteFrequencyData(dataArray);

            // Clear
            canvasCtx.clearRect(0, 0, width, height);

            // Draw centered bars
            const barCount = 32;
            const barWidth = 3;
            const gap = 2;
            const totalWidth = barCount * (barWidth + gap) - gap;
            const startX = (width - totalWidth) / 2;
            const centerY = height / 2;
            const maxHeight = height - 6;

            for (let i = 0; i < barCount; i++) {
                const dataIndex = Math.floor((i / barCount) * bufferLength * 0.6);
                const value = dataArray[dataIndex] / 255;
                const barHeight = Math.max(3, value * maxHeight);
                const x = startX + i * (barWidth + gap);

                canvasCtx.fillStyle = '#6366f1';
                canvasCtx.beginPath();
                canvasCtx.roundRect(x, centerY - barHeight / 2, barWidth, barHeight, 1.5);
                canvasCtx.fill();
            }
        }

        draw();
    }

    async function transcribeAudio(audioBlob) {
        micBtn.disabled = true;

        // Show loading in chat window
        const chatMessages = document.getElementById('chat-messages');
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message loading';
        loadingDiv.id = 'transcribe-loading';
        loadingDiv.innerHTML =
            '<div class="message-header">Transcribing</div>' +
            '<div class="loading-dots"><span></span><span></span><span></span></div>';
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const formData = new FormData();
            formData.append('file', audioBlob, 'recording.webm');

            const API_BASE = window.__TAURI__ ? 'http://localhost:2989' : '';
            const response = await fetch(API_BASE + '/api/transcribe', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Transcription failed');
            }

            const data = await response.json();

            if (data.text && data.text.trim()) {
                const newText = data.text.trim();
                // Append to existing text with space separator
                if (chatInput.value.trim()) {
                    chatInput.value = chatInput.value.trim() + ' ' + newText;
                } else {
                    chatInput.value = newText;
                }
                chatInput.classList.remove('has-selection');
                chatInput.dispatchEvent(new Event('input', { bubbles: true }));
                chatInput.focus();
            }
        } catch (error) {
            console.error('Transcription error:', error);
            alert('Transcription failed: ' + error.message);
        } finally {
            micBtn.disabled = false;
            // Remove loading indicator
            const loading = document.getElementById('transcribe-loading');
            if (loading) loading.remove();
        }
    }

    function handleMicClick() {
        if (micBtn.classList.contains('recording')) {
            stopRecording();
        } else {
            startRecording();
        }
    }

    // Public init function
    window.initWhisper = function() {
        // Get elements from HTML
        micBtn = document.getElementById('mic-btn');
        waveformContainer = document.getElementById('waveform-container');
        canvas = document.getElementById('waveform-canvas');
        chatInput = document.getElementById('chat-input');

        if (!micBtn || !waveformContainer || !canvas || !chatInput) {
            console.error('Whisper: Required elements not found');
            return;
        }

        canvasCtx = canvas.getContext('2d');
        micBtn.addEventListener('click', handleMicClick);
        micBtn.classList.add('enabled');
    };

    // Cleanup function
    window.destroyWhisper = function() {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
        }
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
        if (animationId) {
            cancelAnimationFrame(animationId);
        }
        if (audioContext) {
            audioContext.close();
        }

        if (micBtn) {
            micBtn.removeEventListener('click', handleMicClick);
            micBtn.classList.remove('recording');
            micBtn.classList.remove('enabled');
        }
        if (waveformContainer) {
            waveformContainer.classList.remove('visible');
        }
    };
})();
