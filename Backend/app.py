from flask import (
    Flask,
    request,
    jsonify,
    session,
    send_from_directory
)

from flask_cors import CORS


from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from datetime import datetime, timezone
from functools import wraps
import os
import uuid
import re
import requests

from config import SECRET_KEY

from database import (
    db,
    users,
    students,
    teachers,
    parents,
    attendance,
    attendance_sessions,
    marks,
    assignments,
    quizzes,
    quiz_results,
    study_plans,
    notifications,
    initialize_database
)


# =====================================================
# FLASK APP
# =====================================================

app = Flask(__name__)



app.secret_key = SECRET_KEY

CORS(
    app,
    supports_credentials=True,
    origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5000",
        "http://localhost:5000"
    ]
)


# =====================================================
# FRONTEND PATH
# =====================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

FRONTEND_DIR = os.path.join(
    BASE_DIR,
    "Frontend"
)


# =====================================================
# DATABASE
# =====================================================

initialize_database()


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def now():
    return datetime.now(timezone.utc)


def generate_id(prefix):

    return prefix + "-" + uuid.uuid4().hex[:8].upper()


def clean_document(document):

    if document is None:
        return None

    document = dict(document)

    if "_id" in document:
        document["_id"] = str(document["_id"])

    for key, value in document.items():

        if isinstance(value, datetime):
            document[key] = value.isoformat()

    return document


def clean_documents(documents):

    return [
        clean_document(doc)
        for doc in documents
    ]


def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:

            return jsonify({
                "success": False,
                "message": "Please login first"
            }), 401

        return function(*args, **kwargs)

    return wrapper


def role_required(*roles):

    def decorator(function):

        @wraps(function)
        def wrapper(*args, **kwargs):

            if "user_id" not in session:

                return jsonify({
                    "success": False,
                    "message": "Please login first"
                }), 401

            if session.get("role") not in roles:

                return jsonify({
                    "success": False,
                    "message": "Access denied"
                }), 403

            return function(*args, **kwargs)

        return wrapper

    return decorator


def current_user():

    if "user_id" not in session:
        return None

    return users.find_one({
        "userId": session["user_id"]
    })


def get_student(student_id):

    return students.find_one({
        "studentId": student_id
    })


def class_regex(class_name):

    """
    Creates a case-insensitive exact-match regex
    for class names such as SYCS, FYCS, TYCS.
    """

    class_name = str(class_name or "").strip()

    return {
        "$regex": "^" + re.escape(class_name) + "$",
        "$options": "i"
    }


# =====================================================
# FRONTEND ROUTES
# =====================================================

@app.route("/")
def home():

    return send_from_directory(
        FRONTEND_DIR,
        "login.html"
    )


@app.route("/login.html")
def login_page():

    return send_from_directory(
        FRONTEND_DIR,
        "login.html"
    )


@app.route("/register.html")
def register_page():

    return send_from_directory(
        FRONTEND_DIR,
        "register.html"
    )

@app.route("/chatbot.html")
def chatbot_page():
    return send_from_directory(FRONTEND_DIR, "chatbot.html")


@app.route("/<role>/<path:filename>")
def frontend_pages(role, filename):

    if role not in [
        "student",
        "teacher",
        "parent"
    ]:

        return "Page not found", 404

    folder = os.path.join(
        FRONTEND_DIR,
        role
    )

    return send_from_directory(
        folder,
        filename
    )


# =====================================================
# BASIC API
# =====================================================

@app.route("/api")
def api_home():

    return jsonify({
        "success": True,
        "message": "Zero Failure Academic Support System API is running"
    })


@app.route("/api/me")
def api_me():

    user = current_user()

    if not user:

        return jsonify({
            "success": False,
            "loggedIn": False
        })

    return jsonify({
        "success": True,
        "loggedIn": True,
        "user": clean_document(user)
    })


# =====================================================
# REGISTER
# =====================================================

@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json() or {}

    name = str(
        data.get("name", "")
    ).strip()

    email = str(
        data.get("email", "")
    ).strip().lower()

    password = str(
        data.get("password", "")
    ).strip()

    role = str(
        data.get("role", "")
    ).strip().lower()

    if not name or not email or not password or not role:

        return jsonify({
            "success": False,
            "message": "Name, email, password and role are required"
        }), 400

    if role not in [
        "student",
        "teacher",
        "parent"
    ]:

        return jsonify({
            "success": False,
            "message": "Invalid role"
        }), 400

    if len(password) < 6:

        return jsonify({
            "success": False,
            "message": "Password must contain at least 6 characters"
        }), 400

    existing_user = users.find_one({
        "email": email
    })

    if existing_user:

        return jsonify({
            "success": False,
            "message": "Email already registered"
        }), 409

    user_id = generate_id("USR")

    password_hash = generate_password_hash(
        password
    )

    user_document = {

        "userId": user_id,

        "name": name,

        "email": email,

        "password": password_hash,

        "role": role,

        "createdAt": now()
    }

    users.insert_one(
        user_document
    )


    # =================================================
    # STUDENT
    # =================================================

    if role == "student":

        student_id = data.get(
            "studentId"
        ) or generate_id("STU")

        student_document = {

            "studentId": student_id,

            "userId": user_id,

            "name": name,

            "email": email,

            "className": str(
                data.get(
                    "className",
                    ""
                )
            ).strip(),

            "course": str(
                data.get(
                    "course",
                    ""
                )
            ).strip(),

            "semester": str(
                data.get(
                    "semester",
                    ""
                )
            ).strip(),

            "phone": str(
                data.get(
                    "phone",
                    ""
                )
            ).strip(),

            "createdAt": now()
        }

        students.insert_one(
            student_document
        )


    # =================================================
    # TEACHER
    # =================================================

    elif role == "teacher":

        teacher_id = generate_id("TCH")

        teacher_document = {

            "teacherId": teacher_id,

            "userId": user_id,

            "name": name,

            "email": email,

            "subject": str(
                data.get(
                    "subject",
                    ""
                )
            ).strip(),

            "department": str(
                data.get(
                    "department",
                    ""
                )
            ).strip(),

            "createdAt": now()
        }

        teachers.insert_one(
            teacher_document
        )


    # =================================================
    # PARENT
    # =================================================

    elif role == "parent":

        parent_id = generate_id("PAR")

        parent_document = {

            "parentId": parent_id,

            "userId": user_id,

            "name": name,

            "email": email,

            "phone": str(
                data.get(
                    "phone",
                    ""
                )
            ).strip(),

            "childStudentId": str(
                data.get(
                    "childStudentId",
                    ""
                )
            ).strip(),

            "createdAt": now()
        }

        parents.insert_one(
            parent_document
        )


    return jsonify({

        "success": True,

        "message": "Registration successful",

        "userId": user_id,

        "role": role
    })


