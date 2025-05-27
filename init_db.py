from app import app, db, User
from werkzeug.security import generate_password_hash

def init_database():
    """Initialize the database with sample data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create sample users if they don't exist
        sample_users = [
            {
                'username': 'admin',
                'email': 'admin@skilltrain.com',
                'password': 'admin123',
                'role': 'admin'
            },
            {
                'username': 'trainer1',
                'email': 'trainer1@skilltrain.com',
                'password': 'trainer123',
                'role': 'trainer'
            },
            {
                'username': 'student1',
                'email': 'student1@skilltrain.com',
                'password': 'student123',
                'role': 'student'
            },
            {
                'username': 'ceo',
                'email': 'ceo@skilltrain.com',
                'password': 'ceo123',
                'role': 'management',
                'position': 'CEO'
            },
            {
                'username': 'cto',
                'email': 'cto@skilltrain.com',
                'password': 'cto123',
                'role': 'management',
                'position': 'CTO'
            }
        ]
        
        for user_data in sample_users:
            if not User.query.filter_by(username=user_data['username']).first():
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    password_hash=generate_password_hash(user_data['password']),
                    role=user_data['role'],
                    position=user_data.get('position')
                )
                db.session.add(user)
        
        db.session.commit()
        print("Database initialized with sample data!")

if __name__ == '__main__':
    init_database() 