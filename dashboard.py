import os
import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk

from database import create_database, log_authentication, show_logs

# -------------------- Configuration --------------------
FACE_DETECTOR = "models/face_detection_yunet_2023mar.onnx"
FACE_RECOGNIZER = "models/face_recognition_sface_2021dec.onnx"
REGISTERED_FILE = "data/registered_face.npy"

# Tune this using genuine and non-genuine samples from your own camera.
THRESHOLD = 0.363
MAX_FAILURES = 3
CHECK_EVERY_N_FRAMES = 15
DISPLAY_WIDTH = 960
DISPLAY_HEIGHT = 540

create_database()

# -------------------- Load face models --------------------
if not os.path.exists(FACE_DETECTOR) or not os.path.exists(FACE_RECOGNIZER):
    raise FileNotFoundError(
        "Face model file(s) not found. Check the ONNX files in the models folder."
    )

detector = cv2.FaceDetectorYN.create(
    FACE_DETECTOR, "", (320, 320), 0.9, 0.3, 5000
)
recognizer = cv2.FaceRecognizerSF.create(FACE_RECOGNIZER, "")

# -------------------- State --------------------
camera = None
monitoring = False
frame_count = 0
failed_attempts = 0
similarity = 0.0
status = "NOT STARTED"
registered_feature = None
lock_alert_shown = False

# -------------------- GUI setup --------------------
root = tk.Tk()
root.title("Continuous Biometric Authenticator")
root.geometry("1350x950")
root.minsize(1000, 750)

try:
    root.state("zoomed")
except tk.TclError:
    pass

root.configure(bg="#f2f4f8")

style = ttk.Style(root)
try:
    style.theme_use("clam")
except tk.TclError:
    pass
style.configure("Treeview", rowheight=28, font=("Arial", 10))
style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

header = tk.Frame(root, bg="#172554", pady=14)
header.pack(fill="x")

tk.Label(
    header, text="CONTINUOUS BIOMETRIC AUTHENTICATOR",
    font=("Arial", 22, "bold"), fg="white", bg="#172554"
).pack()

tk.Label(
    header, text="Facial Biometric Authentication System",
    font=("Arial", 11), fg="#dbeafe", bg="#172554"
).pack(pady=(5, 0))

main = tk.Frame(root, bg="#f2f4f8", padx=18, pady=12)
main.pack(fill="both", expand=True)

camera_frame = tk.Frame(main, bg="#111827", bd=2, relief="groove")
camera_frame.pack(fill="both", expand=True, pady=(0, 12))

camera_label = tk.Label(
    camera_frame, text="Camera Not Started",
    font=("Arial", 18, "bold"), bg="#111827", fg="white",
    anchor="center"
)
camera_label.pack(fill="both", expand=True)

info_frame = tk.Frame(main, bg="#f2f4f8")
info_frame.pack(fill="x", pady=5)

status_value = tk.Label(
    info_frame, text="NOT STARTED", font=("Arial", 12, "bold"),
    fg="#1d4ed8", bg="#f2f4f8"
)
similarity_value = tk.Label(
    info_frame, text="0.000", font=("Arial", 12, "bold"), bg="#f2f4f8"
)
failures_value = tk.Label(
    info_frame, text="0/3", font=("Arial", 12, "bold"), bg="#f2f4f8"
)

for col, (label_text, value_widget) in enumerate([
    ("Status", status_value),
    ("Similarity", similarity_value),
    ("Failed Checks", failures_value),
]):
    tk.Label(
        info_frame, text=f"{label_text}:", font=("Arial", 12, "bold"),
        bg="#f2f4f8"
    ).grid(row=0, column=col * 2, padx=(12, 5), pady=4)
    value_widget.grid(row=0, column=col * 2 + 1, padx=(0, 18), pady=4)

button_frame = tk.Frame(main, bg="#f2f4f8")
button_frame.pack(pady=8)

status_label = tk.Label(
    main, text="System Ready", font=("Arial", 10),
    bg="#f2f4f8", fg="#475569"
)
status_label.pack(pady=(5, 0))

