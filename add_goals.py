import sys
sys.path.append('./backend')

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from backend.app.models.user import User, Profile
from backend.app.models.financial import Goal
from backend.app.core.config import DATABASE_URL
import uuid
from datetime import date

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def add_test_goals():
    db = SessionLocal()
    try:
        # Find the test user by email
        test_user = db.query(User).join(Profile, User.user_id == Profile.user_id).filter(Profile.email_address == "test@example.com").first()
        if not test_user:
            print("Test user not found. Please run seed_data.py first.")
            return

        # Check if goals already exist for this user to avoid duplicates
        existing_goals = db.query(Goal).filter(Goal.user_id == test_user.user_id).count()
        if existing_goals > 0:
            print(f"Found {existing_goals} existing goals for test user. Skipping goal creation to avoid duplicates.")
            return

        # Create some test goals for the user
        goal1 = Goal(
            user_id=test_user.user_id,
            goal_type='emergency_fund',
            goal_name='Emergency Fund',
            target_amount=300000.00,  # 6 months of expenses (approx)
            currency='INR',
            target_date=date(2025, 12, 31),
            priority='high',
            current_amount=50000.00,
            monthly_contribution=10000.00,
            expected_return=0.04,  # 4% for savings account
            inflation_adjusted=False,
            notes='Fund to cover unexpected expenses',
            is_active=True
        )
        goal2 = Goal(
            user_id=test_user.user_id,
            goal_type='home_purchase',
            goal_name='Down Payment for House',
            target_amount=2000000.00,  # 20% of 1 crore house
            currency='INR',
            target_date=date(2030, 12, 31),
            priority='high',
            current_amount=500000.00,
            monthly_contribution=20000.00,
            expected_return=0.07,  # 7% for balanced portfolio
            inflation_adjusted=True,
            notes='Down payment for purchasing a house',
            is_active=True
        )
        goal3 = Goal(
            user_id=test_user.user_id,
            goal_type='education',
            goal_name='Child Education Fund',
            target_amount=1500000.00,  # For two children
            currency='INR',
            target_date=date(2035, 12, 31),
            priority='medium',
            current_amount=200000.00,
            monthly_contribution=15000.00,
            expected_return=0.08,  # 8% for equity investments
            inflation_adjusted=True,
            notes='Education fund for children',
            is_active=True
        )
        db.add_all([goal1, goal2, goal3])
        db.commit()
        print("Test goals created successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error creating goals: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_test_goals()