import cv2
import numpy as np
import os
import time

from database import create_database, log_authentication


# ==========================================
# FILE PATHS
# ==========================================

FACE_DETECTOR = "models/face_detection_yunet_2023mar.onnx"

FACE_RECOGNIZER = "models/face_recognition_sface_2021dec.onnx"

REGISTERED_FILE = "data/registered_face.npy"


# ==========================================
# SETTINGS
# ==========================================

# SFace cosine similarity threshold
THRESHOLD = 0.363

# Maximum consecutive authentication failures
MAX_FAILURES = 3

# Authenticate once every 15 frames
CHECK_EVERY_N_FRAMES = 15


# ==========================================
# CREATE DATABASE
# ==========================================

create_database()


# ==========================================
# CHECK REGISTERED USER
# ==========================================

if not os.path.exists(REGISTERED_FILE):

    print("======================================")
    print("ERROR: No registered user found.")
    print("Please run register.py first.")
    print("======================================")

    exit()


# ==========================================
# LOAD REGISTERED BIOMETRIC FEATURE
# ==========================================

registered_feature = np.load(
    REGISTERED_FILE
)

print("Registered biometric data loaded.")


# ==========================================
# CREATE FACE DETECTOR
# ==========================================

detector = cv2.FaceDetectorYN.create(
    FACE_DETECTOR,
    "",
    (320, 320),
    0.9,
    0.3,
    5000
)


# ==========================================
# CREATE FACE RECOGNIZER
# ==========================================

recognizer = cv2.FaceRecognizerSF.create(
    FACE_RECOGNIZER,
    ""
)


# ==========================================
# OPEN WEBCAM
# ==========================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():

    print("======================================")
    print("ERROR: Cannot open webcam.")
    print("======================================")

    exit()


# ==========================================
# START MESSAGE
# ==========================================

print()
print("======================================")
print(" CONTINUOUS BIOMETRIC AUTHENTICATION")
print("======================================")
print("System monitoring started.")
print("Press Q to quit.")
print("======================================")


# ==========================================
# VARIABLES
# ==========================================

frame_count = 0

failed_attempts = 0

similarity = 0.0

status = "AUTHENTICATED"

session_locked = False


# ==========================================
# MAIN LOOP
# ==========================================

