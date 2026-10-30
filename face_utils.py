import os
import base64
import cv2
import numpy as np
from config import FACE_DETECTOR, FACE_RECOGNIZER, THRESHOLD, MAX_FAILURES, REGISTERED_FILE, EMBEDDINGS_DIR


class BiometricEngine:
    """
    Central biometric engine utilizing OpenCV's YuNet face detector
    and SFace face recognizer ONNX models. Reuses the exact parameters
    and algorithms from register.py, authenticate.py, and continuous_auth.py.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BiometricEngine, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        if not os.path.exists(FACE_DETECTOR):
            raise FileNotFoundError(f"YuNet model not found at {FACE_DETECTOR}")
        if not os.path.exists(FACE_RECOGNIZER):
            raise FileNotFoundError(f"SFace model not found at {FACE_RECOGNIZER}")

        # Initialize YuNet Face Detector (identical configuration to register.py / authenticate.py)
        self.detector = cv2.FaceDetectorYN.create(
            FACE_DETECTOR,
            "",
            (320, 320),
            0.9,
            0.3,
            5000
        )

        # Initialize SFace Face Recognizer
        self.recognizer = cv2.FaceRecognizerSF.create(
            FACE_RECOGNIZER,
            ""
        )
        print("[BiometricEngine] YuNet and SFace models loaded successfully.")

    def decode_base64_image(self, base64_str):
        """
        Decodes a base64 string from browser webcam (data:image/jpeg;base64,...)
        into an OpenCV BGR numpy array.
        """
        try:
            if "," in base64_str:
                base64_str = base64_str.split(",")[1]
            image_bytes = base64.b64decode(base64_str)
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            print(f"[BiometricEngine] Error decoding image: {e}")
            return None

    def detect_faces(self, frame):
        """
        Detects faces in the given frame using YuNet.
        Returns faces array, or None.
        """
        if frame is None:
            return None

        height, width = frame.shape[:2]
        self.detector.setInputSize((width, height))
        _, faces = self.detector.detect(frame)
        return faces

    def extract_feature(self, frame, face):
        """
        Crops and aligns face using SFace recognizer, then extracts 128-D feature vector.
        """
        aligned_face = self.recognizer.alignCrop(frame, face)
        feature = self.recognizer.feature(aligned_face)
        return feature

    def compute_similarity(self, feature1, feature2):
        """
        Computes cosine similarity between two 128-D SFace feature vectors.
        """
        similarity = self.recognizer.match(
            feature1,
            feature2,
            cv2.FaceRecognizerSF_FR_COSINE
        )
        return float(similarity)

    def save_user_feature(self, username, feature):
        """
        Saves user feature vector to a secure .npy file in data/embeddings.
        Also updates legacy data/registered_face.npy for backward compatibility.
        """
        os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
        safe_username = "".join(c for c in username if c.isalnum() or c in ("_", "-")).lower()
        feature_path = os.path.join(EMBEDDINGS_DIR, f"{safe_username}_feature.npy")
        np.save(feature_path, feature)

        # Backward compatibility with single-user scripts
        try:
            np.save(REGISTERED_FILE, feature)
        except Exception:
            pass

        return feature_path

    def load_user_feature(self, feature_path):
        """Loads a user feature vector from disk."""
        if not os.path.exists(feature_path):
            return None
        return np.load(feature_path)

    def process_frame_for_registration(self, frame):
        """
        Validates frame for registration: ensures exactly one clear face is visible.
        Returns (success, message, feature, face_box).
        """
        faces = self.detect_faces(frame)
        if faces is None or len(faces) == 0:
            return False, "No face detected. Please face the camera with good lighting.", None, None

        if len(faces) > 1:
            return False, "Multiple faces detected. Please ensure only one person is in frame.", None, None

        face = faces[0]
        x, y, w, h = face[:4].astype(int)
        confidence = float(face[-1]) if len(face) > 14 else 0.95

        try:
            feature = self.extract_feature(frame, face)
            return True, "Face captured successfully.", feature, [int(x), int(y), int(w), int(h)]
        except Exception as e:
            return False, f"Feature extraction failed: {str(e)}", None, None

    def verify_against_target(self, frame, target_feature):
        """
        Verifies face in frame against a target registered template (1:1 continuous auth).
        Returns dict with status, similarity, box, and confidence.
        """
        faces = self.detect_faces(frame)
        if faces is None or len(faces) == 0:
            return {
                "detected": False,
                "status": "NO FACE",
                "similarity": 0.0,
                "box": None,
                "message": "No face detected in camera view"
            }

        face = faces[0]
        x, y, w, h = face[:4].astype(int)
        box = [int(x), int(y), int(w), int(h)]

        try:
            current_feature = self.extract_feature(frame, face)
            similarity = self.compute_similarity(target_feature, current_feature)

            if similarity >= THRESHOLD:
                status = "AUTHENTICATED"
                message = "Face verified"
            else:
                status = "UNAUTHORIZED"
                message = "Biometric mismatch"

            return {
                "detected": True,
                "status": status,
                "similarity": round(similarity, 4),
                "box": box,
                "message": message
            }
        except Exception as e:
            return {
                "detected": True,
                "status": "ERROR",
                "similarity": 0.0,
                "box": box,
                "message": str(e)
            }

    def identify_among_users(self, frame, users_list):
        """
        Performs 1:N face identification across all registered users.
        Returns best match above threshold, or UNAUTHORIZED / NO FACE.
        """
        faces = self.detect_faces(frame)
        if faces is None or len(faces) == 0:
            return {
                "detected": False,
                "status": "NO FACE",
                "similarity": 0.0,
                "matched_user": None,
                "box": None,
                "message": "No face detected"
            }

        face = faces[0]
        x, y, w, h = face[:4].astype(int)
        box = [int(x), int(y), int(w), int(h)]

        try:
            current_feature = self.extract_feature(frame, face)

            best_similarity = -1.0
            best_user = None

            for user in users_list:
                feature_path = user.get("feature_path")
                if feature_path and os.path.exists(feature_path):
                    user_feature = np.load(feature_path)
                    sim = self.compute_similarity(user_feature, current_feature)
                    if sim > best_similarity:
                        best_similarity = sim
                        best_user = user

            if best_similarity >= THRESHOLD and best_user is not None:
                return {
                    "detected": True,
                    "status": "AUTHENTICATED",
                    "similarity": round(best_similarity, 4),
                    "matched_user": {
                        "id": best_user["id"],
                        "username": best_user["username"],
                        "full_name": best_user["full_name"],
                        "role": best_user.get("role", "Authorized User")
                    },
                    "box": box,
                    "message": f"Welcome back, {best_user['full_name']}"
                }
            else:
                return {
                    "detected": True,
                    "status": "UNAUTHORIZED",
                    "similarity": round(max(best_similarity, 0.0), 4),
                    "matched_user": None,
                    "box": box,
                    "message": "Face not recognized"
                }

        except Exception as e:
            return {
                "detected": True,
                "status": "ERROR",
                "similarity": 0.0,
                "matched_user": None,
                "box": box,
                "message": str(e)
            }


# Singleton helper instance
biometric_engine = BiometricEngine()
