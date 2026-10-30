/**
 * CONTINUOUS BIOMETRIC SENTINEL MONITOR
 * Automated continuous authentication loop for secure dashboard
 */

class ContinuousSentinel {
  constructor(cameraInstance, config = {}) {
    this.camera = cameraInstance;
    this.intervalMs = config.intervalMs || 1800; // Check every 1.8 seconds
    this.maxFailures = config.maxFailures || 3;
    this.threshold = config.threshold || 0.363;
    
    this.isRunning = false;
    this.timerId = null;
    this.isProcessing = false;

    // UI Element References
    this.statusBadge = document.getElementById(config.statusBadgeId || 'sentinel-status');
    this.similarityValue = document.getElementById(config.similarityValueId || 'sentinel-similarity');
    this.failuresValue = document.getElementById(config.failuresValueId || 'sentinel-failures');
    this.simBar = document.getElementById(config.simBarId || 'sentinel-sim-bar');
    this.heartbeatDot = document.getElementById(config.heartbeatDotId || 'sentinel-heartbeat');
    this.alertBox = document.getElementById(config.alertBoxId || 'sentinel-alert');
    
    // Callbacks
    this.onLocked = config.onLocked || null;
  }

  start() {
    if (this.isRunning) return;
    this.isRunning = true;
    this.updateStatusDisplay('STARTING', 0.0, 0, 'Sentinel initializing...');
    
    // Begin continuous loop
    this.scheduleNextCheck(500);
  }

  stop() {
    this.isRunning = false;
    if (this.timerId) {
      clearTimeout(this.timerId);
      this.timerId = null;
    }
    this.updateStatusDisplay('PAUSED', 0.0, 0, 'Monitoring paused');
    this.camera.clearOverlay();
  }

  scheduleNextCheck(delay) {
    if (!this.isRunning) return;
    this.timerId = setTimeout(() => {
      this.performCheck();
    }, delay || this.intervalMs);
  }

  async performCheck() {
    if (!this.isRunning || this.isProcessing) return;
    if (!this.camera || !this.camera.isStreaming) {
      this.scheduleNextCheck(1000);
      return;
    }

    this.isProcessing = true;
    if (this.heartbeatDot) {
      this.heartbeatDot.classList.add('pulse-dot-green');
    }

    const frameBase64 = this.camera.captureBase64(0.85);
    if (!frameBase64) {
      this.isProcessing = false;
      this.scheduleNextCheck(1000);
      return;
    }

    try {
      const response = await fetch('/api/continuous-check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: frameBase64 })
      });

      const data = await response.json();

      if (data.locked) {
        // SECURITY BREACH LOCKOUT!
        this.isRunning = false;
        this.camera.playChime('lock');
        this.camera.drawBoundingBox(data.box, 'SESSION LOCKED', 'SECURITY LOCKOUT');
        this.updateStatusDisplay('SESSION LOCKED', data.similarity || 0, data.failed_attempts || 3, data.message);

        if (this.onLocked) {
          this.onLocked(data);
        } else if (data.redirect_url) {
          setTimeout(() => {
            window.location.href = data.redirect_url;
          }, 800);
        }
        return;
      }

      // Update UI metrics
      const status = data.status || 'CHECKING';
      const sim = data.similarity || 0.0;
      const failures = data.failed_attempts || 0;

      this.updateStatusDisplay(status, sim, failures, data.message);

      // Draw bounding box
      if (data.box) {
        const label = `${status} (${(sim * 100).toFixed(0)}%)`;
        this.camera.drawBoundingBox(data.box, status, label);
      } else {
        this.camera.clearOverlay();
      }

      // Audio feedback on state transitions
      if (status === 'UNAUTHORIZED' || status === 'NO FACE') {
        this.camera.playChime('warning');
      }

    } catch (err) {
      console.warn('[ContinuousSentinel] Verification request error:', err);
      this.updateStatusDisplay('NETWORK LAG', 0.0, 0, 'Reconnecting Sentinel API...');
    } finally {
      this.isProcessing = false;
      if (this.isRunning) {
        this.scheduleNextCheck(this.intervalMs);
      }
    }
  }

  updateStatusDisplay(status, similarity, failures, message) {
    if (this.statusBadge) {
      this.statusBadge.textContent = status;
      this.statusBadge.className = 'cyber-badge';

      if (status === 'AUTHENTICATED') {
        this.statusBadge.classList.add('cyber-badge-success');
      } else if (status === 'UNAUTHORIZED' || status === 'SESSION LOCKED') {
        this.statusBadge.classList.add('cyber-badge-danger');
      } else if (status === 'NO FACE') {
        this.statusBadge.classList.add('cyber-badge-warning');
      } else {
        this.statusBadge.classList.add('cyber-badge-neutral');
      }
    }

    if (this.similarityValue) {
      this.similarityValue.textContent = similarity.toFixed(3);
    }

    if (this.failuresValue) {
      this.failuresValue.textContent = `${failures}/${this.maxFailures}`;
      if (failures > 0) {
        this.failuresValue.style.color = '#ef4444';
      } else {
        this.failuresValue.style.color = '#10b981';
      }
    }

    if (this.simBar) {
      const percentage = Math.min(Math.max(similarity * 100, 0), 100);
      this.simBar.style.width = `${percentage}%`;
      if (similarity >= this.threshold) {
        this.simBar.style.backgroundColor = '#10b981';
      } else if (similarity > 0.2) {
        this.simBar.style.backgroundColor = '#f59e0b';
      } else {
        this.simBar.style.backgroundColor = '#ef4444';
      }
    }

    if (this.alertBox && message) {
      this.alertBox.textContent = message;
    }
  }
}
