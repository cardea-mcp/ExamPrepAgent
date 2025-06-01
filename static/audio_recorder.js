// static/audio_recorder.js
class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
        this.recordingStartTime = null;
        this.maxRecordingTime = 60000; // 60 seconds max
        this.recordingTimer = null;
        
        // Audio constraints
        this.constraints = {
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        };
    }

    async initialize() {
        try {
            // Check for browser support
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Browser does not support audio recording');
            }

            if (!window.MediaRecorder) {
                throw new Error('MediaRecorder is not supported in this browser');
            }

            return true;
        } catch (error) {
            console.error('Audio recorder initialization failed:', error);
            return false;
        }
    }

    async startRecording() {
        try {
            if (this.isRecording) {
                console.warn('Recording is already in progress');
                return false;
            }

            // Request microphone permission
            this.stream = await navigator.mediaDevices.getUserMedia(this.constraints);
            
            // Create MediaRecorder instance
            const options = {
                mimeType: this.getSupportedMimeType(),
                audioBitsPerSecond: 128000
            };

            this.mediaRecorder = new MediaRecorder(this.stream, options);
            this.audioChunks = [];

            // Set up event listeners
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                this.handleRecordingStop();
            };

            this.mediaRecorder.onerror = (event) => {
                console.error('MediaRecorder error:', event.error);
                this.stopRecording();
            };

            // Start recording
            this.mediaRecorder.start(1000); // Collect data every second
            this.isRecording = true;
            this.recordingStartTime = Date.now();

            // Set maximum recording time
            this.recordingTimer = setTimeout(() => {
                if (this.isRecording) {
                    this.stopRecording();
                }
            }, this.maxRecordingTime);

            this.onRecordingStart();
            return true;

        } catch (error) {
            console.error('Failed to start recording:', error);
            this.cleanup();
            throw error;
        }
    }

    stopRecording() {
        try {
            if (!this.isRecording || !this.mediaRecorder) {
                return false;
            }

            this.isRecording = false;
            
            if (this.mediaRecorder.state !== 'inactive') {
                this.mediaRecorder.stop();
            }

            this.cleanup();
            return true;

        } catch (error) {
            console.error('Failed to stop recording:', error);
            this.cleanup();
            return false;
        }
    }

    handleRecordingStop() {
        if (this.audioChunks.length === 0) {
            console.warn('No audio data recorded');
            this.onRecordingError('No audio data recorded');
            return;
        }

        // Create audio blob
        const audioBlob = new Blob(this.audioChunks, { 
            type: this.getSupportedMimeType() 
        });

        // Calculate recording duration
        const duration = this.recordingStartTime ? 
            (Date.now() - this.recordingStartTime) / 1000 : 0;

        this.onRecordingStop(audioBlob, duration);
    }

    cleanup() {
        // Clear timer
        if (this.recordingTimer) {
            clearTimeout(this.recordingTimer);
            this.recordingTimer = null;
        }

        // Stop media stream
        if (this.stream) {
            this.stream.getTracks().forEach(track => {
                track.stop();
            });
            this.stream = null;
        }

        // Reset recorder
        this.mediaRecorder = null;
        this.recordingStartTime = null;
    }

    getSupportedMimeType() {
        // Prefer WebM with Opus, fall back to other formats
        const types = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/mp4',
            'audio/wav'
        ];

        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) {
                return type;
            }
        }

        return 'audio/webm'; // Default fallback
    }

    getRecordingDuration() {
        if (!this.recordingStartTime) return 0;
        return (Date.now() - this.recordingStartTime) / 1000;
    }

    // Event handlers (to be overridden)
    onRecordingStart() {
        console.log('Recording started');
    }

    onRecordingStop(audioBlob, duration) {
        console.log('Recording stopped', { duration, size: audioBlob.size });
    }

    onRecordingError(error) {
        console.error('Recording error:', error);
    }

    // Static method to check browser support
    static async checkBrowserSupport() {
        try {
            // Check for required APIs
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                return { supported: false, reason: 'getUserMedia not supported' };
            }

            if (!window.MediaRecorder) {
                return { supported: false, reason: 'MediaRecorder not supported' };
            }

            // Test microphone access (will prompt for permission)
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach(track => track.stop());

            return { supported: true, reason: null };

        } catch (error) {
            return { 
                supported: false, 
                reason: error.name === 'NotAllowedError' ? 
                    'Microphone permission denied' : 
                    'Microphone access failed'
            };
        }
    }
}

// Audio player utility for playback
class AudioPlayer {
    constructor() {
        this.audioElement = null;
        this.isPlaying = false;
    }

    createAudioElement(audioBlob) {
        if (this.audioElement) {
            this.destroyAudioElement();
        }

        this.audioElement = document.createElement('audio');
        this.audioElement.controls = true;
        this.audioElement.src = URL.createObjectURL(audioBlob);
        
        this.audioElement.addEventListener('ended', () => {
            this.isPlaying = false;
            this.onPlaybackEnd();
        });

        this.audioElement.addEventListener('play', () => {
            this.isPlaying = true;
            this.onPlaybackStart();
        });

        this.audioElement.addEventListener('pause', () => {
            this.isPlaying = false;
            this.onPlaybackPause();
        });

        return this.audioElement;
    }

    play() {
        if (this.audioElement && !this.isPlaying) {
            this.audioElement.play();
        }
    }

    pause() {
        if (this.audioElement && this.isPlaying) {
            this.audioElement.pause();
        }
    }

    destroyAudioElement() {
        if (this.audioElement) {
            this.audioElement.pause();
            URL.revokeObjectURL(this.audioElement.src);
            this.audioElement = null;
            this.isPlaying = false;
        }
    }

    // Event handlers (to be overridden)
    onPlaybackStart() {}
    onPlaybackPause() {}
    onPlaybackEnd() {}
}

// Export for use in other scripts
window.AudioRecorder = AudioRecorder;
window.AudioPlayer = AudioPlayer;