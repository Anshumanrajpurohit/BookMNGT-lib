# db_config.py
# PostgreSQL (Supabase) connection using psycopg2


import psycopg2
import psycopg2.extras
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DB_CONFIG = {
    'host': os.environ.get('DB_HOST'),
    'port': int(os.environ.get('DB_PORT')),
    'database': os.environ.get('DB_NAME'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
}

def get_db_connection():
    try:
        return psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            dbname=DB_CONFIG['database'],
            sslmode='require',
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            cursor_factory=psycopg2.extras.DictCursor
        )
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        raise
