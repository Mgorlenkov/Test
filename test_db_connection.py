import os
import logging
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Инициализация Flask приложения для тестирования
from flask import Flask
app = Flask(__name__)
app.config.from_object(Config)

# Инициализация SQLAlchemy
db = SQLAlchemy(app)

# Инициализация Flask-Migrate
migrate = Migrate(app, db)

# Определение модели Task
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<Task {self.description}>'

# Получение строки подключения из переменной окружения
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logging.error("DATABASE_URL environment variable is not set.")
else:
    logging.info(f"DATABASE_URL: {DATABASE_URL}")

# Проверка формата строки подключения
if '@' in DATABASE_URL.split(':')[2]:
    logging.error("Incorrect format of DATABASE_URL. Ensure it does not contain '@' in the host part.")
else:
    logging.info("DATABASE_URL format is correct.")

# Проверка подключения с использованием psycopg2
try:
    conn = psycopg2.connect(DATABASE_URL)
    logging.info("Successfully connected to the database using psycopg2.")
    conn.close()
except psycopg2.OperationalError as e:
    logging.error(f"Failed to connect to the database using psycopg2: {e}")

# Проверка подключения с использованием SQLAlchemy
try:
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    logging.info("Successfully connected to the database using SQLAlchemy.")
    conn.close()
except OperationalError as e:
    logging.error(f"Failed to connect to the database using SQLAlchemy: {e}")

# Проверка наличия таблицы Task
try:
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if 'task' in tables:
        logging.info("Table 'task' exists in the database.")
    else:
        logging.warning("Table 'task' does not exist in the database.")
except OperationalError as e:
    logging.error(f"Failed to check table existence using SQLAlchemy: {e}")

# Проверка возможности выполнения запроса к таблице Task
try:
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    result = conn.execute("SELECT * FROM task;")
    rows = result.fetchall()
    logging.info(f"Successfully queried the 'task' table. Rows: {rows}")
    conn.close()
except OperationalError as e:
    logging.error(f"Failed to query the 'task' table using SQLAlchemy: {e}")
except Exception as e:
    logging.error(f"An unexpected error occurred while querying the 'task' table: {e}")