# manage.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade
import os

# Инициализация приложения
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация базы данных
db = SQLAlchemy(app)

# Инициализация миграций
migrate = Migrate(app, db)

# Применение миграций
with app.app_context():
    db.create_all()
    upgrade()

# Запуск приложения
if __name__ == '__main__':
    app.run()