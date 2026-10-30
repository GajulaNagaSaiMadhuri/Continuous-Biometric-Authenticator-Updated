import cv2
import os
import numpy as np

# Model paths
FACE_DETECTOR = "models/face_detection_yunet_2023mar.onnx"
FACE_RECOGNIZER = "models/face_recognition_sface_2021dec.onnx"

# Create detector
detector = cv2.FaceDetectorYN.create(
    FACE_DETECTOR,
    "",
    (320, 320),
    0.9,
    0.3,
    5000
)

# Create recognizer
recognizer = cv2.FaceRecognizerSF.create(
    FACE_RECOGNIZER,
    ""
)

# Folder for biometric data
os.makedirs("data", exist_ok=True)

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Cannot open webcam")
    exit()

print("===================================")
print("     BIOMETRIC USER REGISTRATION")
print("===================================")
print("Look directly at the camera.")
print("Press S to save your biometric data.")
print("Press Q to quit.")

saved = False

while True:

    success, frame = camera.read()

    if not success:
        print("Failed to read webcam")
        break

    frame = cv2.flip(frame, 1)

    height, width = frame.shape[:2]

    detector.setInputSize((width, height))

    _, faces = detector.detect(frame)

    if faces is not None and len(faces) > 0:

        # Use the first detected face
        face = faces[0]

        # Face coordinates
        x, y, w, h = face[:4].astype(int)

        # Draw rectangle
        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            "Face Detected",
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            "Press S to Register",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        # Press S to save
        key = cv2.waitKey(1) & 0xFF

        if key == ord("s"):

            try:
                # Align and crop face for SFace
                aligned_face = recognizer.alignCrop(frame, face)

                # Extract biometric feature
                feature = recognizer.feature(aligned_face)

                # Save biometric feature
                np.save("data/registered_face.npy", feature)

                print("\nRegistration successful!")
                print("Biometric data saved to:")
                print("data/registered_face.npy")

                saved = True
                break

            except Exception as e:
                print("Registration error:", e)

        elif key == ord("q"):
            break

    else:

        cv2.putText(
            frame,
            "No Face Detected",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

    cv2.imshow("Biometric Registration", frame)

camera.release()
cv2.destroyAllWindows()

if saved:
    print("\nUser registration completed successfully.")
else:
    print("\nRegistration cancelled.")