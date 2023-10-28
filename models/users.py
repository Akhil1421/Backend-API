from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine

Base = declarative_base()

# Replace 'mysql+mysqlconnector://username:password@localhost/dbname' with your MySQL database URL.
DATABASE_URL = "mysql+mysqlconnector://root:1421a1627b@localhost/world"
engine = create_engine(DATABASE_URL)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(length=255), unique=True, index=True)  # Specify a length for the email column
    access_token = Column(String(length=255), unique=True, index=True)
    refresh_token = Column(String(length=255), unique=True, index=True)

# Create the 'users' table
Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_user(db, user):
    db.add(user)
    db.commit()
    db.refresh(user)

def get_user_by_email(db, email):
    return db.query(User).filter(User.email == email).first()

def update_user_attributes(db, email, access_token = None, refresh_token = None):
    user = get_user_by_email(db, email)
    
    if user:
        # Update user attributes
        user.access_token = access_token
        user.refresh_token = refresh_token
        db.commit()
    else:
        raise ValueError("User not found")  # You can choose to handle this differently based on your application's logic