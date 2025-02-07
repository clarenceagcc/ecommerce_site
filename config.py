import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///site.db'
    #SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://admin:testtest@db-project.ceaomtz44zvm.us-east-1.rds.amazonaws.com:3306/site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False