# =====================================================
# LOGIN
# =====================================================

@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json() or {}

    email = str(
        data.get(
            "email",
            ""
        )
    ).strip().lower()

    password = str(
        data.get(
            "password",
            ""
        )
    )

    if not email or not password:

        return jsonify({
            "success": False,
            "message": "Email and password are required"
        }), 400

    user = users.find_one({
        "email": email
    })

    if not user:

        return jsonify({
            "success": False,
            "message": "Invalid email or password"
        }), 401

    if not check_password_hash(
        user["password"],
        password
    ):

        return jsonify({
            "success": False,
            "message": "Invalid email or password"
        }), 401

    session["user_id"] = user["userId"]
    session["role"] = user["role"]
    session["email"] = user["email"]

    return jsonify({

        "success": True,

        "message": "Login successful",

        "role": user["role"],

        "userId": user["userId"],

        "name": user["name"]
    })


# =====================================================
# LOGOUT
# =====================================================

@app.route("/api/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({

        "success": True,

        "message": "Logged out successfully"
    })


# =====================================================
# STUDENT PROFILE
# =====================================================

@app.route(
    "/api/student/profile",
    methods=["GET"]
)
@role_required("student")
def student_profile():

    student = students.find_one({
        "userId": session["user_id"]
    })

    if not student:

        return jsonify({
            "success": False,
            "message": "Student profile not found"
        }), 404

    return jsonify({
        "success": True,
        "student": clean_document(student)
    })


@app.route(
    "/api/student/profile",
    methods=["PUT"]
)
@role_required("student")
def update_student_profile():

    data = request.get_json() or {}

    allowed_fields = [
        "name",
        "phone",
        "className",
        "course",
        "semester"
    ]

    update_data = {}

    for field in allowed_fields:

        if field in data:

            update_data[field] = data[field]

    if update_data:

        students.update_one(

            {
                "userId": session["user_id"]
            },

            {
                "$set": update_data
            }
        )

        if "name" in update_data:

            users.update_one(

                {
                    "userId":
                        session["user_id"]
                },

                {
                    "$set": {
                        "name":
                            update_data["name"]
                    }
                }
            )

    student = students.find_one({
        "userId": session["user_id"]
    })

    return jsonify({

        "success": True,

        "message": "Profile updated",

        "student":
            clean_document(student)
    })


# =====================================================
# STUDENT ATTENDANCE HISTORY
# =====================================================

@app.route(
    "/api/student/attendance",
    methods=["GET"]
)
@role_required("student")
def student_attendance():

    student = students.find_one({
        "userId": session["user_id"]
    })

    if not student:

        return jsonify({
            "success": False,
            "message": "Student not found"
        }), 404

    records = list(
        attendance.find({
            "studentId":
                student["studentId"]
        }).sort(
            "date",
            -1
        )
    )

    total = len(records)

    present = sum(

        1 for r in records

        if str(
            r.get(
                "status",
                ""
            )
        ).lower()
        == "present"
    )

    percentage = (

        round(
            present /
            total *
            100,
            2
        )

        if total > 0

        else 0
    )

    return jsonify({

        "success": True,

        "total":
            total,

        "present":
            present,

        "absent":
            total - present,

        "percentage":
            percentage,

        "records":
            clean_documents(records)
    })


# =====================================================
# TEACHER - START ATTENDANCE SESSION
# =====================================================

@app.route(
    "/api/teacher/attendance/session/start",
    methods=["POST"]
)
@role_required("teacher")
def start_attendance_session():

    try:

        data = request.get_json() or {}

        subject = str(
            data.get(
                "subject",
                ""
            )
        ).strip()

        class_name = str(
            data.get(
                "className",
                ""
            )
        ).strip()


        # -------------------------------------------------
        # Validate data
        # -------------------------------------------------

        if not subject or not class_name:

            return jsonify({

                "success": False,

                "message":
                    "Subject and class are required"

            }), 400


        # -------------------------------------------------
        # Check if THIS teacher already has active session
        # -------------------------------------------------

        teacher_active = attendance_sessions.find_one({

            "teacherId":
                session["user_id"],

            "active":
                True

        })


        if teacher_active:

            return jsonify({

                "success": False,

                "message":
                    "You already have an active attendance session"

            }), 400


        # -------------------------------------------------
        # Check if class already has active attendance
        # -------------------------------------------------

        class_active = attendance_sessions.find_one({

            "className":
                class_regex(class_name),

            "active":
                True

        })


        if class_active:

            return jsonify({

                "success": False,

                "message":
                    "Attendance is already active for this class"

            }), 400


        # -------------------------------------------------
        # Create attendance session
        # -------------------------------------------------

        session_id = generate_id(
            "SES"
        )

        current_time = now()


        session_document = {

            "sessionId":
                session_id,

            "teacherId":
                session["user_id"],

            "subject":
                subject,

            "className":
                class_name,

            "date":
                current_time,

            "startTime":
                current_time,

            "endTime":
                None,

            "active":
                True
        }


        attendance_sessions.insert_one(
            session_document
        )


        # =================================================
        # CREATE NOTIFICATIONS FOR STUDENTS
        # =================================================

        class_students = list(
            students.find({

                "className":
                    class_regex(class_name)

            })
        )


        notification_records = []


        for student in class_students:

            student_id = student.get(
                "studentId"
            )


            if not student_id:

                continue


            notification_records.append({

                "studentId":
                    student_id,

                "userId":
                    student.get(
                        "userId"
                    ),

                "title":
                    "Attendance Started",

                "message":
                    "Attendance has started for "
                    + subject
                    + " for "
                    + class_name
                    + ". Please mark your attendance.",

                "type":
                    "Attendance",

                "sessionId":
                    session_id,

                "subject":
                    subject,

                "className":
                    class_name,

                "read":
                    False,

                "createdAt":
                    current_time

            })


        # -------------------------------------------------
        # Insert notifications
        # -------------------------------------------------

        if notification_records:

            notifications.insert_many(
                notification_records
            )


        # -------------------------------------------------
        # Response
        # -------------------------------------------------

        return jsonify({

            "success":
                True,

            "message":
                "Attendance session started",

            "sessionId":
                session_id,

            "notificationsSent":
                len(notification_records)

        }), 200


    except Exception as e:

        print(
            "Start Attendance Error:",
            e
        )


        return jsonify({

            "success":
                False,

            "message":
                "Error starting attendance",

            "error":
                str(e)

        }), 500

    # -------------------------------------------------
    # Check if THIS teacher already has an active session
    # -------------------------------------------------

    teacher_active = attendance_sessions.find_one({

        "teacherId":
            session["user_id"],

        "active":
            True

    })

    if teacher_active:

        return jsonify({

            "success": False,

            "message":
                "You already have an active attendance session"
        }), 400


    # -------------------------------------------------
    # Prevent two teachers from starting attendance
    # for the same class at the same time
    # -------------------------------------------------

    class_active = attendance_sessions.find_one({

        "className":
            class_regex(class_name),

        "active":
            True
    })

    if class_active:

        return jsonify({

            "success": False,

            "message":
                "Attendance is already active for this class"
        }), 400


    # -------------------------------------------------
    # Create new session
    # -------------------------------------------------

    session_id = generate_id(
        "SES"
    )

    current_time = now()

    session_document = {

        "sessionId":
            session_id,

        "teacherId":
            session["user_id"],

        "subject":
            subject,

        "className":
            class_name,

        "date":
            current_time,

        "startTime":
            current_time,

        "endTime":
            None,

        "active":
            True
    }

    attendance_sessions.insert_one(
        session_document
    )

    return jsonify({

        "success":
            True,

        "message":
            "Attendance session started",

        "sessionId":
            session_id
    })


