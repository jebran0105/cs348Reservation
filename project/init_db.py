# init_db.py
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Date, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import os
from datetime import datetime

# Create base class for declarative models
Base = declarative_base()

class Section(Base):
    __tablename__ = 'sections'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    description = Column(String(200))
    # Relationship to tables
    tables = relationship('Table', back_populates='section')

class Table(Base):
    __tablename__ = 'tables'
    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False)
    capacity = Column(Integer, nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'))
    # Relationships
    section = relationship('Section', back_populates='tables')
    reservations = relationship('Reservation', back_populates='table')

class Customer(Base):
    __tablename__ = 'customers'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20), nullable=False)
    # Relationship to reservations
    reservations = relationship('Reservation', back_populates='customer')

class Reservation(Base):
    __tablename__ = 'reservations'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    duration = Column(Integer, default=120)
    table_id = Column(Integer, ForeignKey('tables.id'))
    customer_id = Column(Integer, ForeignKey('customers.id'))
    guest_count = Column(Integer, nullable=False)
    status = Column(String(20), default='confirmed')
    # Fix the created_at timestamp
    created_at = Column(DateTime, server_default=func.now())
    table = relationship('Table', back_populates='reservations')
    customer = relationship('Customer', back_populates='reservations')

def init_database():
    # Remove old database if it exists
    if os.path.exists('data/restaurant.db'):
        os.remove('data/restaurant.db')
    
    # Create data directory if it doesn't exist
    if not os.path.exists('data'):
        os.makedirs('data')
    
    # Create database engine
    engine = create_engine('sqlite:///data/restaurant.db')
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create a session to add initial data
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Add initial sections
        sections = [
            Section(name='Main Floor', description='Main dining area'),
            Section(name='Patio', description='Outdoor seating'),
            Section(name='Private Room', description='For special events')
        ]
        session.add_all(sections)
        session.flush()
        
        # Add initial tables
        tables = [
            Table(number=1, capacity=4, section_id=1),
            Table(number=2, capacity=4, section_id=1),
            Table(number=3, capacity=6, section_id=1),
            Table(number=4, capacity=2, section_id=2),
            Table(number=5, capacity=4, section_id=2),
            Table(number=6, capacity=8, section_id=3)
        ]
        session.add_all(tables)
        
        session.commit()
        print("Database initialized successfully with sample data!")
        
    except Exception as e:
        session.rollback()
        print(f"Error initializing database: {e}")
        
    finally:
        session.close()

def check_database():
    engine = create_engine('sqlite:///data/restaurant.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        sections_count = session.query(Section).count()
        tables_count = session.query(Table).count()
        customers_count = session.query(Customer).count()
        reservations_count = session.query(Reservation).count()
        
        print("\nDatabase Status:")
        print(f"Sections: {sections_count}")
        print(f"Tables: {tables_count}")
        print(f"Customers: {customers_count}")
        print(f"Reservations: {reservations_count}")
        
    except Exception as e:
        print(f"Error checking database: {e}")
    
    finally:
        session.close()

if __name__ == "__main__":
    init_database()
    check_database()