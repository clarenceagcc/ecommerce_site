import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///site.db'
    #SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://admin:TESTTEST@HERE/ecommerce_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False