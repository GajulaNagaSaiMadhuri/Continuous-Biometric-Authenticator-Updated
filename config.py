import os

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")
EMBEDDINGS_DIR = os.path.join(DATA_DIR, "embeddings")

# Model Paths
FACE_DETECTOR = os.path.join(MODELS_DIR, "face_detection_yunet_2023mar.onnx")
FACE_RECOGNIZER = os.path.join(MODELS_DIR, "face_recognition_sface_2021dec.onnx")

# Legacy single-user file (for backward compatibility with desktop scripts)
REGISTERED_FILE = os.path.join(DATA_DIR, "registered_face.npy")

# Database Path
DATABASE = os.path.join(BASE_DIR, "authentication.db")

# Biometric Verification Parameters (matches continuous_auth.py)
THRESHOLD = 0.363           # SFace Cosine Similarity Threshold
MAX_FAILURES = 3            # Consecutive unauthorized/no-face checks before lockout
CHECK_EVERY_N_FRAMES = 15   # Verification sampling interval

# Flask Security Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "continuous-biometric-cyber-sentinel-2026-key")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# Ensure data directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
