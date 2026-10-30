import os
import functools
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

from config import (
    SECRET_KEY,
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE,
    THRESHOLD,
    MAX_FAILURES,
    REGISTERED_FILE
)
from database import (
    create_database,
    log_authentication,
    show_logs,
    get_logs_extended,
    add_user,
    get_user_by_username,
    get_user_by_id,
    get_all_users,
    get_security_metrics
)
from face_utils import biometric_engine

# Initialize Flask App
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = SESSION_COOKIE_HTTPONLY
app.config["SESSION_COOKIE_SAMESITE"] = SESSION_COOKIE_SAMESITE

# Initialize database tables on startup
create_database()


def login_required(view):
    """Decorator to protect routes requiring biometric authentication."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if "user" not in session:
            return redirect(url_for("login_page", next=request.path))
        if session.get("is_locked", False):
            return redirect(url_for("lock_screen"))
        return view(**kwargs)
    return wrapped_view


# ==========================================
# PAGE ROUTES
# ==========================================

@app.route("/")
def index():
    """Modern cybersecurity landing page with project presentation."""
    metrics = get_security_metrics()
    users = get_all_users()
    is_authenticated = "user" in session and not session.get("is_locked", False)
    return render_template(
        "index.html",
        metrics=metrics,
        users=users,
        threshold=THRESHOLD,
        max_failures=MAX_FAILURES,
        is_authenticated=is_authenticated,
        current_user=session.get("user")
    )


@app.route("/register")
def register_page():
    """User registration page with live webcam biometric enrollment."""
    return render_template("register.html")


@app.route("/login")
def login_page():
    """Biometric authentication page with 1:N face identification or 1:1 match."""
    if "user" in session and not session.get("is_locked", False):
        return redirect(url_for("dashboard_page"))
    users = get_all_users()
    return render_template("login.html", users=users, threshold=THRESHOLD)


@app.route("/dashboard")
@login_required
def dashboard_page():
    """Secure dashboard with real-time continuous biometric monitoring Sentinel."""
    user = session["user"]
    metrics = get_security_metrics()
    recent_logs = get_logs_extended(limit=10)
    return render_template(
        "dashboard.html",
        user=user,
        metrics=metrics,
        recent_logs=recent_logs,
        threshold=THRESHOLD,
        max_failures=MAX_FAILURES
    )


@app.route("/logs")
def logs_page():
    """Detailed security audit logs page."""
    logs = get_logs_extended(limit=200)
    metrics = get_security_metrics()
    return render_template("logs.html", logs=logs, metrics=metrics)


@app.route("/lock-screen")
def lock_screen():
    """Security breach lockout screen displayed when continuous authentication fails."""
    lock_info = {
        "timestamp": session.get("locked_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "reason": session.get("lock_reason", f"{MAX_FAILURES} consecutive failed biometric checks"),
        "user": session.get("last_user", "Unknown Session")
    }
    # Clear the session state on lockout view
    session.pop("user", None)
    session["is_locked"] = True
    return render_template("lock.html", lock_info=lock_info)


@app.route("/logout")
def logout():
    """Secure logout endpoint."""
    user = session.get("user")
    if user:
        log_authentication("LOGOUT", 1.0, 0, username=user.get("username", "System"))
    session.clear()
    return redirect(url_for("login_page"))


# ==========================================
# BIOMETRIC REST API ENDPOINTS
# ==========================================

@app.route("/api/system-status", methods=["GET"])
def api_system_status():
    """Returns biometric system telemetry and health metrics."""
    metrics = get_security_metrics()
    return jsonify({
        "success": True,
        "detector": "YuNet (ONNX)",
        "recognizer": "SFace (ONNX)",
        "threshold": THRESHOLD,
        "max_failures": MAX_FAILURES,
        "metrics": metrics
    })


@app.route("/api/users", methods=["GET"])
def api_get_users():
    """Returns registered users list without exposing embeddings."""
    users = get_all_users()
    safe_users = [{
        "id": u["id"],
        "username": u["username"],
        "full_name": u["full_name"],
        "role": u.get("role", "Authorized User"),
        "created_at": u["created_at"]
    } for u in users]
    return jsonify({"success": True, "users": safe_users})


@app.route("/api/register", methods=["POST"])
def api_register():
    """
    Registers a new user biometrically.
    Accepts: {username, full_name, email, role, image}
    """
    data = request.get_json()
    if not data or "image" not in data or "username" not in data:
        return jsonify({"success": False, "message": "Invalid request payload"}), 400

    username = data["username"].strip().lower()
    full_name = data.get("full_name", "").strip() or username.capitalize()
    email = data.get("email", "").strip()
    role = data.get("role", "Authorized User")
    image_b64 = data["image"]

    if not username:
        return jsonify({"success": False, "message": "Username is required"}), 400

    # Check if username exists
    existing = get_user_by_username(username)
    if existing:
        return jsonify({"success": False, "message": f"Username '{username}' is already registered."}), 409

    # Decode frame
    frame = biometric_engine.decode_base64_image(image_b64)
    if frame is None:
        return jsonify({"success": False, "message": "Failed to decode camera frame"}), 400

    # Process frame with YuNet and SFace
    valid, message, feature, box = biometric_engine.process_frame_for_registration(frame)
    if not valid:
        return jsonify({"success": False, "message": message, "box": box}), 422

    # Save feature vector to secure disk location
    feature_path = biometric_engine.save_user_feature(username, feature)

    # Insert user in database
    ok, result = add_user(username, full_name, email, feature_path, role)
    if not ok:
        return jsonify({"success": False, "message": f"Database error: {result}"}), 500

    # Log successful registration
    log_authentication("USER REGISTERED", 1.0, 0, username=username)

    return jsonify({
        "success": True,
        "message": f"User '{full_name}' successfully registered!",
        "user": {
            "id": result,
            "username": username,
            "full_name": full_name,
            "role": role
        },
        "box": box
    })


@app.route("/api/authenticate", methods=["POST"])
def api_authenticate():
    """
    Authenticates a user via webcam frame.
    Can perform 1:1 verification if username provided, or 1:N across all users.
    """
    data = request.get_json()
    if not data or "image" not in data:
        return jsonify({"success": False, "message": "Missing webcam image data"}), 400

    image_b64 = data["image"]
    target_username = data.get("username", "").strip()

    frame = biometric_engine.decode_base64_image(image_b64)
    if frame is None:
        return jsonify({"success": False, "message": "Could not decode camera frame"}), 400

    users = get_all_users()

    # Fallback to single legacy registered template if no users in DB table yet
    if not users and os.path.exists(REGISTERED_FILE):
        users = [{
            "id": 1,
            "username": "registered_user",
            "full_name": "Registered User",
            "role": "Authorized User",
            "feature_path": REGISTERED_FILE,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }]

    if not users:
        return jsonify({
            "success": False,
            "message": "No registered users found. Please register first."
        }), 404

    # Perform verification
    if target_username:
        user = get_user_by_username(target_username)
        if not user:
            return jsonify({"success": False, "message": "Specified user not found"}), 404

        target_feature = biometric_engine.load_user_feature(user["feature_path"])
        if target_feature is None:
            return jsonify({"success": False, "message": "Biometric template missing on server"}), 500

        result = biometric_engine.verify_against_target(frame, target_feature)
        is_authenticated = (result["status"] == "AUTHENTICATED")

        # Log attempt
        log_authentication(
            result["status"],
            result["similarity"],
            0 if is_authenticated else 1,
            username=user["username"]
        )

        if is_authenticated:
            session.clear()
            session["user"] = {
                "id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user.get("role", "Authorized User"),
                "feature_path": user["feature_path"]
            }
            session["failed_attempts"] = 0
            session["is_locked"] = False
            session["login_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            return jsonify({
                "success": True,
                "status": "AUTHENTICATED",
                "similarity": result["similarity"],
                "box": result["box"],
                "user": session["user"],
                "redirect_url": url_for("dashboard_page")
            })
        else:
            return jsonify({
                "success": False,
                "status": result["status"],
                "similarity": result["similarity"],
                "box": result["box"],
                "message": result["message"]
            })

    else:
        # 1:N Identification
        result = biometric_engine.identify_among_users(frame, users)
        is_authenticated = (result["status"] == "AUTHENTICATED")

        matched_name = result["matched_user"]["username"] if result.get("matched_user") else "Unknown"
        log_authentication(
            result["status"],
            result["similarity"],
            0 if is_authenticated else 1,
            username=matched_name
        )

        if is_authenticated and result.get("matched_user"):
            matched_user = result["matched_user"]
            db_user = get_user_by_id(matched_user["id"])
            session.clear()
            session["user"] = {
                "id": db_user["id"],
                "username": db_user["username"],
                "full_name": db_user["full_name"],
                "role": db_user.get("role", "Authorized User"),
                "feature_path": db_user["feature_path"]
            }
            session["failed_attempts"] = 0
            session["is_locked"] = False
            session["login_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            return jsonify({
                "success": True,
                "status": "AUTHENTICATED",
                "similarity": result["similarity"],
                "box": result["box"],
                "user": session["user"],
                "redirect_url": url_for("dashboard_page")
            })
        else:
            return jsonify({
                "success": False,
                "status": result["status"],
                "similarity": result["similarity"],
                "box": result["box"],
                "message": result["message"]
            })


@app.route("/api/continuous-check", methods=["POST"])
def api_continuous_check():
    """
    Heartbeat endpoint for continuous biometric authentication Sentinel.
    Runs verification on incoming frame against currently logged-in user's template.
    If 3 consecutive unauthorized/no-face checks occur, locks session immediately.
    """
    if "user" not in session:
        return jsonify({
            "authenticated": False,
            "locked": True,
            "message": "No active session found",
            "redirect_url": url_for("login_page")
        }), 401

    if session.get("is_locked", False):
        return jsonify({
            "authenticated": False,
            "locked": True,
            "message": "Session is already locked",
            "redirect_url": url_for("lock_screen")
        })

    data = request.get_json()
    if not data or "image" not in data:
        return jsonify({"success": False, "message": "Missing image frame"}), 400

    user = session["user"]
    feature_path = user.get("feature_path")

    target_feature = biometric_engine.load_user_feature(feature_path)
    if target_feature is None:
        return jsonify({"success": False, "message": "User biometric template missing"}), 500

    frame = biometric_engine.decode_base64_image(data["image"])
    if frame is None:
        return jsonify({"success": False, "message": "Could not decode camera frame"}), 400

    # Verify against active user template
    result = biometric_engine.verify_against_target(frame, target_feature)
    status = result["status"]
    similarity = result["similarity"]
    box = result["box"]

    failed_attempts = session.get("failed_attempts", 0)

    if status == "AUTHENTICATED":
        failed_attempts = 0
        session["failed_attempts"] = 0
        log_authentication("AUTHENTICATED", similarity, 0, username=user["username"])
        is_locked = False

    elif status == "UNAUTHORIZED":
        failed_attempts += 1
        session["failed_attempts"] = failed_attempts
        log_authentication("UNAUTHORIZED", similarity, failed_attempts, username=user["username"])

    elif status == "NO FACE":
        failed_attempts += 1
        session["failed_attempts"] = failed_attempts
        log_authentication("NO FACE", 0.0, failed_attempts, username=user["username"])

    else:
        # Unexpected error
        failed_attempts += 1
        session["failed_attempts"] = failed_attempts

    # Check if threshold reached
    if failed_attempts >= MAX_FAILURES:
        status = "SESSION LOCKED"
        session["is_locked"] = True
        session["locked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        session["last_user"] = user.get("full_name", user.get("username"))
        session["lock_reason"] = f"Detected {MAX_FAILURES} consecutive unauthorized or absent biometric events"

        log_authentication("SESSION LOCKED", similarity, failed_attempts, username=user["username"])

        return jsonify({
            "authenticated": False,
            "locked": True,
            "status": "SESSION LOCKED",
            "similarity": similarity,
            "failed_attempts": failed_attempts,
            "max_failures": MAX_FAILURES,
            "box": box,
            "message": "SECURITY BREACH: Unauthorized identity or absence detected. Session locked.",
            "redirect_url": url_for("lock_screen")
        })

    return jsonify({
        "authenticated": (status == "AUTHENTICATED"),
        "locked": False,
        "status": status,
        "similarity": similarity,
        "failed_attempts": failed_attempts,
        "max_failures": MAX_FAILURES,
        "box": box,
        "message": result["message"]
    })


@app.route("/api/test-lock", methods=["POST"])
@login_required
def api_test_lock():
    """Manual trigger to test security breach lock screen."""
    user = session.get("user", {})
    session["is_locked"] = True
    session["locked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    session["last_user"] = user.get("full_name", "Test User")
    session["lock_reason"] = "Manual security lock test triggered by user"
    log_authentication("SESSION LOCKED", 0.0, MAX_FAILURES, username=user.get("username", "Test"))

    return jsonify({
        "success": True,
        "locked": True,
        "redirect_url": url_for("lock_screen")
    })


@app.route("/api/logs", methods=["GET"])
def api_get_logs():
    """Returns recent logs as JSON for real-time frontend table updates."""
    limit = request.args.get("limit", 50, type=int)
    logs = get_logs_extended(limit=limit)
    return jsonify({"success": True, "logs": logs})


if __name__ == "__main__":
    print("=" * 60)
    print(" CONTINUOUS BIOMETRIC AUTHENTICATOR - FLASK SERVER")
    print(" Server running on http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True)
