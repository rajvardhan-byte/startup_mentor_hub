import os
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'startup_mentor_hub_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------- DATABASE MODELS ----------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'entrepreneur' or 'mentor'
    bio = db.Column(db.Text, nullable=True)
    expertise = db.Column(db.String(200), nullable=True)

class Pitch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    feedback = db.Column(db.Text, nullable=True)
    entrepreneur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entrepreneur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    booking_date = db.Column(db.String(50), nullable=False)
    meeting_link = db.Column(db.String(200), default="https://meet.google.com/new")
    status = db.Column(db.String(20), default="Scheduled")

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    course_type = db.Column(db.String(20), nullable=False)  # 'free' or 'paid'
    link_or_url = db.Column(db.String(255), nullable=False)
    embed_url = db.Column(db.String(255), nullable=True)
    price = db.Column(db.Float, default=0.0)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(20), default="In Progress")
    entrepreneur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    entrepreneur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    feedback = db.Column(db.Text, nullable=False)

# ---------------- HELPER FUNCTIONS ----------------

def current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def extract_youtube_embed(url):
    """Converts YouTube standard/short URL into an embeddable format using raw string regex."""
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)'
        r'([^&=%\?]{11})'
    )
    match = re.search(youtube_regex, url)
    if match:
        video_id = match.group(4)
        return f"https://www.youtube.com/embed/{video_id}"
    return None

# ---------------- ROUTES ----------------

@app.route('/')
def index():
    courses = Course.query.order_by(Course.created_at.desc()).limit(6).all()
    mentors = User.query.filter_by(role='mentor').all()
    return render_template('index.html', user=current_user(), courses=courses, mentors=mentors)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        expertise = request.form.get('expertise', '')
        bio = request.form.get('bio', '')

        if User.query.filter_by(email=email).first():
            flash('Email address is already registered.', 'danger')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password, method='scrypt')
        new_user = User(name=name, email=email, password_hash=hashed_pw, role=role, expertise=expertise, bio=bio)
        db.session.add(new_user)
        db.session.commit()
        flash('Account registered successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', user=current_user())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['role'] = user.role
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email address or password.', 'danger')
    return render_template('login.html', user=current_user())

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    user = current_user()
    if not user:
        flash('Please log in to access your dashboard.', 'warning')
        return redirect(url_for('login'))

    if user.role == 'entrepreneur':
        bookings = Booking.query.filter_by(entrepreneur_id=user.id).all()
        pitches = Pitch.query.filter_by(entrepreneur_id=user.id).all()
        goals = Goal.query.filter_by(entrepreneur_id=user.id).all()
        return render_template('dashboard.html', user=user, bookings=bookings, pitches=pitches, goals=goals)
    else:
        bookings = Booking.query.filter_by(mentor_id=user.id).all()
        all_pitches = Pitch.query.all()
        my_courses = Course.query.filter_by(mentor_id=user.id).all()
        reviews = Review.query.filter_by(mentor_id=user.id).all()
        return render_template('dashboard.html', user=user, bookings=bookings, pitches=all_pitches, courses=my_courses, reviews=reviews)

@app.route('/mentors')
def mentors():
    mentor_list = User.query.filter_by(role='mentor').all()
    return render_template('mentors.html', user=current_user(), mentors=mentor_list)

@app.route('/book_mentor/<int:mentor_id>', methods=['POST'])
def book_mentor(mentor_id):
    user = current_user()
    if not user or user.role != 'entrepreneur':
        flash('Only entrepreneurs can book mentorship sessions.', 'warning')
        return redirect(url_for('login'))

    booking_date = request.form['booking_date']
    meeting_link = request.form.get('meeting_link', 'https://meet.google.com/new')

    new_booking = Booking(
        entrepreneur_id=user.id,
        mentor_id=mentor_id,
        booking_date=booking_date,
        meeting_link=meeting_link
    )
    db.session.add(new_booking)
    db.session.commit()
    flash('Mentorship session booked successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/pitches', methods=['GET', 'POST'])
def pitches():
    user = current_user()
    if request.method == 'POST':
        if not user or user.role != 'entrepreneur':
            flash('Only entrepreneurs can submit pitches.', 'danger')
            return redirect(url_for('login'))

        title = request.form['title']
        description = request.form['description']
        new_pitch = Pitch(title=title, description=description, entrepreneur_id=user.id)
        db.session.add(new_pitch)
        db.session.commit()
        flash('Startup pitch submitted!', 'success')
        return redirect(url_for('pitches'))

    all_pitches = Pitch.query.order_by(Pitch.created_at.desc()).all()
    return render_template('pitches.html', user=user, pitches=all_pitches)

@app.route('/feedback/<int:pitch_id>', methods=['POST'])
def add_feedback(pitch_id):
    user = current_user()
    if not user or user.role != 'mentor':
        flash('Only mentors can provide feedback on pitches.', 'danger')
        return redirect(url_for('pitches'))

    pitch = Pitch.query.get_or_404(pitch_id)
    pitch.feedback = request.form['feedback']
    db.session.commit()
    flash('Feedback submitted successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/courses', methods=['GET', 'POST'])
def courses():
    user = current_user()
    if request.method == 'POST':
        if not user or user.role != 'mentor':
            flash('Only registered mentors can publish courses or video resources.', 'danger')
            return redirect(url_for('courses'))

        title = request.form['title']
        description = request.form.get('description', '')
        course_type = request.form['course_type']  # 'free' or 'paid'
        raw_url = request.form['url']
        price = float(request.form.get('price', 0.0)) if course_type == 'paid' else 0.0
        embed_url = extract_youtube_embed(raw_url) if course_type == 'free' else None

        new_course = Course(
            title=title,
            description=description,
            course_type=course_type,
            link_or_url=raw_url,
            embed_url=embed_url,
            price=price,
            mentor_id=user.id
        )
        db.session.add(new_course)
        db.session.commit()
        flash('Course published successfully!', 'success')
        return redirect(url_for('courses'))

    all_courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template('courses.html', user=user, courses=all_courses)

@app.route('/growth', methods=['GET', 'POST'])
def growth():
    user = current_user()
    if not user or user.role != 'entrepreneur':
        flash('Access restricted to entrepreneurs.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        new_goal = Goal(title=title, entrepreneur_id=user.id)
        db.session.add(new_goal)
        db.session.commit()
        flash('Milestone goal added!', 'success')
        return redirect(url_for('growth'))

    goals = Goal.query.filter_by(entrepreneur_id=user.id).all()
    return render_template('growth.html', user=user, goals=goals)

@app.route('/toggle_goal/<int:goal_id>')
def toggle_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    goal.status = 'Completed' if goal.status == 'In Progress' else 'In Progress'
    db.session.commit()
    return redirect(url_for('growth'))

@app.route('/review/<int:mentor_id>', methods=['POST'])
def add_review(mentor_id):
    user = current_user()
    if not user or user.role != 'entrepreneur':
        flash('Only entrepreneurs can review mentors.', 'warning')
        return redirect(url_for('mentors'))

    rating = int(request.form['rating'])
    feedback = request.form['feedback']
    new_review = Review(mentor_id=mentor_id, entrepreneur_id=user.id, rating=rating, feedback=feedback)
    db.session.add(new_review)
    db.session.commit()
    flash('Review saved.', 'success')
    return redirect(url_for('mentors'))

# Initialize database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)