# =====================================================
# TEACHER - END ATTENDANCE SESSION
# =====================================================

@app.route(
    "/api/teacher/attendance/session/end",
    methods=["POST"]
)
@role_required("teacher")
def end_attendance_session():

    active = attendance_sessions.find_one({

        "teacherId":
            session["user_id"],

        "active":
            True
    })

    if not active:

        return jsonify({

            "success":
                False,

            "message":
                "No active attendance session"
        }), 404


    # -------------------------------------------------
    # Find students belonging to this class
    # -------------------------------------------------

    class_students = list(
        students.find({

            "className":
                class_regex(
                    active["className"]
                )

        })
    )


    # -------------------------------------------------
    # Find students who already marked attendance
    # -------------------------------------------------

    marked_students = attendance.distinct(

        "studentId",

        {
            "sessionId":
                active["sessionId"]
        }
    )


    # -------------------------------------------------
    # Automatically mark remaining students absent
    # -------------------------------------------------

    absent_records = []

    for student in class_students:

        student_id = student.get(
            "studentId"
        )

        if student_id not in marked_students:

            absent_records.append({

                "sessionId":
                    active["sessionId"],

                "studentId":
                    student_id,

                "studentName":
                    student.get(
                        "name",
                        ""
                    ),

                "teacherId":
                    active["teacherId"],

                "subject":
                    active["subject"],

                "className":
                    active["className"],

                "status":
                    "Absent",

                "date":
                    now()
            })


    if absent_records:

        attendance.insert_many(
            absent_records
        )


    # -------------------------------------------------
    # Close session
    # -------------------------------------------------

    attendance_sessions.update_one(

        {
            "_id":
                active["_id"]
        },

        {
            "$set": {

                "active":
                    False,

                "endTime":
                    now()
            }
        }
    )


    return jsonify({

        "success":
            True,

        "message":
            "Attendance session ended"
    })


# =====================================================
# TEACHER - CURRENT ATTENDANCE SESSION
# =====================================================

@app.route(
    "/api/teacher/attendance/session/current",
    methods=["GET"]
)
@role_required("teacher")
def teacher_current_attendance_session():

    active = attendance_sessions.find_one({

        "teacherId":
            session["user_id"],

        "active":
            True
    })

    if not active:

        return jsonify({

            "success":
                True,

            "active":
                False,

            "session":
                None
        })


    return jsonify({

        "success":
            True,

        "active":
            True,

        "session":
            clean_document(active)
    })


# =====================================================
# TEACHER - CURRENT SESSION ATTENDANCE RECORDS
# =====================================================

@app.route(
    "/api/teacher/attendance/session/records",
    methods=["GET"]
)
@role_required("teacher")
def teacher_attendance_session_records():

    active = attendance_sessions.find_one({

        "teacherId":
            session["user_id"],

        "active":
            True
    })

    if not active:

        return jsonify({

            "success":
                True,

            "records":
                []
        })


    records = list(
        attendance.find({

            "sessionId":
                active["sessionId"]

        }).sort(
            "date",
            1
        )
    )


    return jsonify({

        "success":
            True,

        "records":
            clean_documents(records)
    })


# =====================================================
# STUDENT - CHECK ACTIVE ATTENDANCE
# =====================================================

@app.route(
    "/api/student/attendance/active",
    methods=["GET"]
)
@role_required("student")
def student_active_attendance():

    student = students.find_one({

        "userId":
            session["user_id"]
    })

    if not student:

        return jsonify({

            "success":
                False,

            "message":
                "Student not found"
        }), 404


    student_class = str(
        student.get(
            "className",
            ""
        )
    ).strip()


    if not student_class:

        return jsonify({

            "success":
                True,

            "active":
                False,

            "session":
                None,

            "marked":
                False,

            "message":
                "Your class is not set in your profile"
        })


    # -------------------------------------------------
    # Find active session for student's class
    # -------------------------------------------------

    active = attendance_sessions.find_one({

        "className":
            class_regex(student_class),

        "active":
            True
    })


    if not active:

        return jsonify({

            "success":
                True,

            "active":
                False,

            "session":
                None,

            "marked":
                False
        })


    # -------------------------------------------------
    # Check whether this student already marked
    # -------------------------------------------------

    existing = attendance.find_one({

        "sessionId":
            active["sessionId"],

        "studentId":
            student["studentId"]
    })


    return jsonify({

        "success":
            True,

        "active":
            True,

        "marked":
            existing is not None,

        "status":
            existing.get(
                "status"
            )
            if existing
            else None,

        "session": {

            "sessionId":
                active["sessionId"],

            "subject":
                active["subject"],

            "className":
                active["className"],

            "startTime":
                active["startTime"]
        }
    })


# =====================================================
# STUDENT - MARK OWN ATTENDANCE
# =====================================================

