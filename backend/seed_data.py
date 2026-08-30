from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.models.user import User, Profile
from app.models.financial import IncomeSource, Expense, Asset, Liability, Goal, InsurancePolicy, FinancialFreedomTarget
from app.core.config import DATABASE_URL
import uuid
from datetime import date, datetime, timezone
from app.auth.manager import get_password_hash

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_test_data():
    db = SessionLocal()
    try:
        # List of users to ensure exist
        users_to_create = [
            {
                "email": "test@example.com",
                "password": "testpassword123",
                "role": "user",
                "profile": {
                    "full_name": "Test User",
                    "phone_number": "9876543210",
                    "address_line1": "123 Test Street",
                    "city": "Test City",
                    "state": "Test State",
                    "postal_code": "123456",
                    "country": "India",
                    "preferred_language": "en",
                    "timezone": "Asia/Kolkata",
                    "email_verified": True,
                    "phone_verified": True
                },
                "user_data": {
                    "date_of_birth": date(1990, 1, 1),
                    "gender": 'M',
                    "marital_status": 'married',
                    "dependents_count": 2,
                    "residential_status": 'resident_indian',
                    "pan_last_four": 'ABCD',
                    "aadhaar_last_four": '1234',
                    "employment_status": 'employed',
                    "primary_occupation": 'Software Engineer'
                }
            },
            {
                "email": "advisor@example.com",
                "password": "advisorpassword123",
                "role": "advisor",
                "profile": {
                    "full_name": "Financial Advisor",
                    "phone_number": "9876543211",
                    "address_line1": "456 Advisor Avenue",
                    "city": "Advisor City",
                    "state": "Advisor State",
                    "postal_code": "654321",
                    "country": "India",
                    "preferred_language": "en",
                    "timezone": "Asia/Kolkata",
                    "email_verified": True,
                    "phone_verified": True
                },
                "user_data": {
                    "date_of_birth": date(1985, 5, 15),
                    "gender": 'F',
                    "marital_status": 'single',
                    "dependents_count": 0,
                    "residential_status": 'resident_indian',
                    "pan_last_four": 'EFGH',
                    "aadhaar_last_four": '5678',
                    "employment_status": 'employed',
                    "primary_occupation": 'Financial Advisor'
                }
            },
            {
                "email": "admin@example.com",
                "password": "adminpassword123",
                "role": "admin",
                "profile": {
                    "full_name": "System Administrator",
                    "phone_number": "9876543212",
                    "address_line1": "789 Admin Road",
                    "city": "Admin City",
                    "state": "Admin State",
                    "postal_code": "112233",
                    "country": "India",
                    "preferred_language": "en",
                    "timezone": "Asia/Kolkata",
                    "email_verified": True,
                    "phone_verified": True
                },
                "user_data": {
                    "date_of_birth": date(1980, 1, 1),
                    "gender": 'M',
                    "marital_status": 'married',
                    "dependents_count": 0,
                    "residential_status": 'resident_indian',
                    "pan_last_four": 'IJKL',
                    "aadhaar_last_four": '9012',
                    "employment_status": 'employed',
                    "primary_occupation": 'System Administrator'
                }
            }
        ]

        for user_spec in users_to_create:
            email = user_spec["email"]
            # Check if profile exists for this email
            existing_profile = db.query(Profile).filter(Profile.email_address == email).first()
            if existing_profile:
                # Update existing user and profile
                user = existing_profile.user
                # Update user fields
                for key, value in user_spec["user_data"].items():
                    setattr(user, key, value)
                user.hashed_password = get_password_hash(user_spec["password"])
                user.role = user_spec["role"]
                user.is_active = True
                user.last_login = datetime.now(timezone.utc)
                # Update profile
                for key, value in user_spec["profile"].items():
                    setattr(existing_profile, key, value)
            else:
                # Create new user and profile
                user = User(
                    hashed_password=get_password_hash(user_spec["password"]),
                    role=user_spec["role"],
                    is_active=True,
                    last_login=datetime.now(timezone.utc),
                    **user_spec["user_data"]
                )
                db.add(user)
                db.flush()  # Get user_id

                profile = Profile(
                    user_id=user.user_id,
                    email_address=email,
                    **user_spec["profile"]
                )
                db.add(profile)

            # If this is the test user, also set up financial data
            if email == "test@example.com":
                # Delete existing financial data for this user
                db.query(IncomeSource).filter(IncomeSource.user_id == user.user_id).delete()
                db.query(Expense).filter(Expense.user_id == user.user_id).delete()
                db.query(Asset).filter(Asset.user_id == user.user_id).delete()
                db.query(Liability).filter(Liability.user_id == user.user_id).delete()
                db.query(Goal).filter(Goal.user_id == user.user_id).delete()
                db.query(InsurancePolicy).filter(InsurancePolicy.user_id == user.user_id).delete()
                db.query(FinancialFreedomTarget).filter(FinancialFreedomTarget.user_id == user.user_id).delete()

                # Create income sources
                income1 = IncomeSource(
                    user_id=user.user_id,
                    source_type='salary',
                    source_name='Monthly Salary',
                    amount=100000.00,
                    currency='INR',
                    frequency='monthly',
                    is_taxable=True,
                    tax_withheld=20000.00,
                    start_date=date(2023, 1, 1),
                    is_active=True
                )
                income2 = IncomeSource(
                    user_id=user.user_id,
                    source_type='bonus',
                    source_name='Annual Bonus',
                    amount=300000.00,
                    currency='INR',
                    frequency='annually',
                    is_taxable=True,
                    tax_withheld=60000.00,
                    start_date=date(2023, 1, 1),
                    is_active=True
                )
                db.add_all([income1, income2])

                # Create expenses
                expense1 = Expense(
                    user_id=user.user_id,
                    category='housing',
                    subcategory='rent',
                    description='Monthly rent for apartment',
                    amount=25000.00,
                    currency='INR',
                    frequency='monthly',
                    is_essential=True,
                    is_inflation_linked=True,
                    inflation_rate=0.05,
                    start_date=date(2023, 1, 1),
                    is_active=True
                )
                expense2 = Expense(
                    user_id=user.user_id,
                    category='food',
                    subcategory='groceries',
                    description='Monthly groceries',
                    amount=10000.00,
                    currency='INR',
                    frequency='monthly',
                    is_essential=True,
                    is_inflation_linked=True,
                    inflation_rate=0.06,
                    start_date=date(2023, 1, 1),
                    is_active=True
                )
                expense3 = Expense(
                    user_id=user.user_id,
                    category='transportation',
                    subcategory='fuel',
                    description='Monthly fuel expenses',
                    amount=3000.00,
                    currency='INR',
                    frequency='monthly',
                    is_essential=True,
                    is_inflation_linked=True,
                    inflation_rate=0.07,
                    start_date=date(2023, 1, 1),
                    is_active=True
                )
                db.add_all([expense1, expense2, expense3])

                # Create assets
                asset1 = Asset(
                    user_id=user.user_id,
                    asset_type='savsavings_account',
                    account_name='Savings Account',
                    institution_name='State Bank of India',
                    account_number_masked='1234',
                    current_value=2000000.00,
                    currency='INR',
                    purchase_date=date(2020, 1, 1),
                    expected_return_rate=0.04,
                    risk_level='low',
                    liquidity='high',
                    is_active=True
                )
                asset2 = Asset(
                    user_id=user.user_id,
                    asset_type='mutual_funds',
                    account_name='Mutual Fund SIP',
                    institution_name='HDFC Mutual Fund',
                    account_number_masked='5678',
                    current_value=3000000.00,
                    currency='INR',
                    purchase_date=date(2021, 1, 1),
                    expected_return_rate=0.12,
                    risk_level='medium',
                    liquidity='medium',
                    is_active=True
                )
                asset3 = Asset(
                    user_id=user.user_id,
                    asset_type='epf',
                    account_name='Employee Provident Fund',
                    institution_name='EPFO',
                    account_number_masked='9012',
                    current_value=1780000.00,
                    currency='INR',
                    purchase_date=date(2020, 1, 1),
                    expected_return_rate=0.085,
                    risk_level='low',
                    liquidity='low',
                    is_active=True
                )
                db.add_all([asset1, asset2, asset3])

                # Create liabilities
                liability1 = Liability(
                    user_id=user.user_id,
                    liability_type='home_loan',
                    lender_name='ICICI Bank',
                    account_number_masked='3456',
                    principal_outstanding=2500000.00,
                    currency='INR',
                    interest_rate=0.085,
                    interest_type='floating',
                    emi_amount=20000.00,
                    total_emis=240,
                    emis_paid=24,
                    start_date=date(2022, 1, 1),
                    end_date=date(2042, 1, 1),
                    is_tax_deductible=True,
                    is_active=True
                )
                db.add(liability1)

                # Create financial freedom target
                # Target age 60, target lifestyle expenses ₹50,000/month, inflation 6%, return 8%
                ff_target = FinancialFreedomTarget(
                    user_id=user.user_id,
                    target_age=60,
                    target_lifestyle_expenses=50000.00,
                    currency='INR',
                    inflation_assumption=0.06,
                    return_assumption=0.08,
                    current_age=36,  # As of 2026, born 1990-01-01
                    years_to_target=24,  # 60 - 36
                    # These will be calculated by the tools when needed
                )
                db.add(ff_target)

                # Create some test goals for the user
                goal1 = Goal(
                    user_id=user.user_id,
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
                    user_id=user.user_id,
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
                    inflation_rate=0.05,
                    notes='Down payment for purchasing a house',
                    is_active=True
                )
                goal3 = Goal(
                    user_id=user.user_id,
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
                    inflation_rate=0.06,
                    notes='Education fund for children',
                    is_active=True
                )
                db.add_all([goal1, goal2, goal3])

        # Commit all changes
        db.commit()

        # Create advisor consent for testing (advisor to test user)
        try:
            advisor_user = db.query(User).join(User.profile).filter(
                User.profile.email_address == "advisor@example.com"
            ).first()
            test_user = db.query(User).join(User.profile).filter(
                User.profile.email_address == "test@example.com"
            ).first()

            if advisor_user and test_user:
                # Check if consent already exists
                existing_consent = db.query(AdvisorConsent).filter(
                    AdvisorConsent.advisor_id == advisor_user.user_id,
                    AdvisorConsent.client_id == test_user.user_id,
                    AdvisorConsent.is_active == True
                ).first()

                if not existing_consent:
                    # Create consent
                    new_consent = AdvisorConsent(
                        advisor_id=advisor_user.user_id,
                        client_id=test_user.user_id,
                        scope="read_only",
                        is_active=True
                    )
                    db.add(new_consent)
                    db.commit()
                    print("Advisor consent created for testing")
        except Exception as e:
            print(f"Note: Could not create advisor consent: {e}")

        print("Seed data created/updated successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error creating seed data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_data()