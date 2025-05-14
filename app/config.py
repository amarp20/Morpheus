import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Pilla de .env en producción si lo deseas
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/Morpheus')
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    ALLOWED_EXTENSIONS = {"xls", "xlsx", "csv"}