@app.route(
    "/api/student/attendance/mark",
    methods=["POST"]
)
@role_required("student")
def student_mark_attendance():

    student = students.find_one({

        "userId":
            session["user_id"]
    })

    if not student:

        return jsonify({

            "success":
                False,

            "message":
                "Student not found"
        }), 404


    student_class = str(
        student.get(
            "className",
            ""
        )
    ).strip()


    if not student_class:

        return jsonify({

            "success":
                False,

            "message":
                "Your class is not set in your profile"
        }), 400


    # -------------------------------------------------
    # Find active session for student's class
    # -------------------------------------------------

    active = attendance_sessions.find_one({

        "className":
            class_regex(student_class),

        "active":
            True
    })


    if not active:

        return jsonify({

            "success":
                False,

            "message":
                "No active attendance session for your class"
        }), 400


    # -------------------------------------------------
    # Prevent duplicate attendance
    # -------------------------------------------------

    existing = attendance.find_one({

        "sessionId":
            active["sessionId"],

        "studentId":
            student["studentId"]
    })


    if existing:

        return jsonify({

            "success":
                False,

            "message":
                "You have already marked attendance",

            "status":
                existing.get(
                    "status",
                    "Present"
                )
        }), 400


    # -------------------------------------------------
    # Save Present attendance
    # -------------------------------------------------

    attendance_record = {

        "sessionId":
            active["sessionId"],

        "studentId":
            student["studentId"],

        "studentName":
            student.get(
                "name",
                ""
            ),

        "teacherId":
            active["teacherId"],

        "subject":
            active["subject"],

        "className":
            active["className"],

        "status":
            "Present",

        "date":
            now()
    }


    attendance.insert_one(
        attendance_record
    )


    return jsonify({

        "success":
            True,

        "message":
            "Attendance marked successfully",

        "status":
            "Present"
    })


# =====================================================
# TEACHER - MANUAL ATTENDANCE MARKING
# =====================================================

@app.route(
    "/api/teacher/attendance/mark",
    methods=["POST"]
)
@role_required("teacher")
def teacher_manual_mark_attendance():

    data = request.get_json() or {}

    student_id = str(
        data.get(
            "studentId",
            ""
        )
    ).strip()

    status = str(
        data.get(
            "status",
            "Absent"
        )
    ).strip()

    subject = str(
        data.get(
            "subject",
            ""
        )
    ).strip()

    class_name = str(
        data.get(
            "className",
            ""
        )
    ).strip()


    if not student_id:

        return jsonify({

            "success":
                False,

            "message":
                "Student ID is required"
        }), 400


    if status not in [
        "Present",
        "Absent"
    ]:

        return jsonify({

            "success":
                False,

            "message":
                "Status must be Present or Absent"
        }), 400


    student = get_student(
        student_id
    )


    if not student:

        return jsonify({

            "success":
                False,

            "message":
                "Student not found"
        }), 404


    # -------------------------------------------------
    # If an active session exists, use that session
    # -------------------------------------------------

    active = attendance_sessions.find_one({

        "teacherId":
            session["user_id"],

        "active":
            True
    })


    if active:

        session_id = active["sessionId"]

        subject = active["subject"]

        class_name = active["className"]

    else:

        session_id = None


    # -------------------------------------------------
    # Prevent duplicate record for active session
    # -------------------------------------------------

    if session_id:

        existing = attendance.find_one({

            "sessionId":
                session_id,

            "studentId":
                student_id
        })

        if existing:

            attendance.update_one(

                {
                    "_id":
                        existing["_id"]
                },

                {
                    "$set": {

                        "status":
                            status,

                        "date":
                            now()
                    }
                }
            )

            return jsonify({

                "success":
                    True,

                "message":
                    "Attendance updated successfully"
            })


    # -------------------------------------------------
    # Create attendance record
    # -------------------------------------------------

    record = {

        "studentId":
            student_id,

        "studentName":
            student["name"],

        "teacherId":
            session["user_id"],

        "sessionId":
            session_id,

        "subject":
            subject,

        "className":
            class_name,

        "status":
            status,

        "date":
            now()
    }


    attendance.insert_one(
        record
    )


    return jsonify({

        "success":
            True,

        "message":
            "Attendance recorded"
    })


# =====================================================
# STUDENT MARKS
# =====================================================

@app.route(
    "/api/student/marks",
    methods=["GET"]
)
@role_required("student")
def student_marks():

    student = students.find_one({

        "userId":
            session["user_id"]
    })

    if not student:

        return jsonify({

            "success":
                False,

            "message":
                "Student not found"
        }), 404


    records = list(
        marks.find({

            "studentId":
                student["studentId"]

        }).sort(
            "date",
            -1
        )
    )


    return jsonify({

        "success":
            True,

        "records":
            clean_documents(records)
    })


# =====================================================
# TEACHER MARKS
# =====================================================

@app.route(
    "/api/teacher/marks",
    methods=["GET"]
)
@role_required("teacher")
def teacher_marks():

    records = list(
        marks.find({

            "teacherId":
                session["user_id"]

        }).sort(
            "date",
            -1
        )
    )


    return jsonify({

        "success":
            True,

        "records":
            clean_documents(records)
    })


@app.route(
    "/api/teacher/marks",
    methods=["POST"]
)
@role_required("teacher")
def add_marks():

    data = request.get_json() or {}

    student_id = data.get(
        "studentId"
    )

    subject = data.get(
        "subject"
    )

    exam = data.get(
        "exam",
        "Internal"
    )

    try:

        obtained = float(
            data.get(
                "obtained",
                0
            )
        )

        maximum = float(
            data.get(
                "maximum",
                100
            )
        )

    except (TypeError, ValueError):

        return jsonify({

            "success":
                False,

            "message":
                "Marks must be numeric"
        }), 400


    student = get_student(
        student_id
    )


    if not student:

        return jsonify({

            "success":
                False,

            "message":
                "Student not found"
        }), 404


    if maximum <= 0:

        return jsonify({

            "success":
                False,

            "message":
                "Maximum marks must be greater than zero"
        }), 400


    if obtained < 0 or obtained > maximum:

        return jsonify({

            "success":
                False,

            "message":
                "Invalid marks"
        }), 400


    record = {

        "studentId":
            student_id,

        "studentName":
            student["name"],

        "teacherId":
            session["user_id"],

        "subject":
            subject,

        "exam":
            exam,

        "obtained":
            obtained,

        "maximum":
            maximum,

        "percentage":
            round(
                obtained /
                maximum *
                100,
                2
            ),

        "date":
            now()
    }


    marks.insert_one(
        record
    )


    return jsonify({

        "success":
            True,

        "message":
            "Marks saved successfully"
    })