# -------------------- Helper functions --------------------
def load_registered_user(show_status=True):
    global registered_feature

    if not os.path.exists(REGISTERED_FILE):
        registered_feature = None
        if show_status:
            status_label.config(text="No registered user. Click Register User.")
        return False

    try:
        registered_feature = np.load(REGISTERED_FILE)
        if show_status:
            status_label.config(text="Registered face template loaded.")
        return True
    except Exception as error:
        messagebox.showerror("Registration File Error", str(error))
        registered_feature = None
        return False


def release_camera():
    global camera
    if camera is not None:
        camera.release()
        camera = None


def set_status_display():
    status_value.config(text=status)
    similarity_value.config(text=f"{similarity:.3f}")
    failures_value.config(text=f"{failed_attempts}/{MAX_FAILURES}")

    if status == "AUTHENTICATED":
        status_value.config(fg="#15803d")
    elif status in ("UNAUTHORIZED", "SESSION LOCKED"):
        status_value.config(fg="#b91c1c")
    else:
        status_value.config(fg="#b45309")


def register_user():
    global registered_feature

    if monitoring:
        messagebox.showwarning(
            "Monitoring Active", "Stop monitoring before registering again."
        )
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap.release()
        messagebox.showerror("Camera Error", "Cannot open webcam.")
        return

    try:
        messagebox.showinfo(
            "Registration",
            "Look directly at the camera. Click OK to capture your face."
        )
        success, frame = cap.read()
        if not success:
            messagebox.showerror("Camera Error", "Could not capture an image.")
            return

        frame = cv2.flip(frame, 1)
        height, width = frame.shape[:2]
        detector.setInputSize((width, height))
        _, faces = detector.detect(frame)

        if faces is None or len(faces) == 0:
            messagebox.showerror(
                "Registration Failed",
                "No face detected. Improve lighting and try again."
            )
            return

        aligned_face = recognizer.alignCrop(frame, faces[0])
        feature = recognizer.feature(aligned_face)
        os.makedirs(os.path.dirname(REGISTERED_FILE), exist_ok=True)
        np.save(REGISTERED_FILE, feature)
        registered_feature = feature
        status_label.config(text="User registered successfully.")
        messagebox.showinfo("Success", "User registered successfully!")
    except Exception as error:
        messagebox.showerror("Registration Error", str(error))
    finally:
        cap.release()


def start_monitoring():
    global camera, monitoring, frame_count, failed_attempts
    global similarity, status, lock_alert_shown

    if monitoring:
        return
    if not load_registered_user():
        messagebox.showwarning(
            "Registration Required", "Please register a user first."
        )
        return

    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        release_camera()
        messagebox.showerror("Camera Error", "Cannot open webcam.")
        return

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    monitoring = True
    frame_count = 0
    failed_attempts = 0
    similarity = 0.0
    status = "WAITING FOR CHECK"
    lock_alert_shown = False
    set_status_display()
    status_label.config(text="Monitoring Active")
    update_camera()


