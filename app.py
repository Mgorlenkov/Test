# app.py
from flask import Flask, request, redirect, url_for, render_template, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import os
import unittest
from urllib.parse import parse_qs, urlencode

# Инициализация приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация базы данных
db = SQLAlchemy(app)

# Инициализация миграций
migrate = Migrate(app, db)

# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Инициализация Flask-Bcrypt
bcrypt = Bcrypt(app)

# Модель User
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), nullable=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Модель Task
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(250), nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Task {self.description}>'

# Маршрут для корневого URL
@app.route('/')
def index():
    tasks = Task.query.all()
    return render_template('index.html', tasks=tasks)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.')
            return redirect(url_for('register'))

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful.')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/filter_tasks', methods=['POST'])
@login_required
def filter_tasks():
    status = request.form.get('status')
    if status == 'completed':
        tasks = Task.query.filter_by(completed=True).all()
    elif status == 'not_completed':
        tasks = Task.query.filter_by(completed=False).all()
    else:
        tasks = Task.query.all()
    return render_template('index.html', tasks=tasks)

# Тесты
class FlaskAppTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_index_route(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Список задач', response.get_data(as_text=True))

    def test_register_route(self):
        response = self.app.get('/register')
        self.assertEqual(response.status_code, 200)

    def test_login_route(self):
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)

    def test_logout_route(self):
        response = self.app.get('/logout')
        self.assertEqual(response.status_code, 302)  # Должен быть редирект на логин

    def test_filter_tasks_route(self):
        # Регистрация пользователя
        self.app.post('/register', data={'username': 'testuser', 'password': 'testpass'})
        # Вход пользователя
        self.app.post('/login', data={'username': 'testuser', 'password': 'testpass'})
        # Фильтрация задач
        response = self.app.post('/filter_tasks', data={'status': 'completed'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Список задач', response.get_data(as_text=True))

    def test_register_user(self):
        response = self.app.post('/register', data={'username': 'testuser', 'password': 'testpass'})
        self.assertEqual(response.status_code, 302)  # Должен быть редирект на логин
        user = User.query.filter_by(username='testuser').first()
        self.assertIsNotNone(user)

    def test_login_user(self):
        # Регистрация пользователя
        self.app.post('/register', data={'username': 'testuser', 'password': 'testpass'})

        # Вход пользователя
        response = self.app.post('/login', data={'username': 'testuser', 'password': 'testpass'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Login successful.', response.get_data(as_text=True))

if __name__ == '__main__':
    # Запуск тестов
    unittest.main(argv=[''], exit=False)

    # Запуск приложения
    app.run(debug=True)