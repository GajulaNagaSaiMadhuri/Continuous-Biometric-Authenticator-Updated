/**
 * CONTINUOUS BIOMETRIC AUTHENTICATOR
 * Client-Side Camera & WebRTC Audio/HUD Engine
 */

class BiometricCamera {
  constructor(videoElementId, canvasElementId, options = {}) {
    this.video = document.getElementById(videoElementId);
    this.canvas = document.getElementById(canvasElementId);
    this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
    this.stream = null;
    this.isStreaming = false;
    this.options = Object.assign({
      width: 640,
      height: 480,
      onReady: null,
      onError: null
    }, options);

    this.audioCtx = null;
  }

  // Initialize Web Audio API for cybersecurity feedback sound effects
  initAudio() {
    if (!this.audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        this.audioCtx = new AudioContext();
      }
    }
  }

  playChime(type = 'success') {
    try {
      this.initAudio();
      if (!this.audioCtx) return;
      if (this.audioCtx.state === 'suspended') {
        this.audioCtx.resume();
      }

      const now = this.audioCtx.currentTime;
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();

      osc.connect(gain);
      gain.connect(this.audioCtx.destination);

      if (type === 'success') {
        // High-tech ascending cyber chirp
        osc.type = 'sine';
        osc.frequency.setValueAtTime(587.33, now); // D5
        osc.frequency.exponentialRampToValueAtTime(880.00, now + 0.15); // A5
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.3);
        osc.start(now);
        osc.stop(now + 0.3);
      } else if (type === 'warning') {
        // Double alert tone
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(330, now);
        osc.frequency.setValueAtTime(260, now + 0.1);
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.25);
        osc.start(now);
        osc.stop(now + 0.25);
      } else if (type === 'lock') {
        // Security breach alert siren
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(800, now);
        osc.frequency.linearRampToValueAtTime(400, now + 0.2);
        osc.frequency.linearRampToValueAtTime(800, now + 0.4);
        gain.gain.setValueAtTime(0.25, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.5);
        osc.start(now);
        osc.stop(now + 0.5);
      }
    } catch (e) {
      console.warn("Audio feedback error:", e);
    }
  }

  // Request browser camera stream
  async start() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      const errorMsg = "Webcam API (getUserMedia) not supported in this browser. Please use Chrome, Edge, or Firefox.";
      if (this.options.onError) this.options.onError(errorMsg);
      return false;
    }

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: this.options.width },
          height: { ideal: this.options.height },
          facingMode: "user"
        },
        audio: false
      });

      this.video.srcObject = this.stream;

      return new Promise((resolve) => {
        this.video.onloadedmetadata = () => {
          this.video.play();
          this.isStreaming = true;
          if (this.canvas) {
            this.canvas.width = this.video.videoWidth || this.options.width;
            this.canvas.height = this.video.videoHeight || this.options.height;
          }
          if (this.options.onReady) this.options.onReady(this.video);
          resolve(true);
        };
      });
    } catch (err) {
      let friendlyMessage = "Could not open camera.";
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        friendlyMessage = "Camera access was denied. Please allow camera permissions in your browser address bar.";
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        friendlyMessage = "No webcam device detected. Please attach a camera and refresh.";
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        friendlyMessage = "Camera is already in use by another application. Please close other programs using the camera.";
      } else {
        friendlyMessage = `Camera error: ${err.message || err.name}`;
      }

      if (this.options.onError) this.options.onError(friendlyMessage);
      return false;
    }
  }

  stop() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    this.isStreaming = false;
    if (this.video) {
      this.video.srcObject = null;
    }
  }

  // Capture current frame as Base64 JPEG
  captureBase64(quality = 0.88) {
    if (!this.isStreaming || !this.video) return null;

    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = this.video.videoWidth || this.options.width;
    tempCanvas.height = this.video.videoHeight || this.options.height;
    const tempCtx = tempCanvas.getContext('2d');

    // Draw the image onto canvas
    tempCtx.drawImage(this.video, 0, 0, tempCanvas.width, tempCanvas.height);
    return tempCanvas.toDataURL('image/jpeg', quality);
  }

  // Draw HUD bounding box on live overlay canvas
  drawBoundingBox(box, status = 'AUTHENTICATED', label = '') {
    if (!this.ctx || !this.canvas) return;

    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    if (!box) return;

    const [x, y, w, h] = box;

    let color = '#06b6d4'; // default cyan
    if (status === 'AUTHENTICATED') color = '#10b981'; // emerald
    else if (status === 'UNAUTHORIZED' || status === 'SESSION LOCKED') color = '#ef4444'; // crimson
    else if (status === 'NO FACE') color = '#f59e0b'; // amber

    this.ctx.save();
    this.ctx.strokeStyle = color;
    this.ctx.lineWidth = 3;

    // Draw tech bracket corners
    const cornerLength = Math.min(w, h) * 0.22;

    // Top-left
    this.ctx.beginPath();
    this.ctx.moveTo(x, y + cornerLength);
    this.ctx.lineTo(x, y);
    this.ctx.lineTo(x + cornerLength, y);
    this.ctx.stroke();

    // Top-right
    this.ctx.beginPath();
    this.ctx.moveTo(x + w - cornerLength, y);
    this.ctx.lineTo(x + w, y);
    this.ctx.lineTo(x + w, y + cornerLength);
    this.ctx.stroke();

    // Bottom-left
    this.ctx.beginPath();
    this.ctx.moveTo(x, y + h - cornerLength);
    this.ctx.lineTo(x, y + h);
    this.ctx.lineTo(x + cornerLength, y + h);
    this.ctx.stroke();

    // Bottom-right
    this.ctx.beginPath();
    this.ctx.moveTo(x + w - cornerLength, y + h);
    this.ctx.lineTo(x + w, y + h);
    this.ctx.lineTo(x + w, y + h - cornerLength);
    this.ctx.stroke();

    // Label tag
    if (label) {
      this.ctx.fillStyle = color;
      this.ctx.font = 'bold 14px "JetBrains Mono", monospace';
      const textWidth = this.ctx.measureText(label).width;
      this.ctx.fillRect(x, Math.max(0, y - 24), textWidth + 12, 22);

      this.ctx.fillStyle = '#020617';
      this.ctx.fillText(label, x + 6, Math.max(16, y - 8));
    }

    this.ctx.restore();
  }

  clearOverlay() {
    if (this.ctx && this.canvas) {
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
  }
}
