from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'barber.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Barber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref='barber', uselist=False)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barber_id = db.Column(db.Integer, db.ForeignKey('barber.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    time = db.Column(db.String(5), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Confirmed')
    barber = db.relationship('Barber', backref='bookings')
    client = db.relationship('Client', backref='bookings')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper function for slots
def get_available_slots(barber_id, date):
    all_slots = [f"{hour:02d}:{minute:02d}" for hour in range(9, 17) for minute in (0, 30)]
    booked_slots = Booking.query.filter_by(barber_id=barber_id, date=date, status='Confirmed').all()
    booked_times = [b.time for b in booked_slots]
    return [slot for slot in all_slots if slot not in booked_times]

@app.route('/')
def home():
    barbers = Barber.query.all()
    return render_template('index.html', barbers=barbers)

@app.route('/slots', methods=['GET'])
def slots():
    barber_id = request.args.get('barber_id')
    date = request.args.get('date')
    if not barber_id or not date:
        return jsonify({'error': 'Missing barber_id or date'}), 400
    # Validate date
    try:
        selected_date = datetime.strptime(date, '%Y-%m-%d')
        if selected_date.date() < datetime.now().date():
            return jsonify({'error': 'Cannot book past dates'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    slots = get_available_slots(int(barber_id), date)
    return jsonify({'slots': slots})

@app.route('/book', methods=['POST'])
def book():
    barber_id = request.form['barber_id']
    date = request.form['date']
    time = request.form['time']
    client_name = request.form['client_name']
    client_email = request.form['client_email']

    # Validate date
    try:
        selected_date = datetime.strptime(date, '%Y-%m-%d')
        if selected_date.date() < datetime.now().date():
            flash('Cannot book past dates.', 'error')
            return redirect(url_for('home'))
    except ValueError:
        flash('Invalid date format.', 'error')
        return redirect(url_for('home'))

    # Check for duplicate booking
    existing_booking = Booking.query.filter_by(barber_id=barber_id, date=date, time=time, status='Confirmed').first()
    if existing_booking:
        flash('This time slot is already booked.', 'error')
        return redirect(url_for('home'))

    # Check if client exists
    client = Client.query.filter_by(email=client_email).first()
    if not client:
        client = Client(name=client_name, email=client_email)
        db.session.add(client)
        db.session.commit()

    # Create booking
    booking = Booking(
        barber_id=barber_id,
        client_id=client.id,
        date=date,
        time=time,
        status='Confirmed'
    )
    db.session.add(booking)
    db.session.commit()
    flash('Booking confirmed!', 'success')
    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    barbers = Barber.query.all()
    bookings = Booking.query.all()
    return render_template('dashboard.html', barbers=barbers, bookings=bookings)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Add test barber and user if none exist
        if not User.query.first():
            user = User(username='barber1')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            barber = Barber(name='John', user_id=user.id)
            db.session.add(barber)
            db.session.commit()
    app.run(debug=True)