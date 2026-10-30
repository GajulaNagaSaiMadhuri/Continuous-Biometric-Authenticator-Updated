import cv2

# Model paths
FACE_DETECTOR = "models/face_detection_yunet_2023mar.onnx"
FACE_RECOGNIZER = "models/face_recognition_sface_2021dec.onnx"

# Create face detector
detector = cv2.FaceDetectorYN.create(
    FACE_DETECTOR,
    "",
    (320, 320),
    0.9,
    0.3,
    5000
)

# Create face recognizer
recognizer = cv2.FaceRecognizerSF.create(
    FACE_RECOGNIZER,
    ""
)

# Open webcam
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Cannot open webcam")
    exit()

print("Face recognition test started")
print("Press Q to quit")

while True:

    success, frame = camera.read()

    if not success:
        print("Failed to read webcam")
        break

    # Flip camera like a mirror
    frame = cv2.flip(frame, 1)

    # Set detector input size
    height, width = frame.shape[:2]
    detector.setInputSize((width, height))

    # Detect faces
    _, faces = detector.detect(frame)

    if faces is not None:

        for face in faces:

            # Face bounding box
            x, y, w, h = face[:4].astype(int)

            # Draw rectangle
            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2
            )

            # Display message
            cv2.putText(
                frame,
                "Face Detected",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

    cv2.imshow("Biometric Face Test", frame)

    # Press Q to quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()

print("Test completed")