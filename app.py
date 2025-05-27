import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
from functools import wraps

# Initialize Flask app
app = Flask(__name__)

# Load configuration based on environment
if os.environ.get('VERCEL'):
    # Production configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
else:
    # Development configuration
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///skilltrain.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False)
    position = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    priority = db.Column(db.String(10), default='medium')
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)


class TrainingProgram(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    trainer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    duration_weeks = db.Column(db.Integer)
    max_students = db.Column(db.Integer, default=20)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class GoToMarketStrategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('training_program.id'), nullable=False)
    target_audience = db.Column(db.Text)
    marketing_channels = db.Column(db.Text)
    budget = db.Column(db.Float)
    timeline = db.Column(db.Text)
    success_metrics = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Removed updated_at column to avoid database conflict

# Authentication decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)

    return decorated_function


# Routes - FIXED VERSIONS
@app.route('/', methods=['GET'])
def index():
    """Home page - redirect to dashboard if logged in, otherwise show login"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page with proper GET/POST handling"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')

    # GET request - show login form
    return render_template('login.html')


@app.route('/logout', methods=['GET'])
def logout():
    """Logout route"""
    session.clear()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """Dashboard with role-based content"""
    user = User.query.get(session['user_id'])

    if not user:
        session.clear()
        return redirect(url_for('login'))

    # Get basic statistics
    total_users = User.query.count()
    total_tasks = Task.query.count()
    pending_tasks = Task.query.filter_by(status='pending').count()
    total_programs = TrainingProgram.query.count()

    # Get recent activities
    recent_tasks = Task.query.order_by(Task.created_at.desc()).limit(5).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    return render_template('admin_dashboard.html',
                           user=user,
                           total_users=total_users,
                           total_tasks=total_tasks,
                           pending_tasks=pending_tasks,
                           total_programs=total_programs,
                           recent_tasks=recent_tasks,
                           recent_users=recent_users)


@app.route('/users', methods=['GET'])
@admin_required
def users():
    """User management page"""
    users = User.query.all()
    return render_template('users.html', users=users)


@app.route('/add_user', methods=['GET', 'POST'])
@admin_required
def add_user():
    """Add new user"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', '')
        position = request.form.get('position', '').strip()

        # Validation
        if not username or not email or not password or not role:
            flash('Please fill in all required fields', 'error')
            return render_template('add_user.html')

        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('add_user.html')

        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('add_user.html')

        # Create new user
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            position=position if position else None
        )

        try:
            db.session.add(user)
            db.session.commit()
            flash('User created successfully', 'success')
            return redirect(url_for('users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'error')

    return render_template('add_user.html')


@app.route('/tasks', methods=['GET'])
@login_required
def tasks():
    """Tasks page"""
    user = User.query.get(session['user_id'])

    if user.role == 'admin':
        tasks = Task.query.all()
    else:
        # This allows management, trainers, and students to see their assigned tasks
        tasks = Task.query.filter_by(assigned_to=user.id).all()

    # Get user information for each task
    task_data = []
    for task in tasks:
        assigned_user = User.query.get(task.assigned_to)
        assigned_by_user = User.query.get(task.assigned_by)
        task_data.append({
            'task': task,
            'assigned_user': assigned_user,
            'assigned_by_user': assigned_by_user
        })

    return render_template('tasks.html', task_data=task_data, user=user)


@app.route('/add_task', methods=['GET', 'POST'])
@admin_required
def add_task():
    """Add new task - UPDATED to include management users"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        assigned_to = request.form.get('assigned_to', '')
        priority = request.form.get('priority', 'medium')
        due_date_str = request.form.get('due_date', '')

        if not title or not assigned_to:
            flash('Please fill in all required fields', 'error')
            # UPDATED: Include management users in the dropdown
            users = User.query.filter(User.role.in_(['trainer', 'student', 'management'])).all()
            return render_template('add_task.html', users=users)

        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid due date format', 'error')
                # UPDATED: Include management users in the dropdown
                users = User.query.filter(User.role.in_(['trainer', 'student', 'management'])).all()
                return render_template('add_task.html', users=users)

        task = Task(
            title=title,
            description=description,
            assigned_to=int(assigned_to),
            assigned_by=session['user_id'],
            priority=priority,
            due_date=due_date
        )

        try:
            db.session.add(task)
            db.session.commit()
            flash('Task created successfully', 'success')
            return redirect(url_for('tasks'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating task: {str(e)}', 'error')

    # GET request - show form
    # UPDATED: Include management users in the dropdown
    users = User.query.filter(User.role.in_(['trainer', 'student', 'management'])).all()
    return render_template('add_task.html', users=users)


@app.route('/programs', methods=['GET', 'POST'])
@login_required
def programs():
    """Programs page with add program functionality"""
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        # Handle program creation
        if user.role not in ['admin', 'trainer']:
            flash('Access denied. Only admins and trainers can create programs.', 'error')
            return redirect(url_for('programs'))

        program_name = request.form.get('program_name', '').strip()
        program_description = request.form.get('program_description', '').strip()
        duration_weeks = request.form.get('duration_weeks', '')
        max_students = request.form.get('max_students', '20')
        start_date_str = request.form.get('start_date', '')

        # Validation
        if not program_name:
            flash('Program name is required', 'error')
            programs = TrainingProgram.query.all()
            return render_template('programs.html', programs=programs, user=user)

        # Parse duration
        duration_weeks_int = None
        if duration_weeks:
            try:
                duration_weeks_int = int(duration_weeks)
                if duration_weeks_int <= 0:
                    raise ValueError("Duration must be positive")
            except ValueError:
                flash('Please enter a valid duration in weeks', 'error')
                programs = TrainingProgram.query.all()
                return render_template('programs.html', programs=programs, user=user)

        # Parse max students
        max_students_int = 20  # default
        if max_students:
            try:
                max_students_int = int(max_students)
                if max_students_int <= 0:
                    raise ValueError("Max students must be positive")
            except ValueError:
                flash('Please enter a valid number for max students', 'error')
                programs = TrainingProgram.query.all()
                return render_template('programs.html', programs=programs, user=user)

        # Parse start date
        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                # Calculate end date if duration is provided
                if duration_weeks_int:
                    end_date = start_date + timedelta(weeks=duration_weeks_int)
            except ValueError:
                flash('Please enter a valid start date', 'error')
                programs = TrainingProgram.query.all()
                return render_template('programs.html', programs=programs, user=user)

        # Determine trainer assignment
        trainer_id = user.id
        if user.role == 'admin':
            # Admin can assign to any trainer, but let's assign to first available trainer
            first_trainer = User.query.filter_by(role='trainer').first()
            if first_trainer:
                trainer_id = first_trainer.id
            else:
                trainer_id = user.id  # Assign to admin if no trainers exist

        # Create new training program
        program = TrainingProgram(
            name=program_name,
            description=program_description if program_description else None,
            trainer_id=trainer_id,
            duration_weeks=duration_weeks_int,
            max_students=max_students_int,
            start_date=start_date,
            end_date=end_date
        )

        try:
            db.session.add(program)
            db.session.commit()
            flash(f'Training program "{program_name}" created successfully!', 'success')
            return redirect(url_for('programs'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating program: {str(e)}', 'error')

    # GET request - show programs page
    programs = TrainingProgram.query.order_by(TrainingProgram.created_at.desc()).all()
    return render_template('programs.html', programs=programs, user=user)

@app.route('/update_task_status/<int:task_id>/<status>', methods=['GET'])
@login_required
def update_task_status(task_id, status):
    """Update task status - works for management users too"""
    task = Task.query.get_or_404(task_id)
    user = User.query.get(session['user_id'])

    # Check permissions - management users can update their own tasks
    if user.role != 'admin' and task.assigned_to != user.id:
        flash('You can only update your own tasks', 'error')
        return redirect(url_for('tasks'))

    if status not in ['pending', 'in_progress', 'completed']:
        flash('Invalid status', 'error')
        return redirect(url_for('tasks'))

    task.status = status
    if status == 'completed':
        task.completed_at = datetime.utcnow()

    try:
        db.session.commit()
        flash('Task status updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating task: {str(e)}', 'error')

    return redirect(url_for('tasks'))


@app.route('/calendar', methods=['GET'])
@login_required
def calendar():
    """Calendar page"""
    user = User.query.get(session['user_id'])

    # Get tasks for calendar - management users see their own tasks
    if user.role == 'admin':
        tasks = Task.query.filter(Task.due_date.isnot(None)).all()
    else:
        tasks = Task.query.filter_by(assigned_to=user.id).filter(Task.due_date.isnot(None)).all()

    # Prepare calendar events
    events = []
    for task in tasks:
        events.append({
            'title': f'Task: {task.title}',
            'start': task.due_date.isoformat(),
            'color': '#ff6b6b' if task.priority == 'high' else '#4ecdc4' if task.priority == 'medium' else '#45b7d1',
            'type': 'task'
        })

    return render_template('calendar.html', events=json.dumps(events))


@app.route('/analytics', methods=['GET'])
@login_required
def analytics():
    """Analytics page"""
    user = User.query.get(session['user_id'])

    if user.role not in ['admin', 'management']:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))

    # Calculate analytics
    total_tasks = Task.query.count()
    completed_tasks = Task.query.filter_by(status='completed').count()
    pending_tasks = Task.query.filter_by(status='pending').count()
    in_progress_tasks = Task.query.filter_by(status='in_progress').count()

    total_users = User.query.count()
    trainers_count = User.query.filter_by(role='trainer').count()
    students_count = User.query.filter_by(role='student').count()
    management_count = User.query.filter_by(role='management').count()

    total_programs = TrainingProgram.query.count()

    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    analytics_data = {
        'task_stats': {
            'total': total_tasks,
            'completed': completed_tasks,
            'pending': pending_tasks,
            'in_progress': in_progress_tasks,
            'completion_rate': round(completion_rate, 2)
        },
        'user_stats': {
            'total': total_users,
            'trainers': trainers_count,
            'students': students_count,
            'management': management_count
        },
        'program_stats': {
            'total': total_programs,
            'active_enrollments': 0  # Placeholder
        }
    }

    return render_template('analytics.html', analytics=analytics_data)


@app.route('/go_to_market', methods=['GET', 'POST'])
@login_required
def go_to_market():
    """Go-to-market strategies page with add strategy functionality"""
    user = User.query.get(session['user_id'])

    if user.role not in ['admin', 'management']:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Handle strategy creation
        program_id = request.form.get('program_id', '')
        target_audience = request.form.get('target_audience', '').strip()
        marketing_channels = request.form.get('marketing_channels', '').strip()
        budget = request.form.get('budget', '')
        timeline = request.form.get('timeline', '').strip()
        success_metrics = request.form.get('success_metrics', '').strip()

        # Validation
        if not program_id:
            flash('Please select a training program', 'error')
            strategies = GoToMarketStrategy.query.all()
            programs = TrainingProgram.query.all()
            return render_template('go_to_market.html', strategies=strategies, programs=programs)

        # Parse budget
        budget_float = None
        if budget:
            try:
                budget_float = float(budget)
                if budget_float < 0:
                    raise ValueError("Budget cannot be negative")
            except ValueError:
                flash('Please enter a valid budget amount', 'error')
                strategies = GoToMarketStrategy.query.all()
                programs = TrainingProgram.query.all()
                return render_template('go_to_market.html', strategies=strategies, programs=programs)

        # Check if strategy already exists for this program
        existing_strategy = GoToMarketStrategy.query.filter_by(program_id=int(program_id)).first()
        if existing_strategy:
            flash('A go-to-market strategy already exists for this program', 'error')
            strategies = GoToMarketStrategy.query.all()
            programs = TrainingProgram.query.all()
            return render_template('go_to_market.html', strategies=strategies, programs=programs)

        # Create new go-to-market strategy
        strategy = GoToMarketStrategy(
            program_id=int(program_id),
            target_audience=target_audience if target_audience else None,
            marketing_channels=marketing_channels if marketing_channels else None,
            budget=budget_float,
            timeline=timeline if timeline else None,
            success_metrics=success_metrics if success_metrics else None,
            created_by=user.id
        )

        try:
            db.session.add(strategy)
            db.session.commit()
            flash('Go-to-market strategy created successfully!', 'success')
            return redirect(url_for('go_to_market'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating strategy: {str(e)}', 'error')

    # GET request - show go-to-market page
    strategies = GoToMarketStrategy.query.order_by(GoToMarketStrategy.created_at.desc()).all()
    programs = TrainingProgram.query.all()

    return render_template('go_to_market.html', strategies=strategies, programs=programs)


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(405)
def method_not_allowed_error(error):
    return "Method Not Allowed. Please check the URL and try again.", 405


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


# Export app for Vercel
application = app

if __name__ == '__main__':
    # Only run in development
    if not os.environ.get('VERCEL'):
        with app.app_context():
            db.create_all()
            # Create admin user if not exists
            if not User.query.filter_by(username='admin').first():
                admin = User(
                    username='admin',
                    email='admin@skilltrain.com',
                    password_hash=generate_password_hash('admin123'),
                    role='admin'
                )
                db.session.add(admin)
                db.session.commit()

        app.run(debug=True, host='0.0.0.0', port=5000)