# =====================================================
# STUDENTS FOR TEACHER
# =====================================================

@app.route(
    "/api/teacher/students",
    methods=["GET"]
)
@role_required("teacher")
def teacher_students():

    records = list(
        students.find().sort(
            "name",
            1
        )
    )


    return jsonify({

        "success":
            True,

        "students":
            clean_documents(records)
    })


# =====================================================
# QUIZZES
# =====================================================

@app.route("/api/student/quizzes", methods=["GET"])
@role_required("student")
def get_quizzes():
    records = list(quizzes.find().sort("createdAt", -1))
    return jsonify({
        "success": True,
        "quizzes": clean_documents(records)
    })


@app.route("/api/student/quizzes/result", methods=["POST"])
@role_required("student")
def save_quiz_result():
    student = students.find_one({"userId": session["user_id"]})

    if not student:
        return jsonify({
            "success": False,
            "message": "Student not found"
        }), 404

    data = request.get_json() or {}

    quiz_id = str(data.get("quizId", "")).strip()
    subject = str(data.get("subject", quiz_id)).strip()

    try:
        score = float(data.get("score", 0))
        total = float(data.get("total", 0))
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Score and total must be numeric"
        }), 400

    if total <= 0:
        return jsonify({
            "success": False,
            "message": "Total questions must be greater than zero"
        }), 400

    if score < 0 or score > total:
        return jsonify({
            "success": False,
            "message": "Invalid score"
        }), 400

    percentage = round((score / total) * 100, 2)

    if percentage >= 80:
        performance = "Excellent"
    elif percentage >= 60:
        performance = "Good"
    elif percentage >= 40:
        performance = "Average"
    else:
        performance = "Needs Improvement"

    answers = data.get("answers", [])
    if not isinstance(answers, list):
        answers = []

    result = {
        "quizId": quiz_id,
        "subject": subject,
        "studentId": student.get("studentId", ""),
        "studentName": student.get("name", ""),
        "className": student.get("className", ""),
        "score": score,
        "total": total,
        "percentage": percentage,
        "performance": performance,
        "answers": answers,
        "date": now()
    }

    quiz_results.insert_one(result)

    return jsonify({
        "success": True,
        "message": "Quiz result saved successfully",
        "percentage": percentage
    })


@app.route("/api/teacher/quizzes/results", methods=["GET"])
@role_required("teacher")
def teacher_quiz_results():
    records = list(quiz_results.find().sort("date", -1))
    final_results = []

    for record in records:
        student_id = record.get("studentId", "")
        student = students.find_one({"studentId": student_id})

        student_name = record.get("studentName", "")
        class_name = record.get("className", "")

        if student:
            student_name = student.get("name", student_name)
            class_name = student.get("className", class_name)

        percentage = float(record.get("percentage", 0))

        if percentage >= 80:
            performance = "Excellent"
        elif percentage >= 60:
            performance = "Good"
        elif percentage >= 40:
            performance = "Average"
        else:
            performance = "Needs Improvement"

        final_results.append({
            "studentId": student_id,
            "studentName": student_name,
            "className": class_name,
            "quizId": record.get("quizId", ""),
            "subject": record.get("subject", record.get("quizId", "")),
            "score": record.get("score", 0),
            "total": record.get("total", 0),
            "percentage": percentage,
            "performance": performance,
            "answers": record.get("answers", []),
            "date": record.get("date", "")
        })

    return jsonify({
        "success": True,
        "results": clean_documents(final_results)
    })


@app.route("/api/teacher/quizzes/summary", methods=["GET"])
@role_required("teacher")
def teacher_quiz_summary():
    records = list(quiz_results.find())
    attempts = len(records)
    student_ids = {r.get("studentId") for r in records if r.get("studentId")}
    percentages = [float(r.get("percentage", 0)) for r in records]
    average_score = round(sum(percentages) / len(percentages), 2) if percentages else 0

    return jsonify({
        "success": True,
        "students": len(student_ids),
        "attempts": attempts,
        "averageScore": average_score
    })


@app.route("/api/teacher/quizzes/student/<student_id>", methods=["GET"])
@role_required("teacher")
def teacher_student_quiz_details(student_id):
    records = list(
        quiz_results.find({"studentId": student_id}).sort("date", -1)
    )

    return jsonify({
        "success": True,
        "studentId": student_id,
        "results": clean_documents(records)
    })


# =====================================================
# NOTIFICATIONS
# =====================================================

@app.route(
    "/api/notifications",
    methods=["GET"]
)
@app.route(
    "/api/student/notifications",
    methods=["GET"]
)
@login_required
def get_notifications():

    try:

        # ---------------------------------------------
        # Get logged-in user
        # ---------------------------------------------

        user_id = session["user_id"]

        user = current_user()


        if not user:

            return jsonify({

                "success":
                    False,

                "message":
                    "User not found"

            }), 404


        # ---------------------------------------------
        # Get role
        # ---------------------------------------------

        user_role = user.get(
            "role",
            ""
        )


        # ---------------------------------------------
        # Student ID
        # ---------------------------------------------

        student_id = None


        if user_role == "student":

            student = students.find_one({

                "userId":
                    user_id

            })


            if student:

                student_id = student.get(
                    "studentId"
                )


        # ---------------------------------------------
        # Build notification query
        # ---------------------------------------------

        conditions = []


        # Notification for exact user

        conditions.append({

            "userId":
                user_id

        })


        # Notification for exact student

        if student_id:

            conditions.append({

                "studentId":
                    student_id

            })


        # Notification for user's role

        if user_role:

            conditions.append({

                "role":
                    user_role

            })


        # Notification for everyone

        conditions.append({

            "role":
                "all"

        })


        query = {

            "$or":
                conditions

        }


        # ---------------------------------------------
        # Get notifications
        # ---------------------------------------------

        records = list(

            notifications.find(
                query
            ).sort(
                "createdAt",
                -1
            )

        )


        # ---------------------------------------------
        # Send response
        # ---------------------------------------------

        return jsonify({

            "success":
                True,

            "notifications":
                clean_documents(records)

        }), 200


    except Exception as e:

        print(
            "Notification Error:",
            e
        )


        return jsonify({

            "success":
                False,

            "message":
                "Error loading notifications",

            "error":
                str(e)

        }), 500

# =========================================================
# STUDENT STUDY PLAN
# =========================================================

