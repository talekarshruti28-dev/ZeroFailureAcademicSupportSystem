import os

# =====================================================
# MONGODB CONFIGURATION
# =====================================================

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017"
)

DATABASE_NAME = os.getenv(
    "DATABASE_NAME",
    "ZeroFailureDB"
)

# =====================================================
# FLASK CONFIGURATION
# =====================================================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "ZeroFailureAcademicSupportSystemSecretKey2026"
)