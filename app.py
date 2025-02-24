#app.py
import logging
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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