#app.py
import logging
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Инициализация Flask приложения
app = Flask(__name__)
app.config.from_object('config.Config')
app.secret_key = os.environ.get('SECRET_KEY') or 'your_secret_key'

# Инициализация SQLAlchemy
db = SQLAlchemy(app)

# Инициализация Flask-Migrate
migrate = Migrate(app, db)

# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Инициализация Flask-Bcrypt
bcrypt = Bcrypt(app)

# Модель User
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), default='user', nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

# Модель Task
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('tasks', lazy=True))

    def __repr__(self):
        return f'<Task {self.description}>'

# Функция для загрузки пользователя по ID
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Функция для выполнения миграций
def apply_migrations():
    with app.app_context():
        try:
            upgrade()
            logging.info("Migrations applied successfully.")
        except Exception as e:
            logging.error(f"Failed to apply migrations: {e}")
            exit(1)

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
def initialize_database():
    if not check_database_connection():
        logging.error("Database connection failed. Exiting...")
        exit(1)
    apply_migrations()

# Вызов инициализации базы данных при создании приложения
initialize_database()

# Главная страница с формой и списком задач
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        task_description = request.form.get('task')
        if task_description:
            new_task = Task(description=task_description, user=current_user)
            db.session.add(new_task)
            try:
                db.session.commit()
            except Exception as e:
                app.logger.error(f"Error committing task: {e}")
                db.session.rollback()
        return redirect(url_for('index'))
    
    filter_completed = request.args.get('completed', type=bool)
    if filter_completed is None:
        tasks = current_user.tasks
    elif filter_completed:
        tasks = current_user.tasks.filter_by(completed=True).all()
    else:
        tasks = current_user.tasks.filter_by(completed=False).all()

    return render_template('index.html', tasks=tasks, filter_completed=filter_completed)

# Удаление задачи
@app.route('/delete/<int:task_id>')
@login_required
def delete_task(task_id):
    try:
        task = Task.query.get_or_404(task_id)
        if task.user != current_user:
            flash('Вы можете удалять только свои задачи.', 'danger')
            return redirect(url_for('index'))
        db.session.delete(task)
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Error deleting task: {e}")
        db.session.rollback()
    return redirect(url_for('index'))

# Обновление задачи
@app.route('/update/<int:task_id>', methods=['GET', 'POST'])
@login_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user != current_user:
        flash('Вы можете обновлять только свои задачи.', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        task.description = request.form.get('task')
        task.completed = 'completed' in request.form
        try:
            db.session.commit()
        except Exception as e:
            app.logger.error(f"Error updating task: {e}")
            db.session.rollback()
        return redirect(url_for('index'))
    return render_template('update.html', task=task)

# Фильтрация задач по статусу
@app.route('/filter', methods=['POST'])
@login_required
def filter_tasks():
    completed = 'completed' in request.form
    return redirect(url_for('index', completed=completed))

# Регистрация пользователя
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Пожалуйста, заполните все поля.', 'danger')
            return redirect(url_for('register'))
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Пользователь с таким именем уже существует.', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        try:
            db.session.commit()
            flash('Регистрация успешна!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            app.logger.error(f"Error registering user: {e}")
            db.session.rollback()
            flash('Произошла ошибка при регистрации.', 'danger')
    
    return render_template('register.html')

# Вход пользователя
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Пожалуйста, заполните все поля.', 'danger')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Вход успешен!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль.', 'danger')
    
    return render_template('login.html')

# Выход пользователя
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('login'))

# Страница администратора
@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        flash('Доступ запрещен.', 'danger')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('admin.html', users=users)

if __name__ == '__main__':
    app.run(debug=True)