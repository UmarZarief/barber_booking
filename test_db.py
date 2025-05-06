from app import app, db, User, Barber

with app.app_context():
    print("Users:", User.query.all())
    print("Barbers:", Barber.query.all())