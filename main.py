import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os


# ==========================================
# FUNCTIONS
# ==========================================

def register_user():
    try:
        subprocess.run(
            [sys.executable, "register.py"],
            check=False
        )
    except Exception as e:
        messagebox.showerror(
            "Error",
            f"Could not start registration:\n{e}"
        )


def start_authentication():
    try:
        subprocess.run(
            [sys.executable, "continuous_auth.py"],
            check=False
        )
    except Exception as e:
        messagebox.showerror(
            "Error",
            f"Could not start authentication:\n{e}"
        )


def view_logs():
    try:
        subprocess.run(
            [sys.executable, "view_logs.py"],
            check=False
        )
    except Exception as e:
        messagebox.showerror(
            "Error",
            f"Could not open logs:\n{e}"
        )


def exit_application():
    root.destroy()


# ==========================================
# MAIN WINDOW
# ==========================================

root = tk.Tk()

root.title(
    "Continuous Biometric Authenticator"
)

root.geometry(
    "600x500"
)

root.resizable(
    False,
    False
)


# ==========================================
# TITLE
# ==========================================

title = tk.Label(
    root,
    text="CONTINUOUS BIOMETRIC AUTHENTICATOR",
    font=("Arial", 20, "bold")
)

title.pack(
    pady=30
)


# ==========================================
# SUBTITLE
# ==========================================

subtitle = tk.Label(
    root,
    text="Facial Biometric Authentication System",
    font=("Arial", 12)
)

subtitle.pack(
    pady=5
)


# ==========================================
# DESCRIPTION
# ==========================================

description = tk.Label(
    root,
    text=(
        "Continuously verifies the identity of the user\n"
        "and locks the session when an unauthorized user is detected."
    ),
    font=("Arial", 10),
    justify="center"
)

description.pack(
    pady=20
)


# ==========================================
# REGISTER BUTTON
# ==========================================

register_button = tk.Button(
    root,
    text="Register User",
    font=("Arial", 13, "bold"),
    width=25,
    height=2,
    command=register_user
)

register_button.pack(
    pady=10
)


# ==========================================
# AUTHENTICATION BUTTON
# ==========================================

auth_button = tk.Button(
    root,
    text="Start Authentication",
    font=("Arial", 13, "bold"),
    width=25,
    height=2,
    command=start_authentication
)

auth_button.pack(
    pady=10
)


# ==========================================
# LOG BUTTON
# ==========================================

logs_button = tk.Button(
    root,
    text="View Authentication Logs",
    font=("Arial", 13, "bold"),
    width=25,
    height=2,
    command=view_logs
)

logs_button.pack(
    pady=10
)


# ==========================================
# EXIT BUTTON
# ==========================================

exit_button = tk.Button(
    root,
    text="Exit",
    font=("Arial", 13, "bold"),
    width=25,
    height=2,
    command=exit_application
)

exit_button.pack(
    pady=10
)


# ==========================================
# FOOTER
# ==========================================

footer = tk.Label(
    root,
    text="Python • OpenCV • SFace • YuNet • SQLite",
    font=("Arial", 9)
)

footer.pack(
    pady=20
)


# ==========================================
# START GUI
# ==========================================

root.mainloop()