@app.route("/api/student/study-plan", methods=["GET"])
@role_required("student")
def get_student_study_plan():

    try:

        student = students.find_one({
            "userId": session["user_id"]
        })

        if not student:
            return jsonify({
                "success": False,
                "message": "Student record not found"
            }), 404

        plans = list(
            study_plans.find(
                {
                    "studentId": student["studentId"]
                }
            ).sort(
                "createdAt",
                -1
            )
        )

        return jsonify({
            "success": True,
            "plans": clean_documents(plans)
        }), 200

    except Exception as e:

        print("Study Plan GET Error:", e)

        return jsonify({
            "success": False,
            "message": "Error loading study plans",
            "error": str(e)
        }), 500


@app.route("/api/student/study-plan", methods=["POST"])
@role_required("student")
def create_student_study_plan():

    try:

        student = students.find_one({
            "userId": session["user_id"]
        })

        if not student:
            return jsonify({
                "success": False,
                "message": "Student record not found"
            }), 404


        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "success": False,
                "message": "No data received"
            }), 400


        subject = str(
            data.get("subject", "")
        ).strip()

        study_date = str(
            data.get("date", "")
        ).strip()

        study_time = str(
            data.get("time", "")
        ).strip()

        task = str(
            data.get("task", "")
        ).strip()


        if not subject:

            return jsonify({
                "success": False,
                "message": "Subject is required"
            }), 400


        if not study_date:

            return jsonify({
                "success": False,
                "message": "Study date is required"
            }), 400


        if not study_time:

            return jsonify({
                "success": False,
                "message": "Study time is required"
            }), 400


        if not task:

            return jsonify({
                "success": False,
                "message": "Study task is required"
            }), 400


        plan = {

            "planId": generate_id("PLAN"),

            "studentId":
                student["studentId"],

            "studentName":
                student.get("name", ""),

            "subject":
                subject,

            "date":
                study_date,

            "time":
                study_time,

            "task":
                task,

            "createdAt":
                now()
        }


        result = study_plans.insert_one(plan)


        if not result.inserted_id:

            return jsonify({
                "success": False,
                "message": "Study plan could not be created"
            }), 500


        return jsonify({

            "success": True,

            "message":
                "Study plan created successfully",

            "plan":
                clean_document(plan)

        }), 201


    except Exception as e:

        print("Study Plan POST Error:", e)

        return jsonify({

            "success": False,

            "message":
                "Error creating study plan",

            "error":
                str(e)

        }), 500

# =====================================================
# CREATE STUDY PLAN
# =====================================================

@app.route(
    "/api/student/study-plan",
    methods=["POST"]
)
@role_required("student")
def create_study_plan():

    student = students.find_one({

        "userId":
            session["user_id"]

    })


    if not student:

        return jsonify({

            "success":
                False,

            "message":
                "Student not found"

        }), 404


    data = request.get_json() or {}


    subject = str(
        data.get(
            "subject",
            ""
        )
    ).strip()


    study_date = str(
        data.get(
            "date",
            ""
        )
    ).strip()


    study_time = str(
        data.get(
            "time",
            ""
        )
    ).strip()


    task = str(
        data.get(
            "task",
            ""
        )
    ).strip()


    # -------------------------------------------------
    # VALIDATION
    # -------------------------------------------------

    if not subject:

        return jsonify({

            "success":
                False,

            "message":
                "Subject is required"

        }), 400


    if not study_date:

        return jsonify({

            "success":
                False,

            "message":
                "Study date is required"

        }), 400


    if not study_time:

        return jsonify({

            "success":
                False,

            "message":
                "Study time is required"

        }), 400


    if not task:

        return jsonify({

            "success":
                False,

            "message":
                "Study task is required"

        }), 400


    # -------------------------------------------------
    # CREATE STUDY PLAN DOCUMENT
    # -------------------------------------------------

    plan = {

        "planId":
            generate_id("PLAN"),

        "studentId":
            student["studentId"],

        "studentName":
            student.get(
                "name",
                ""
            ),

        "subject":
            subject,

        "date":
            study_date,

        "time":
            study_time,

        "task":
            task,

        "createdAt":
            now()

    }


    study_plans.insert_one(
        plan
    )


    return jsonify({

        "success":
            True,

        "message":
            "Study plan created successfully",

        "plan":
            clean_document(plan)

    }), 201

# =====================================================
# PREDICTION
# =====================================================

def calculate_student_prediction(student_id):

    attendance_records = list(
        attendance.find({

            "studentId":
                student_id
        })
    )


    mark_records = list(
        marks.find({

            "studentId":
                student_id
        })
    )


    # -------------------------------------------------
    # Attendance
    # -------------------------------------------------

    total_attendance = len(
        attendance_records
    )


    present = sum(

        1 for item
        in attendance_records

        if str(
            item.get(
                "status",
                ""
            )
        ).lower()
        == "present"
    )


    attendance_percentage = (

        present /
        total_attendance *
        100

        if total_attendance

        else 0
    )


    # -------------------------------------------------
    # Marks
    # -------------------------------------------------

    percentages = [

        float(
            item.get(
                "percentage",
                0
            )
        )

        for item
        in mark_records
    ]


    average_marks = (

        sum(percentages) /
        len(percentages)

        if percentages

        else 0
    )


    # -------------------------------------------------
    # Risk
    # -------------------------------------------------

    if (
        attendance_percentage < 60
        or average_marks < 40
    ):

        risk = "High"

    elif (
        attendance_percentage < 75
        or average_marks < 55
    ):

        risk = "Medium"

    else:

        risk = "Low"


    return {

        "studentId":
            student_id,

        "attendance":
            round(
                attendance_percentage,
                2
            ),

        "averageMarks":
            round(
                average_marks,
                2
            ),

        "risk":
            risk
    }


@app.route(
    "/api/student/prediction",
    methods=["GET"]
)
@role_required("student")
def student_prediction():

    student = students.find_one({

        "userId":
            session["user_id"]
    })


    if not student:

        return jsonify({

            "success":
                False,

            "message":
                "Student not found"
        }), 404


    prediction = calculate_student_prediction(

        student["studentId"]

    )


    return jsonify({

        "success":
            True,

        "prediction":
            prediction
    })


@app.route(
    "/api/teacher/predictions",
    methods=["GET"]
)
@role_required("teacher")
def teacher_predictions():

    all_students = list(
        students.find()
    )


    predictions = []


    for student in all_students:

        prediction = calculate_student_prediction(

            student["studentId"]

        )


        prediction["name"] = student["name"]


        predictions.append(
            prediction
        )


    return jsonify({

        "success":
            True,

        "predictions":
            predictions
    })


