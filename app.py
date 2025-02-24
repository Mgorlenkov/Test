#app.py
import logging
import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade
from flask.cli import with_appcontext
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.config.from_object('config.Config')

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

# Функция для выполнения миграций
@with_appcontext
def apply_migrations():
    try:
        upgrade()
        logging.info("Migrations applied successfully.")
    except Exception as e:
        logging.error(f"Failed to apply migrations: {e}")

# Функция для проверки подключения к базе данных
def check_database_connection():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        logging.error("DATABASE_URL environment variable is not set.")
        return False
    logging.info(f"DATABASE_URL: {DATABASE_URL}")

    # Проверка формата строки подключения
    if '@' in DATABASE_URL.split(':')[2].split('@')[0]:
        logging.error("Incorrect format of DATABASE_URL. Ensure it does not contain '@' in the host part.")
        return False
    logging.info("DATABASE_URL format is correct.")

    # Проверка подключения с использованием psycopg2
    try:
        import psycopg2
        logging.info("Attempting to connect to the database using psycopg2...")
        conn = psycopg2.connect(DATABASE_URL)
        logging.info("Successfully connected to the database using psycopg2.")
        conn.close()
    except Exception as e:
        logging.error(f"Failed to connect to the database using psycopg2: {e}")
        return False

    # Проверка подключения с использованием SQLAlchemy
    try:
        engine = create_engine(DATABASE_URL)
        conn = engine.connect()
        logging.info("Successfully connected to the database using SQLAlchemy.")
        conn.close()
    except Exception as e:
        logging.error(f"Failed to connect to the database using SQLAlchemy: {e}")
        return False

    # Проверка наличия таблицы Task
    try:
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if 'task' in tables:
            logging.info("Table 'task' exists in the database.")
        else:
            logging.warning("Table 'task' does not exist in the database.")
    except Exception as e:
        logging.error(f"Failed to check table existence using SQLAlchemy: {e}")
        return False

    return True

# Инициализация приложения
@app.before_first_request
def initialize_database():
    if not check_database_connection():
        logging.error("Database connection failed. Exiting...")
        exit(1)
    apply_migrations()

# Главная страница с формой и списком задач
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        task_description = request.form.get('task')
        if task_description:
            new_task = Task(description=task_description)
            db.session.add(new_task)
            try:
                db.session.commit()
            except Exception as e:
                app.logger.error(f"Error committing task: {e}")
                db.session.rollback()
        return redirect(url_for('index'))
    
    try:
        tasks = Task.query.all()
    except Exception as e:
        app.logger.error(f"Error querying tasks: {e}")
        tasks = []
    return render_template('index.html', tasks=tasks)

# Удаление задачи
@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    try:
        task = Task.query.get_or_404(task_id)
        db.session.delete(task)
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Error deleting task: {e}")
        db.session.rollback()
    return redirect(url_for('index'))

# Обновление задачи
@app.route('/update/<int:task_id>', methods=['GET', 'POST'])
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    if request.method == 'POST':
        task.description = request.form.get('task')
        try:
            db.session.commit()
        except Exception as e:
            app.logger.error(f"Error updating task: {e}")
            db.session.rollback()
        return redirect(url_for('index'))
    return render_template('update.html', task=task)

if __name__ == '__main__':
    app.run(debug=True)