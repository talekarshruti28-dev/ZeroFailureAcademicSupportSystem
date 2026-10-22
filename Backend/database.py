from pymongo import MongoClient
from pymongo.errors import PyMongoError

from config import MONGO_URI, DATABASE_NAME


# =====================================================
# MONGODB CONNECTION
# =====================================================

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)

db = client[DATABASE_NAME]


# =====================================================
# COLLECTIONS
# =====================================================

users = db["Users"]
students = db["Students"]
teachers = db["Teachers"]
parents = db["Parents"]

attendance = db["Attendance"]
attendance_sessions = db["AttendanceSessions"]

marks = db["Marks"]
assignments = db["Assignments"]

quizzes = db["Quizzes"]
quiz_results = db["QuizResults"]

study_plans = db["StudyPlans"]
notifications = db["Notifications"]


# =====================================================
# DATABASE INITIALIZATION
# =====================================================

def initialize_database():

    try:

        # Test connection
        client.admin.command("ping")

        # Unique email
        users.create_index(
            "email",
            unique=True
        )

        students.create_index(
            "studentId",
            unique=True
        )

        teachers.create_index(
            "teacherId",
            unique=True
        )

        print("==========================================")
        print("MongoDB connected successfully")
        print("Database:", DATABASE_NAME)
        print("==========================================")

    except PyMongoError as e:

        print("MongoDB connection error:")
        print(e)