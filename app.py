from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SECRET_KEY'] = 'mysecret'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ---------------- Models ----------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    tasks = db.relationship('Task', backref='user', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- Routes ----------------
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('⚠️ Username already taken, try another one.')
            return redirect(url_for('signup'))

        # Hash the password and create new user
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        flash('✅ Account created successfully! Please login.')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('tasks'))
        else:
            flash('❌ Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/tasks', methods=['GET', 'POST'])
@login_required
def tasks():
    if request.method == 'POST':
        task_title = request.form['title']
        new_task = Task(title=task_title, user_id=current_user.id)
        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for('tasks'))

    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return render_template('tasks.html', tasks=tasks)

@app.route('/complete/<int:task_id>')
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id == current_user.id:
        task.completed = True
        db.session.commit()
    return redirect(url_for('tasks'))

@app.route('/delete/<int:task_id>')
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id == current_user.id:
        db.session.delete(task)
        db.session.commit()
    return redirect(url_for('tasks'))

@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)

    if task.user_id != current_user.id:
        flash("❌ You are not allowed to edit this task.")
        return redirect(url_for('tasks'))

    if request.method == 'POST':
        new_title = request.form['title']
        task.title = new_title
        db.session.commit()
        flash("✅ Task updated successfully!")
        return redirect(url_for('tasks'))

    return render_template('edit_task.html', task=task)

# ---------------- Dashboard ----------------
@app.route('/dashboard')
@login_required
def dashboard():
    total_tasks = Task.query.filter_by(user_id=current_user.id).count()
    completed_tasks = Task.query.filter_by(user_id=current_user.id, completed=True).count()
    pending_tasks = total_tasks - completed_tasks

    return render_template(
        'dashboard.html',
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks
    )

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
