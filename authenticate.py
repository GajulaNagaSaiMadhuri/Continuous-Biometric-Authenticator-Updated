import cv2
import numpy as np
import os

# -----------------------------
# Model paths
# -----------------------------
FACE_DETECTOR = "models/face_detection_yunet_2023mar.onnx"
FACE_RECOGNIZER = "models/face_recognition_sface_2021dec.onnx"

# Registered biometric data
REGISTERED_FILE = "data/registered_face.npy"

# -----------------------------
# Check registration
# -----------------------------
if not os.path.exists(REGISTERED_FILE):
    print("No registered user found.")
    print("Please run register.py first.")
    exit()

# Load registered feature
registered_feature = np.load(REGISTERED_FILE)

# -----------------------------
# Create detector
# -----------------------------
detector = cv2.FaceDetectorYN.create(
    FACE_DETECTOR,
    "",
    (320, 320),
    0.9,
    0.3,
    5000
)

# -----------------------------
# Create recognizer
# -----------------------------
recognizer = cv2.FaceRecognizerSF.create(
    FACE_RECOGNIZER,
    ""
)

# -----------------------------
# Open webcam
# -----------------------------
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Cannot open webcam")
    exit()

print("===================================")
print("       BIOMETRIC AUTHENTICATION")
print("===================================")
print("Look at the camera.")
print("Press Q to quit.")

# SFace cosine similarity threshold
THRESHOLD = 0.363

while True:

    success, frame = camera.read()

    if not success:
        print("Failed to read webcam")
        break

    # Mirror image
    frame = cv2.flip(frame, 1)

    height, width = frame.shape[:2]

    # Set detector input size
    detector.setInputSize((width, height))

    # Detect face
    _, faces = detector.detect(frame)

    if faces is not None and len(faces) > 0:

        # Use first detected face
        face = faces[0]

        # Face coordinates
        x, y, w, h = face[:4].astype(int)

        try:

            # Align face
            aligned_face = recognizer.alignCrop(
                frame,
                face
            )

            # Extract current biometric feature
            current_feature = recognizer.feature(
                aligned_face
            )

            # Compare with registered feature
            similarity = recognizer.match(
                registered_feature,
                current_feature,
                cv2.FaceRecognizerSF_FR_COSINE
            )

            print(
                "Similarity:",
                round(float(similarity), 4)
            )

            # -----------------------------
            # Authentication decision
            # -----------------------------
            if similarity >= THRESHOLD:

                status = "AUTHENTICATED"
                text_color = (0, 255, 0)

            else:

                status = "UNAUTHORIZED"
                text_color = (0, 0, 255)

            # Draw face box
            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                text_color,
                2
            )

            # Display status
            cv2.putText(
                frame,
                status,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                text_color,
                2
            )

            # Display similarity
            cv2.putText(
                frame,
                f"Similarity: {similarity:.3f}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

        except Exception as e:

            print("Recognition error:", e)

    else:

        cv2.putText(
            frame,
            "NO FACE DETECTED",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )

    # Show webcam
    cv2.imshow(
        "Continuous Biometric Authentication",
        frame
    )

    # Quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()

print("Authentication stopped.")