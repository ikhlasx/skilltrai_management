import os
from app import app, db, User
from werkzeug.security import generate_password_hash


def setup_production_database():
    """Setup database for production"""
    with app.app_context():
        # Create all tables
        db.create_all()

        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@skilltrain.com',
                password_hash=generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'admin123')),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created")

        print("✅ Database setup complete")


if __name__ == '__main__':
    setup_production_database()