while True:

    # --------------------------------------
    # Read webcam frame
    # --------------------------------------

    success, frame = camera.read()

    if not success:

        print("Failed to read webcam.")
        break


    # --------------------------------------
    # Flip webcam image
    # --------------------------------------

    frame = cv2.flip(frame, 1)


    # --------------------------------------
    # Get frame dimensions
    # --------------------------------------

    height, width = frame.shape[:2]


    # --------------------------------------
    # Set detector input size
    # --------------------------------------

    detector.setInputSize(
        (width, height)
    )


    # --------------------------------------
    # Detect faces
    # --------------------------------------

    _, faces = detector.detect(frame)


    frame_count += 1


    # ======================================
    # CONTINUOUS AUTHENTICATION
    # ======================================

    if frame_count % CHECK_EVERY_N_FRAMES == 0:

        # ----------------------------------
        # Face found
        # ----------------------------------

        if faces is not None and len(faces) > 0:

            # Use first detected face
            face = faces[0]

            try:

                # --------------------------
                # Align face
                # --------------------------

                aligned_face = recognizer.alignCrop(
                    frame,
                    face
                )


                # --------------------------
                # Extract current feature
                # --------------------------

                current_feature = recognizer.feature(
                    aligned_face
                )


                # --------------------------
                # Compare with registered face
                # --------------------------

                similarity = recognizer.match(
                    registered_feature,
                    current_feature,
                    cv2.FaceRecognizerSF_FR_COSINE
                )


                similarity = float(similarity)


                print(
                    "Authentication similarity:",
                    round(similarity, 4)
                )


                # ==================================
                # AUTHENTICATION DECISION
                # ==================================

                if similarity >= THRESHOLD:

                    # ------------------------------
                    # User authenticated
                    # ------------------------------

                    status = "AUTHENTICATED"

                    # Reset failed attempts
                    failed_attempts = 0


                    print(
                        "✓ User verified"
                    )


                    # Save authentication log
                    log_authentication(
                        "AUTHENTICATED",
                        similarity,
                        failed_attempts
                    )


                else:

                    # ------------------------------
                    # Authentication failed
                    # ------------------------------

                    failed_attempts += 1

                    status = "UNAUTHORIZED"


                    print(
                        "✗ Authentication failed:",
                        failed_attempts,
                        "/",
                        MAX_FAILURES
                    )


                    # Save failed authentication
                    log_authentication(
                        "UNAUTHORIZED",
                        similarity,
                        failed_attempts
                    )


            except Exception as error:

                print(
                    "Recognition error:",
                    error
                )


        # ==================================
        # NO FACE FOUND
        # ==================================

        else:

            failed_attempts += 1

            status = "NO FACE"


            print(
                "✗ No face detected:",
                failed_attempts,
                "/",
                MAX_FAILURES
            )


            # Save no-face event
            log_authentication(
                "NO FACE",
                0.0,
                failed_attempts
            )


    # ======================================
    # SESSION LOCK
    # ======================================

    if failed_attempts >= MAX_FAILURES:

        status = "SESSION LOCKED"

        session_locked = True


        print()
        print("======================================")
        print("          SECURITY ALERT")
        print("======================================")
        print("Unauthorized user detected.")
        print("Session has been locked.")
        print("======================================")


        # Save session lock event
        log_authentication(
            "SESSION LOCKED",
            similarity,
            failed_attempts
        )


        # Display locked message
        cv2.putText(
            frame,
            "SESSION LOCKED",
            (50, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 0, 255),
            3
        )


        cv2.putText(
            frame,
            "Unauthorized User",
            (50, 145),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )


        # Show locked screen for 3 seconds
        cv2.imshow(
            "Continuous Biometric Authentication",
            frame
        )

        cv2.waitKey(3000)

        break


    # ======================================
    # SELECT STATUS COLOR
    # ======================================

    if status == "AUTHENTICATED":

        status_color = (0, 255, 0)

    elif status == "UNAUTHORIZED":

        status_color = (0, 0, 255)

    else:

        status_color = (0, 165, 255)


    # ======================================
    # DRAW FACE RECTANGLE
    # ======================================

    if faces is not None and len(faces) > 0:

        face = faces[0]

        x, y, w, h = face[:4].astype(int)


        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            status_color,
            2
        )


    # ======================================
    # DISPLAY STATUS
    # ======================================

    cv2.putText(
        frame,
        status,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        status_color,
        2
    )


    # ======================================
    # DISPLAY SIMILARITY
    # ======================================

    cv2.putText(
        frame,
        f"Similarity: {similarity:.3f}",
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )


    # ======================================
    # DISPLAY FAILED ATTEMPTS
    # ======================================

    cv2.putText(
        frame,
        f"Failed Checks: {failed_attempts}/{MAX_FAILURES}",
        (20, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )


    # ======================================
    # DISPLAY MONITORING MESSAGE
    # ======================================

    cv2.putText(
        frame,
        "Continuous Monitoring Active",
        (20, height - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )


    # ======================================
    # SHOW WEBCAM
    # ======================================

    cv2.imshow(
        "Continuous Biometric Authentication",
        frame
    )


    # ======================================
    # QUIT WITH Q
    # ======================================

    if cv2.waitKey(1) & 0xFF == ord("q"):

        print()
        print("User stopped monitoring.")

        break


# ==========================================
# CLEANUP
# ==========================================

camera.release()

cv2.destroyAllWindows()


# ==========================================
# FINAL MESSAGE
# ==========================================

print()
print("======================================")

if session_locked:

    print("SESSION STATUS: LOCKED")

else:

    print("SESSION STATUS: STOPPED")

print("Continuous authentication stopped.")

print("======================================")