def draw_camera_frame(frame, faces):
    if status == "AUTHENTICATED":
        color = (0, 190, 70)
    elif status in ("UNAUTHORIZED", "SESSION LOCKED"):
        color = (0, 0, 235)
    else:
        color = (0, 165, 255)

    if faces is not None and len(faces) > 0:
        x, y, w, h = faces[0][:4].astype(int)
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 3)

    cv2.putText(frame, status, (24, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
    cv2.putText(
        frame, f"Similarity: {similarity:.3f}", (24, 78),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
    )
    cv2.putText(
        frame, f"Failed Checks: {failed_attempts}/{MAX_FAILURES}", (24, 112),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
    )

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame_rgb)

    # Use the available camera panel size, keeping the image proportions.
    camera_frame.update_idletasks()
    available_w = max(camera_frame.winfo_width() - 8, DISPLAY_WIDTH)
    available_h = max(camera_frame.winfo_height() - 8, DISPLAY_HEIGHT)
    image.thumbnail((available_w, available_h), Image.Resampling.LANCZOS)

    photo = ImageTk.PhotoImage(image=image)
    camera_label.config(image=photo, text="")
    camera_label.image = photo


def update_camera():
    global frame_count, failed_attempts, similarity, status, monitoring
    global lock_alert_shown

    if not monitoring or camera is None:
        return

    success, frame = camera.read()
    if not success:
        stop_monitoring()
        messagebox.showerror("Camera Error", "Failed to read from webcam.")
        return

    frame = cv2.flip(frame, 1)
    height, width = frame.shape[:2]
    detector.setInputSize((width, height))
    _, faces = detector.detect(frame)
    frame_count += 1

    # Authenticate only at the configured interval.
    if frame_count % CHECK_EVERY_N_FRAMES == 0:
        if faces is not None and len(faces) > 0:
            try:
                aligned_face = recognizer.alignCrop(frame, faces[0])
                current_feature = recognizer.feature(aligned_face)
                similarity = float(recognizer.match(
                    registered_feature,
                    current_feature,
                    cv2.FaceRecognizerSF_FR_COSINE
                ))

                if similarity >= THRESHOLD:
                    status = "AUTHENTICATED"
                    failed_attempts = 0
                    log_authentication("AUTHENTICATED", similarity, failed_attempts)
                else:
                    status = "UNAUTHORIZED"
                    failed_attempts += 1
                    log_authentication("UNAUTHORIZED", similarity, failed_attempts)

            except Exception as error:
                status = "RECOGNITION ERROR"
                status_label.config(text=f"Recognition error: {error}")
        else:
            # Missing face is not counted as an unauthorized identity.
            # Keep the previous failure count; a face must be detected to fail identity matching.
            status = "NO FACE"
            similarity = 0.0
            log_authentication("NO FACE", 0.0, failed_attempts)

    # Lock only after MAX_FAILURES consecutive unauthorized face matches.
    if failed_attempts >= MAX_FAILURES:
        status = "SESSION LOCKED"
        log_authentication("SESSION LOCKED", similarity, failed_attempts)
        draw_camera_frame(frame, faces)
        set_status_display()
        monitoring = False
        release_camera()
        status_label.config(text="Session locked. Click Start Monitoring to restart this demo.")
        if not lock_alert_shown:
            lock_alert_shown = True
            messagebox.showwarning(
                "Security Alert",
                "Three consecutive failed face matches detected. "
                "Monitoring has stopped and the demo session is locked."
            )
        return

    draw_camera_frame(frame, faces)
    set_status_display()
    root.after(15, update_camera)


def stop_monitoring():
    global monitoring
    monitoring = False
    release_camera()
    camera_label.config(image="", text="Camera Not Started")
    camera_label.image = None
    status_label.config(text="Monitoring Stopped")


def view_logs():
    records = show_logs()
    log_window = tk.Toplevel(root)
    log_window.title("Authentication Logs")
    log_window.geometry("950x520")

    columns = ("ID", "Timestamp", "Status", "Similarity", "Failures")
    tree = ttk.Treeview(log_window, columns=columns, show="headings")
    widths = {
        "ID": 60, "Timestamp": 190, "Status": 220,
        "Similarity": 140, "Failures": 110
    }
    for column in columns:
        tree.heading(column, text=column)
        tree.column(column, width=widths[column], anchor="center")

    scrollbar = ttk.Scrollbar(log_window, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
    scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

    for record in records:
        formatted = list(record)
        if formatted[3] is not None:
            formatted[3] = f"{float(formatted[3]):.4f}"
        tree.insert("", "end", values=formatted)


def exit_application():
    global monitoring
    monitoring = False
    release_camera()
    root.destroy()


# -------------------- Buttons --------------------
button_specs = [
    ("Register User", register_user),
    ("Start Monitoring", start_monitoring),
    ("Stop Monitoring", stop_monitoring),
    ("View Logs", view_logs),
    ("Exit", exit_application),
]

for text, command in button_specs:
    tk.Button(
        button_frame,
        text=text,
        command=command,
        font=("Arial", 11, "bold"),
        width=17,
        height=2,
        bg="#e2e8f0",
        activebackground="#cbd5e1",
        cursor="hand2",
    ).pack(side="left", padx=6)

root.protocol("WM_DELETE_WINDOW", exit_application)
load_registered_user(show_status=False)
root.mainloop()

