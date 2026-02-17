# db_config.py
# MySQL connection using PyMySQL


import pymysql
from pymysql.cursors import DictCursor
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '127.0.0.1'),
    'port': int(os.environ.get('DB_PORT', '3306')),
    'database': os.environ.get('DB_NAME', 'online_book_store'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
}

def get_db_connection():
    try:
        return pymysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            db=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            cursorclass=DictCursor,
            charset='utf8mb4',
            autocommit=False
        )
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        raise