# =====================================================
# TEACHER REPORTS
# =====================================================

@app.route(
    "/api/teacher/reports",
    methods=["GET"]
)
@role_required("teacher")
def teacher_reports():

    all_students = list(
        students.find()
    )


    report = []


    for student in all_students:

        prediction = calculate_student_prediction(

            student["studentId"]

        )


        report.append({

            "studentId":
                student["studentId"],

            "studentName":
                student["name"],

            "className":
                student.get(
                    "className",
                    ""
                ),

            "attendance":
                prediction["attendance"],

            "averageMarks":
                prediction["averageMarks"],

            "risk":
                prediction["risk"]
        })


    return jsonify({

        "success":
            True,

        "report":
            report
    })


# =====================================================
# PARENT PROFILE / CHILD
# =====================================================

@app.route(
    "/api/parent/child",
    methods=["GET"]
)
@role_required("parent")
def parent_child():

    parent = parents.find_one({

        "userId":
            session["user_id"]
    })


    if not parent:

        return jsonify({

            "success":
                False,

            "message":
                "Parent profile not found"
        }), 404


    child_id = parent.get(

        "childStudentId",

        ""
    )


    if not child_id:

        return jsonify({

            "success":
                True,

            "child":
                None,

            "message":
                "No child has been linked yet"
        })


    child = get_student(
        child_id
    )


    if not child:

        return jsonify({

            "success":
                False,

            "message":
                "Child student not found"
        }), 404


    return jsonify({

        "success":
            True,

        "child":
            clean_document(child)
    })


# =====================================================
# PARENT ATTENDANCE
# =====================================================

@app.route(
    "/api/parent/attendance",
    methods=["GET"]
)
@role_required("parent")
def parent_attendance():

    parent = parents.find_one({

        "userId":
            session["user_id"]
    })


    if not parent:

        return jsonify({

            "success":
                False,

            "message":
                "Parent profile not found"
        }), 404


    child_id = parent.get(

        "childStudentId",

        ""
    )


    records = list(
        attendance.find({

            "studentId":
                child_id

        }).sort(
            "date",
            -1
        )
    )


    total = len(
        records
    )


    present = sum(

        1 for item
        in records

        if str(
            item.get(
                "status",
                ""
            )
        ).lower()
        == "present"
    )


    percentage = (

        present /
        total *
        100

        if total

        else 0
    )


    return jsonify({

        "success":
            True,

        "total":
            total,

        "present":
            present,

        "absent":
            total - present,

        "percentage":
            round(
                percentage,
                2
            ),

        "records":
            clean_documents(records)
    })


# =====================================================
# PARENT PERFORMANCE
# =====================================================

@app.route(
    "/api/parent/performance",
    methods=["GET"]
)
@role_required("parent")
def parent_performance():

    parent = parents.find_one({

        "userId":
            session["user_id"]
    })


    if not parent:

        return jsonify({

            "success":
                False,

            "message":
                "Parent profile not found"
        }), 404


    child_id = parent.get(

        "childStudentId",

        ""
    )


    child = get_student(
        child_id
    )


    if not child:

        return jsonify({

            "success":
                False,

            "message":
                "Child not found"
        }), 404


    mark_records = list(
        marks.find({

            "studentId":
                child_id

        }).sort(
            "date",
            -1
        )
    )


    prediction = calculate_student_prediction(

        child_id

    )


    return jsonify({

        "success":
            True,

        "child":
            clean_document(child),

        "marks":
            clean_documents(mark_records),

        "prediction":
            prediction
    })

# =====================================================
# LOCAL AI CHATBOT - REAL MONGODB ACADEMIC ASSISTANT
# =====================================================

