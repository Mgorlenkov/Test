# manage.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade
import os
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
import subprocess
import sys

# Загрузка переменных окружения из файла .env
load_dotenv()

# Инициализация приложения
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация базы данных
db = SQLAlchemy(app)

# Инициализация миграций
migrate = Migrate(app, db)

# Функция для инициализации Alembic и применения миграций
def apply_migrations():
    # Путь к конфигурационному файлу Alembic
    alembic_cfg = Config("migrations/alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", app.config['SQLALCHEMY_DATABASE_URI'])

    # Проверка наличия директории migrations
    if not os.path.exists("migrations"):
        print("Error: Path doesn't exist: 'migrations'. Initializing Alembic...")
        command.init(alembic_cfg, "migrations")

    # Применение миграций
    command.upgrade(alembic_cfg, "head")

# Применение миграций
with app.app_context():
    db.create_all()
    apply_migrations()

# Запуск app.py после применения миграций
if __name__ == '__main__':
    print("Migrations applied. Starting app.py...")
    subprocess.run([sys.executable, "app.py"])