from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import logging
import re
from sqlalchemy.exc import OperationalError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///barber.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    
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
    email = db.Column(db.String(120), nullable=False)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barber_id = db.Column(db.Integer, db.ForeignKey('barber.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    time = db.Column(db.String(5), nullable=False)
    status = db.Column(db.String(20), default='Confirmed')
    barber = db.relationship('Barber', backref='bookings')
    client = db.relationship('Client', backref='bookings')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize database at startup
def initialize_database():
    try:
        logger.info("Attempting to initialize database")
        db_path = os.path.join(os.getcwd(), 'barber.db')
        if not os.path.exists(db_path):
            logger.info(f"Database file {db_path} does not exist, creating it")
            open(db_path, 'a').close()
            logger.info(f"Database file {db_path} created")
        
        with app.app_context():
            logger.info("Creating database tables")
            db.create_all()
            logger.info("Database tables created successfully")
            
            if not User.query.first():
                logger.info("No users found, adding test data")
                user = User(username='barber1')
                user.set_password('password123')
                db.session.add(user)
                db.session.commit()
                barber = Barber(name='John', user_id=user.id)
                db.session.add(barber)
                db.session.commit()
                logger.info("Test user and barber added successfully")
    except OperationalError as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}")
        raise

# Run database initialization at startup
initialize_database()

# Routes
@app.route('/')
def index():
    try:
        barbers = Barber.query.all()
    except OperationalError as e:
        logger.error(f"Error querying barbers: {e}")
        flash('Database error. Please try again later.', 'error')
        barbers = []
    return render_template('index.html', barbers=barbers)

@app.route('/book', methods=['POST'])
def book():
    try:
        barber_id = request.form['barber']
        date = request.form['date']
        time = request.form['time']
        client_name = request.form['client_name'].strip()
        client_email = request.form['client_email'].strip()
        
        # Validate inputs
        if not client_name:
            flash('Client name cannot be empty.', 'error')
            return redirect(url_for('index'))
        
        # Email validation with regex
        email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_pattern, client_email):
            flash('Invalid email address.', 'error')
            return redirect(url_for('index'))
        
        today = datetime.now().strftime('%Y-%m-%d')
        if date < today:
            flash('Cannot book past dates.', 'error')
            return redirect(url_for('index'))
        
        existing_booking = Booking.query.filter_by(barber_id=barber_id, date=date, time=time).first()
        if existing_booking:
            flash('This time slot is already booked.', 'error')
            return redirect(url_for('index'))
        
        client = Client(name=client_name, email=client_email)
        db.session.add(client)
        db.session.commit()
        
        booking = Booking(barber_id=barber_id, client_id=client.id, date=date, time=time)
        db.session.add(booking)
        db.session.commit()
        
        flash('Booking confirmed!', 'success')
        return redirect(url_for('index'))
    except OperationalError as e:
        logger.error(f"Error creating booking: {e}")
        flash('Database error. Please try again later.', 'error')
        return redirect(url_for('index'))

@app.route('/slots', methods=['GET'])
def slots():
    try:
        barber_id = request.args.get('barber_id')
        date = request.args.get('date')
        booked_slots = Booking.query.filter_by(barber_id=barber_id, date=date).all()
        booked_times = [slot.time for slot in booked_slots]
        all_slots = ['09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00']
        available_slots = [slot for slot in all_slots if slot not in booked_times]
        return jsonify(available_slots)
    except OperationalError as e:
        logger.error(f"Error querying slots: {e}")
        return jsonify([]), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for('dashboard'))
            flash('Invalid username or password.', 'error')
        return render_template('login.html')
    except OperationalError as e:
        logger.error(f"Error during login: {e}")
        flash('Database error. Please try again later.', 'error')
        return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        bookings = Booking.query.join(Barber).filter(Barber.user_id == current_user.id).all()
        return render_template('dashboard.html', bookings=bookings, username=current_user.username)
    except OperationalError as e:
        logger.error(f"Error querying dashboard: {e}")
        flash('Database error. Please try again later.', 'error')
        return render_template('dashboard.html', bookings=[], username=current_user.username)

@app.route('/cancel/<int:booking_id>', methods=['POST'])
@login_required
def cancel(booking_id):
    try:
        booking = Booking.query.get_or_404(booking_id)
        # Ensure the booking belongs to the logged-in barber
        barber = Barber.query.filter_by(user_id=current_user.id).first()
        if booking.barber_id != barber.id:
            flash('Unauthorized action.', 'error')
            return redirect(url_for('dashboard'))
        booking.status = 'Cancelled'
        db.session.commit()
        flash('Booking cancelled successfully!', 'success')
    except OperationalError as e:
        logger.error(f"Error cancelling booking: {e}")
        flash('Database error. Please try again later.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)