@app.route("/api/chatbot/message", methods=["POST"])
@login_required
def chatbot_message():

    try:
        data = request.get_json() or {}
        message = str(data.get("message", "")).strip()

        if not message:
            return jsonify({
                "success": False,
                "message": "Please enter a message"
            }), 400

        user = current_user()

        if not user:
            return jsonify({
                "success": False,
                "message": "User session not found"
            }), 401

        user_id = session["user_id"]
        role = str(user.get("role", "")).lower().strip()
        academic_context = ""

        # -------------------------------------------------
        # STUDENT CONTEXT
        # -------------------------------------------------
        if role == "student":
            student = students.find_one({"userId": user_id})

            if student:
                student_id = student.get("studentId", "")

                attendance_records = list(
                    attendance.find({"studentId": student_id})
                    .sort("date", -1)
                    .limit(100)
                )
                marks_records = list(
                    marks.find({"studentId": student_id})
                    .sort("date", -1)
                    .limit(100)
                )
                quiz_records = list(
                    quiz_results.find({"studentId": student_id})
                    .sort("date", -1)
                    .limit(100)
                )
                assignment_records = list(
                    assignments.find({"studentId": student_id})
                    .sort("date", -1)
                    .limit(100)
                )
                study_plan_records = list(
                    study_plans.find({"studentId": student_id})
                    .sort("createdAt", -1)
                    .limit(100)
                )
                notification_records = list(
                    notifications.find({
                        "$or": [
                            {"userId": user_id},
                            {"studentId": student_id},
                            {"role": "student"},
                            {"role": "all"}
                        ]
                    }).sort("createdAt", -1).limit(100)
                )

                total = len(attendance_records)
                present = sum(
                    1 for r in attendance_records
                    if str(r.get("status", "")).lower() == "present"
                )
                absent = total - present
                percentage = round((present / total) * 100, 2) if total else 0

                academic_context = f"""
REAL MONGODB DATA - STUDENT
Student Name: {student.get('name', '')}
Student ID: {student_id}
Class: {student.get('className', '')}
Course: {student.get('course', '')}
Semester: {student.get('semester', '')}

ATTENDANCE SUMMARY
Total records: {total}
Present: {present}
Absent: {absent}
Attendance percentage: {percentage}%

ATTENDANCE RECORDS:
{clean_documents(attendance_records)}

MARKS:
{clean_documents(marks_records)}

QUIZ RESULTS:
{clean_documents(quiz_records)}

ASSIGNMENTS:
{clean_documents(assignment_records)}

STUDY PLANS:
{clean_documents(study_plan_records)}

NOTIFICATIONS:
{clean_documents(notification_records)}
"""
            else:
                academic_context = "No student profile was found for the logged-in student. Do not invent student data."

        # -------------------------------------------------
        # TEACHER CONTEXT
        # -------------------------------------------------
        elif role == "teacher":
            teacher = teachers.find_one({"userId": user_id})
            student_records = list(students.find().sort("name", 1).limit(100))
            attendance_records = list(attendance.find().sort("date", -1).limit(100))
            marks_records = list(marks.find().sort("date", -1).limit(100))
            quiz_result_records = list(quiz_results.find().sort("date", -1).limit(100))
            quiz_records = list(quizzes.find().sort("createdAt", -1).limit(100))
            assignment_records = list(assignments.find().sort("date", -1).limit(100))
            study_plan_records = list(study_plans.find().sort("createdAt", -1).limit(100))
            notification_records = list(notifications.find().sort("createdAt", -1).limit(100))

            academic_context = f"""
REAL MONGODB DATA - TEACHER
Teacher Name: {teacher.get('name', '') if teacher else ''}
Teacher ID: {teacher.get('teacherId', '') if teacher else ''}
Subject: {teacher.get('subject', '') if teacher else ''}
Department: {teacher.get('department', '') if teacher else ''}

TOTAL DATABASE COUNTS
Students: {students.count_documents({})}
Attendance records: {attendance.count_documents({})}
Marks records: {marks.count_documents({})}
Quiz results: {quiz_results.count_documents({})}
Quizzes: {quizzes.count_documents({})}
Assignments: {assignments.count_documents({})}
Study plans: {study_plans.count_documents({})}
Notifications: {notifications.count_documents({})}

STUDENTS:
{clean_documents(student_records)}

ATTENDANCE:
{clean_documents(attendance_records)}

MARKS:
{clean_documents(marks_records)}

QUIZ RESULTS:
{clean_documents(quiz_result_records)}

QUIZZES:
{clean_documents(quiz_records)}

ASSIGNMENTS:
{clean_documents(assignment_records)}

STUDY PLANS:
{clean_documents(study_plan_records)}

NOTIFICATIONS:
{clean_documents(notification_records)}
"""

        # -------------------------------------------------
        # PARENT CONTEXT
        # -------------------------------------------------
        elif role == "parent":
            parent = parents.find_one({"userId": user_id})

            if parent:
                child_id = str(parent.get("childStudentId", "")).strip()
                child = students.find_one({"studentId": child_id}) if child_id else None

                if child:
                    attendance_records = list(
                        attendance.find({"studentId": child_id}).sort("date", -1).limit(100)
                    )
                    marks_records = list(
                        marks.find({"studentId": child_id}).sort("date", -1).limit(100)
                    )
                    quiz_records = list(
                        quiz_results.find({"studentId": child_id}).sort("date", -1).limit(100)
                    )
                    assignment_records = list(
                        assignments.find({"studentId": child_id}).sort("date", -1).limit(100)
                    )
                    study_plan_records = list(
                        study_plans.find({"studentId": child_id}).sort("createdAt", -1).limit(100)
                    )
                    notification_records = list(
                        notifications.find({
                            "$or": [
                                {"userId": user_id},
                                {"role": "parent"},
                                {"role": "all"}
                            ]
                        }).sort("createdAt", -1).limit(100)
                    )

                    total = len(attendance_records)
                    present = sum(
                        1 for r in attendance_records
                        if str(r.get("status", "")).lower() == "present"
                    )
                    absent = total - present
                    percentage = round((present / total) * 100, 2) if total else 0

                    academic_context = f"""
REAL MONGODB DATA - PARENT
Parent Name: {parent.get('name', '')}
Parent ID: {parent.get('parentId', '')}

CHILD INFORMATION
Child Name: {child.get('name', '')}
Child Student ID: {child_id}
Class: {child.get('className', '')}

CHILD ATTENDANCE SUMMARY
Total records: {total}
Present: {present}
Absent: {absent}
Attendance percentage: {percentage}%

CHILD ATTENDANCE:
{clean_documents(attendance_records)}

CHILD MARKS:
{clean_documents(marks_records)}

CHILD QUIZ RESULTS:
{clean_documents(quiz_records)}

CHILD ASSIGNMENTS:
{clean_documents(assignment_records)}

CHILD STUDY PLANS:
{clean_documents(study_plan_records)}

PARENT NOTIFICATIONS:
{clean_documents(notification_records)}
"""
                else:
                    academic_context = f"""
REAL MONGODB DATA - PARENT
Parent Name: {parent.get('name', '')}
Parent ID: {parent.get('parentId', '')}
Child Student ID stored in parent record: {child_id}
No matching child student record was found.
Do not invent child information.
"""
            else:
                academic_context = "No parent profile was found. Do not invent parent or child information."

        else:
            academic_context = f"The logged-in user's role is {role}. No role-specific academic data is available."

        # -------------------------------------------------
        # AI SYSTEM PROMPT
        # -------------------------------------------------
        system_prompt = f"""
You are the AI Academic Assistant for the Zero-Failure Academic Support System.

Current user role: {role}

Use the REAL MONGODB DATA supplied below for questions about system records.
Never invent students, names, IDs, marks, attendance, quiz results, quizzes,
assignments, study plans, notifications, or database counts.
If requested information is not present, say that it is not available.
Do not reveal passwords, session secrets, or authentication information.
Students may receive information about their own records.
Parents may receive information only about their associated child.
Teachers may receive the academic information supplied in their context.
For general academic questions, answer normally and clearly.

When several records or fields are requested, use a Markdown table with clear
column headings. Do not put Markdown tables inside code blocks.
For a simple one-value question, give a short direct answer.

DATABASE CONTEXT:
{academic_context}
"""

        payload = {
            "model": "llama3.2",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            "stream": False
        }

        response = requests.post(
            "http://127.0.0.1:11434/api/chat",
            json=payload,
            timeout=120
        )
        response.raise_for_status()

        result = response.json()
        answer = result.get("message", {}).get("content", "").strip()

        return jsonify({
            "success": True,
            "reply": answer
        }), 200

    except requests.exceptions.RequestException as e:
        print("Ollama Error:", e)
        return jsonify({
            "success": False,
            "message": "Ollama is not available. Please make sure Ollama is running."
        }), 503

    except Exception as e:
        print("Chatbot Error:", e)
        return jsonify({
            "success": False,
            "message": "Unable to get a chatbot response",
            "error": str(e)
        }), 500


# =====================================================
# SERVER
# =====================================================

if __name__ == "__main__":

    app.run(

        host="127.0.0.1",

        port=5000,

        debug=True
    )