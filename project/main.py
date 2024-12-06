import streamlit as st
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Date, Time, text
from sqlalchemy.sql import func, extract
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import text
import numpy as np

# Get the current directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Create data directory if it doesn't exist
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Database path
DB_PATH = os.path.join(DATA_DIR, 'restaurant.db')
DATABASE_URL = f'sqlite:///{DB_PATH}'

# Create base class for declarative models
Base = declarative_base()

# Define models
class Section(Base):
    __tablename__ = 'sections'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    description = Column(String(200))
    tables = relationship('Table', back_populates='section')

class Table(Base):
    __tablename__ = 'tables'
    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False)
    capacity = Column(Integer, nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'))
    section = relationship('Section', back_populates='tables')
    reservations = relationship('Reservation', back_populates='table')

class Customer(Base):
    __tablename__ = 'customers'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20), nullable=False)
    reservations = relationship('Reservation', back_populates='customer')

class Reservation(Base):
    __tablename__ = 'reservations'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    table_id = Column(Integer, ForeignKey('tables.id'))
    customer_id = Column(Integer, ForeignKey('customers.id'))
    guest_count = Column(Integer, nullable=False)
    status = Column(String(20), default='confirmed')
    created_at = Column(DateTime, default=datetime.utcnow)
    table = relationship('Table', back_populates='reservations')
    customer = relationship('Customer', back_populates='reservations')

# Create engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def execute_prepared_statement(query, params=None):
    with engine.connect() as connection:
        if params is None:
            params = {}
        result = connection.execute(text(query), params)
        return result

def init_db():
    try:
        # Create tables
        Base.metadata.create_all(engine)
        
        session = SessionLocal()
        
        # Check if we need to add initial data
        if session.query(Section).count() == 0:
            # Add sections
            sections = [
                Section(name='Main Floor', description='Main dining area'),
                Section(name='Patio', description='Outdoor seating'),
                Section(name='Private Room', description='For special events')
            ]
            session.add_all(sections)
            session.commit()

            # Add tables
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
            st.success("Database initialized with sample data!")
        
    except Exception as e:
        st.error(f"Error initializing database: {e}")
    finally:
        session.close()

def format_reservations_display(df):
    if not df.empty:
        # Create a copy to avoid modifying the original
        formatted_df = df.copy()
        
        # Rename columns for better display
        formatted_df = formatted_df.rename(columns={
            'date': 'Date',
            'time': 'Time',
            'customer_name': 'Customer',
            'phone': 'Phone',
            'table_number': 'Table',
            'guest_count': 'Guests',
            'status': 'Status'
        })
        
        return formatted_df
    return pd.DataFrame()

def get_current_reservations():
    query = """
    SELECT 
        r.id AS id,
        r.date AS date,
        r.time AS time,
        r.guest_count AS guest_count,
        r.status AS status,
        c.name AS customer_name,
        c.email AS customer_email,
        c.phone AS phone,
        t.number AS table_number
    FROM reservations r
    JOIN customers c ON r.customer_id = c.id
    JOIN tables t ON r.table_id = t.id
    ORDER BY r.date, r.time
    """
    params = {}
    result = execute_prepared_statement(query, params)

    # Convert the result to a DataFrame
    df = pd.DataFrame(result.fetchall(), columns=result.keys())

    if not df.empty:
        # Format the date column
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

        # Handle mixed time formats
        def parse_time(time_str):
            try:
                return pd.to_datetime(time_str, format='%H:%M:%S.%f').strftime('%I:%M %p')
            except ValueError:
                return pd.to_datetime(time_str, format='%H:%M:%S').strftime('%I:%M %p')

        df['time'] = df['time'].astype(str).apply(parse_time)

        # Sort DataFrame by 'id' column
        df = df.sort_values(by='id', ascending=True).reset_index(drop=True)

    return df


def delete_reservation(reservation_id):
    session = SessionLocal()
    try:
        # Debug print
        st.write(f"Attempting to delete reservation with ID: {reservation_id}")
        
        # Get the reservation
        reservation = session.query(Reservation).filter_by(id=int(reservation_id)).first()
        
        # Debug print
        st.write(f"Found reservation: {reservation}")
        
        if reservation:
            session.delete(reservation)
            session.commit()
            return True, "Reservation deleted successfully!"
        return False, f"Reservation with ID {reservation_id} not found."
    except Exception as e:
        session.rollback()
        return False, f"Error deleting reservation: {str(e)}"
    finally:
        session.close()
    
def update_reservation(reservation_id, update_data):
    session = SessionLocal()
    try:
        # Get the reservation and associated customer
        reservation = session.query(Reservation).filter_by(id=int(reservation_id)).first()
        if not reservation:
            return False, "Reservation not found"
        
        # Update reservation fields
        reservation.date = update_data['date']
        reservation.time = update_data['time']
        reservation.guest_count = update_data['guest_count']
        reservation.table_id = update_data['table_id']
        
        # Update customer fields through the relationship
        reservation.customer.name = update_data['customer_name']
        reservation.customer.email = update_data['customer_email']
        reservation.customer.phone = update_data['customer_phone']
        
        session.commit()
        return True, "Reservation updated successfully!"
    except Exception as e:
        session.rollback()
        return False, f"Error updating reservation: {str(e)}"
    finally:
        session.close()

def get_available_tables(date, time, guest_count):
    session = SessionLocal()
    try:
        suitable_tables = session.query(Table).filter(Table.capacity >= guest_count).all()
        available_tables = []
        for table in suitable_tables:
            reservation_exists = session.query(Reservation).filter(
                Reservation.table_id == table.id,
                Reservation.date == date,
                Reservation.time.between(
                    (datetime.combine(date, time) - timedelta(hours=2)).time(),
                    (datetime.combine(date, time) + timedelta(hours=2)).time()
                )
            ).first()
            if not reservation_exists:
                available_tables.append(table)
        return available_tables
    finally:
        session.close()

def create_reservation(customer_data, reservation_data):
    session = SessionLocal()
    try:
        # Check if customer exists
        customer = session.query(Customer).filter_by(email=customer_data['email']).first()
        if not customer:
            customer = Customer(
                name=customer_data['name'],
                email=customer_data['email'],
                phone=customer_data['phone']
            )
            session.add(customer)
            session.flush()

        # Create reservation
        reservation = Reservation(
            date=reservation_data['date'],
            time=reservation_data['time'],
            table_id=reservation_data['table_id'],
            customer_id=customer.id,
            guest_count=reservation_data['guest_count']
        )
        session.add(reservation)
        session.commit()
        return True, "Reservation created successfully!"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()

def fetch_key_metrics(start_date, end_date, selected_section, min_guest_count, max_guest_count):
    try:
        # Base query for Total Reservations
        base_query = """
        SELECT COUNT(r.id) AS total_reservations
        FROM reservations r
        LEFT JOIN tables t ON r.table_id = t.id
        LEFT JOIN sections s ON t.section_id = s.id
        WHERE r.date BETWEEN :start_date AND :end_date
        AND r.status = 'confirmed'
        """

        # Add filters for section and guest count
        filters = []
        if selected_section != "All Sections":
            filters.append("s.name = :selected_section")
        filters.append("r.guest_count BETWEEN :min_guest_count AND :max_guest_count")
        if filters:
            base_query += " AND " + " AND ".join(filters)

        # Parameters for the query
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'selected_section': selected_section,
            'min_guest_count': min_guest_count,
            'max_guest_count': max_guest_count,
        }

        # Execute the Total Reservations query
        result = execute_prepared_statement(base_query, params)
        row = result.fetchone()
        total_reservations = row[0] if row and row[0] is not None else 0

        # Average Party Size
        avg_party_size_query = """
        SELECT AVG(r.guest_count) AS avg_party_size
        FROM reservations r
        LEFT JOIN tables t ON r.table_id = t.id
        LEFT JOIN sections s ON t.section_id = s.id
        WHERE r.date BETWEEN :start_date AND :end_date
        AND r.status = 'confirmed'
        """
        if selected_section != "All Sections":
            avg_party_size_query += " AND s.name = :selected_section"
        avg_party_size_query += " AND r.guest_count BETWEEN :min_guest_count AND :max_guest_count"

        result = execute_prepared_statement(avg_party_size_query, params)
        row = result.fetchone()
        avg_party_size = round(row[0], 1) if row and row[0] is not None else 0.0

        # Most Busy Day
        most_busy_day_query = """
        SELECT r.date
        FROM reservations r
        LEFT JOIN tables t ON r.table_id = t.id
        LEFT JOIN sections s ON t.section_id = s.id
        WHERE r.date BETWEEN :start_date AND :end_date
        AND r.status = 'confirmed'
        """
        if selected_section != "All Sections":
            most_busy_day_query += " AND s.name = :selected_section"
        most_busy_day_query += """
        GROUP BY r.date
        ORDER BY COUNT(r.id) DESC
        LIMIT 1
        """

        result = execute_prepared_statement(most_busy_day_query, params)
        most_busy_day = result.fetchone()
        most_busy_day = most_busy_day[0] if most_busy_day else "N/A"

        # Peak Hour
        peak_hour_query = """
        SELECT r.time
        FROM reservations r
        LEFT JOIN tables t ON r.table_id = t.id
        LEFT JOIN sections s ON t.section_id = s.id
        WHERE r.date BETWEEN :start_date AND :end_date
        AND r.status = 'confirmed'
        """
        if selected_section != "All Sections":
            peak_hour_query += " AND s.name = :selected_section"
        peak_hour_query += """
        GROUP BY r.time
        ORDER BY COUNT(r.time) DESC
        LIMIT 1
        """

        result = execute_prepared_statement(peak_hour_query, params)
        peak_hour = result.fetchone()
        peak_hour = peak_hour[0] if peak_hour else "N/A"

        # Most Popular Section
        most_popular_section_query = """
        SELECT s.name
        FROM reservations r
        LEFT JOIN tables t ON r.table_id = t.id
        LEFT JOIN sections s ON t.section_id = s.id
        WHERE r.date BETWEEN :start_date AND :end_date
        AND r.status = 'confirmed'
        """
        most_popular_section_query += """
        GROUP BY s.name
        ORDER BY COUNT(r.id) DESC
        LIMIT 1
        """

        result = execute_prepared_statement(most_popular_section_query, params)
        most_popular_section = result.fetchone()
        most_popular_section = most_popular_section[0] if most_popular_section else "N/A"

        return {
            'total_reservations': total_reservations,
            'avg_party_size': avg_party_size,
            'most_busy_day': most_busy_day,
            'peak_hour': peak_hour,
            'most_popular_section': most_popular_section,
        }

    except Exception as e:
        st.error(f"Error fetching key metrics: {str(e)}")
        return {
            'total_reservations': 0,
            'avg_party_size': 0.0,
            'most_busy_day': "N/A",
            'peak_hour': "N/A",
            'most_popular_section': "N/A",
        }




# Function to fetch daily reservations
def get_daily_reservations(start_date, end_date, selected_section, min_guest_count, max_guest_count):
    session = SessionLocal()
    try:
        base_query = """
        SELECT r.date AS Date, COUNT(r.id) AS Reservations
        FROM reservations r
        LEFT JOIN tables t ON r.table_id = t.id
        LEFT JOIN sections s ON t.section_id = s.id
        WHERE r.date BETWEEN :start_date AND :end_date
        AND r.status = 'confirmed'
        """

        # Add filters for section and guest count
        filters = []
        if selected_section != "All Sections":
            filters.append("s.name = :selected_section")
        filters.append("r.guest_count BETWEEN :min_guest_count AND :max_guest_count")
        if filters:
            base_query += " AND " + " AND ".join(filters)

        base_query += " GROUP BY r.date ORDER BY r.date"

        params = {
            'start_date': start_date,
            'end_date': end_date,
            'selected_section': selected_section,
            'min_guest_count': min_guest_count,
            'max_guest_count': max_guest_count,
        }

        result = execute_prepared_statement(base_query, params)
        daily_counts = result.fetchall()

        # Convert to DataFrame
        daily_data = pd.DataFrame(daily_counts, columns=['Date', 'Reservations'])
        daily_data['Date'] = pd.to_datetime(daily_data['Date'])
        return daily_data
    except Exception as e:
        st.error(f"Error fetching daily reservations: {str(e)}")
        return pd.DataFrame(columns=['Date', 'Reservations'])
    finally:
        session.close()



def get_party_size_distribution(start_date, end_date, selected_section, min_guest_count, max_guest_count):
    session = SessionLocal()
    try:
        base_query = """
        SELECT
            CASE
                WHEN r.guest_count BETWEEN 1 AND 2 THEN '1-2 guests'
                WHEN r.guest_count BETWEEN 3 AND 4 THEN '3-4 guests'
                WHEN r.guest_count BETWEEN 5 AND 6 THEN '5-6 guests'
                ELSE '7+ guests'
            END AS Party_Size,
            COUNT(r.id) AS Count
        FROM reservations r
        LEFT JOIN tables t ON r.table_id = t.id
        LEFT JOIN sections s ON t.section_id = s.id
        WHERE r.date BETWEEN :start_date AND :end_date
        AND r.status = 'confirmed'
        """

        # Add filters for section and guest count
        filters = []
        if selected_section != "All Sections":
            filters.append("s.name = :selected_section")
        filters.append("r.guest_count BETWEEN :min_guest_count AND :max_guest_count")
        if filters:
            base_query += " AND " + " AND ".join(filters)

        base_query += " GROUP BY Party_Size"

        params = {
            'start_date': start_date,
            'end_date': end_date,
            'selected_section': selected_section,
            'min_guest_count': min_guest_count,
            'max_guest_count': max_guest_count,
        }

        result = execute_prepared_statement(base_query, params)
        party_size_counts = result.fetchall()

        # Convert to DataFrame
        party_sizes = pd.DataFrame(party_size_counts, columns=['Party_Size', 'Count'])
        return party_sizes
    except Exception as e:
        st.error(f"Error fetching party size distribution: {str(e)}")
        return pd.DataFrame(columns=['Party_Size', 'Count'])
    finally:
        session.close()


# Function to fetch section utilization
def get_section_utilization(start_date, end_date, selected_section, min_guest_count, max_guest_count):
    session = SessionLocal()
    try:
        base_query = """
        SELECT s.name AS Section, COUNT(r.id) AS Utilization
        FROM reservations r
        LEFT JOIN tables t ON r.table_id = t.id
        LEFT JOIN sections s ON t.section_id = s.id
        WHERE r.date BETWEEN :start_date AND :end_date
        AND r.status = 'confirmed'
        """

        # Add filters for guest count
        filters = []
        if selected_section != "All Sections":
            filters.append("s.name = :selected_section")
        filters.append("r.guest_count BETWEEN :min_guest_count AND :max_guest_count")
        if filters:
            base_query += " AND " + " AND ".join(filters)

        base_query += " GROUP BY s.name"

        params = {
            'start_date': start_date,
            'end_date': end_date,
            'selected_section': selected_section,
            'min_guest_count': min_guest_count,
            'max_guest_count': max_guest_count,
        }

        result = execute_prepared_statement(base_query, params)
        section_counts = result.fetchall()

        # Convert to DataFrame
        section_data = pd.DataFrame(section_counts, columns=['Section', 'Utilization'])
        return section_data
    except Exception as e:
        st.error(f"Error fetching section utilization: {str(e)}")
        return pd.DataFrame(columns=['Section', 'Utilization'])
    finally:
        session.close()



# Main function to display analytics
def show_analytics_page():
    st.title("Reservation Analytics")

    # Expandable filters section
    with st.expander("Filters", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("From Date", value=pd.to_datetime('2024-01-01'))
            min_guest_count = st.number_input("Min Guest Count", min_value=1, max_value=20, value=1)
        with col2:
            end_date = st.date_input("To Date", value=pd.to_datetime('2024-03-31'))
            max_guest_count = st.number_input("Max Guest Count", min_value=1, max_value=20, value=20)

        # Additional filters
        sections = ["All Sections", "Main Floor", "Patio", "Private Room"]
        selected_section = st.selectbox("Select Section", sections)

    # Fetch key metrics with the applied filters
    metrics = fetch_key_metrics(start_date, end_date, selected_section, min_guest_count, max_guest_count)

    # Display key metrics
    st.subheader("Key Metrics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Reservations", metrics['total_reservations'])
        st.metric("Average Party Size", f"{metrics['avg_party_size']:.1f} guests")
    with col2:
        st.metric("Peak Hour", metrics['peak_hour'])
        st.metric("Most Popular Section", metrics['most_popular_section'])
    with col3:
        st.metric("Most Busy day", metrics['most_busy_day'])

    # Daily Reservations Chart
    daily_data = get_daily_reservations(start_date, end_date, selected_section, min_guest_count, max_guest_count)
    st.subheader("Reservation Trends")
    tab1, tab2 = st.tabs(["Daily Reservations", "Party Size Distribution"])
    daily_data['Reservations'] += np.random.uniform(-0.2, 0.2, size=len(daily_data))

    # Daily Reservations Chart
    with tab1:
        st.line_chart(daily_data.set_index('Date')['Reservations'])

    # Party Size Distribution Chart
    party_sizes = get_party_size_distribution(start_date, end_date, selected_section, min_guest_count, max_guest_count)
    with tab2:
        st.bar_chart(party_sizes.set_index('Party_Size'))

    # Section Utilization Chart
    section_data = get_section_utilization(start_date, end_date, selected_section, min_guest_count, max_guest_count)
    st.subheader("Section Utilization")
    st.bar_chart(section_data.set_index('Section'))

def main():
    st.title("Restaurant Reservation System")
    
    # Initialize database if needed
    if not os.path.exists(DB_PATH):
        init_db()
    
    tab1, tab2, tab3 = st.tabs(["Make Reservation", "View Reservations", "Analytics Report"])
    
    with tab1:
        # Store the reservation state
        if 'reservation_state' not in st.session_state:
            st.session_state.reservation_state = 'entering_details'
            st.session_state.available_tables = None
            st.session_state.selected_table = None

        if st.session_state.reservation_state == 'entering_details':
            with st.form("reservation_form"):
                st.subheader("Customer Information")
                col1, col2 = st.columns(2)
                with col1:
                    customer_name = st.text_input("Name")
                    customer_email = st.text_input("Email")
                with col2:
                    customer_phone = st.text_input("Phone")
                    guest_count = st.number_input("Number of Guests", min_value=1, max_value=20)

                st.subheader("Reservation Details")
                col3, col4 = st.columns(2)
                with col3:
                    date = st.date_input("Date", min_value=datetime.today())
                with col4:
                    time = st.time_input("Time")

                check_availability = st.form_submit_button("Check Availability")

                if check_availability:
                    if not all([customer_name, customer_email, customer_phone]):
                        st.error("Please fill in all customer details.")
                    else:
                        available_tables = get_available_tables(date, time, guest_count)
                        if available_tables:
                            st.session_state.available_tables = available_tables
                            st.session_state.reservation_details = {
                                'customer_name': customer_name,
                                'customer_email': customer_email,
                                'customer_phone': customer_phone,
                                'date': date,
                                'time': time,
                                'guest_count': guest_count
                            }
                            st.session_state.reservation_state = 'selecting_table'
                            st.rerun()
                        else:
                            st.error("No tables available for this time and party size.")

        elif st.session_state.reservation_state == 'selecting_table':
            # Display reservation details
            st.subheader("Reservation Details")
            details = st.session_state.reservation_details
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"Name: {details['customer_name']}")
                st.write(f"Email: {details['customer_email']}")
                st.write(f"Phone: {details['customer_phone']}")
            with col2:
                st.write(f"Date: {details['date']}")
                st.write(f"Time: {details['time']}")
                st.write(f"Guests: {details['guest_count']}")

            # Table selection form
            with st.form("table_selection_form"):
                table_options = {f"Table {t.number} (Capacity: {t.capacity})": t.id 
                               for t in st.session_state.available_tables}
                selected_table = st.selectbox("Select Table", options=list(table_options.keys()))
                
                confirm_reservation = st.form_submit_button("Confirm Reservation")
                
                if confirm_reservation:
                    table_id = table_options[selected_table]
                    success, message = create_reservation(
                        customer_data={
                            'name': details['customer_name'],
                            'email': details['customer_email'],
                            'phone': details['customer_phone']
                        },
                        reservation_data={
                            'date': details['date'],
                            'time': details['time'],
                            'table_id': table_id,
                            'guest_count': details['guest_count']
                        }
                    )
                    if success:
                        st.success(message)
                        # Reset the reservation state
                        st.session_state.reservation_state = 'entering_details'
                        st.session_state.available_tables = None
                        st.rerun()
                    else:
                        st.error(f"Error: {message}")

            # Add a back button outside the form
            if st.button("Back to Details"):
                st.session_state.reservation_state = 'entering_details'
                st.rerun()
    
    with tab2:
        st.subheader("Current Reservations")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("↻ Refresh"):
                st.session_state.reservations = get_current_reservations()
        
        if 'reservations' not in st.session_state:
            st.session_state.reservations = get_current_reservations()
        
        if not st.session_state.reservations.empty:
            # Configure column display
            column_config = {
                "id": st.column_config.NumberColumn(
                    "ID",
                    width="small",
                ),
                "date": st.column_config.TextColumn(
                    "Date",
                    width="medium",
                ),
                "time": st.column_config.TextColumn(
                    "Time",
                    width="small",
                ),
                "customer_name": st.column_config.TextColumn(
                    "Customer",
                    width="medium",
                ),
                "customer_email": st.column_config.TextColumn(  # Added email column
                    "Email",
                    width="medium",
                ),
                "phone": st.column_config.TextColumn(
                    "Phone",
                    width="medium",
                ),
                "table_number": st.column_config.NumberColumn(
                    "Table",
                    width="small",
                ),
                "guest_count": st.column_config.NumberColumn(
                    "Guests",
                    width="small",
                ),
                "status": st.column_config.TextColumn(
                    "Status",
                    width="small",
                ),
            }
            
            # Display dataframe with selection enabled
            event = st.dataframe(
                st.session_state.reservations,
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
            )

            # Handle selection
            if event.selection and event.selection.rows:
                selected_row = event.selection.rows[0]
                selected_reservation = st.session_state.reservations.iloc[selected_row]
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Edit", key="edit_button"):
                        # Initialize edit state
                        st.session_state.edit_state = 'entering_details'
                        st.session_state.editing_reservation = selected_reservation
                with col2:
                    if st.button("Delete", key="delete_button"):
                        success, message = delete_reservation(selected_reservation['id'])
                        if success:
                            st.success(message)
                            st.session_state.reservations = get_current_reservations()
                            st.rerun()
                        else:
                            st.error(message)

                # Show edit form when edit is clicked
                if 'edit_state' in st.session_state:
                    if st.session_state.edit_state == 'entering_details':
                        with st.form(key="edit_form"):
                            st.subheader("Edit Reservation")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                customer_name = st.text_input("Name", value=selected_reservation['customer_name'])
                                customer_email = st.text_input("Email", value=selected_reservation['customer_email'])
                            with col2:
                                customer_phone = st.text_input("Phone", value=selected_reservation['phone'])
                                guest_count = st.number_input("Number of Guests", 
                                                            min_value=1, 
                                                            max_value=20, 
                                                            value=selected_reservation['guest_count'])

                            st.subheader("Reservation Details")
                            col3, col4 = st.columns(2)
                            with col3:
                                # Get the default date from the reservation
                                default_date = pd.to_datetime(selected_reservation['date']).date()

                                # Ensure the default date is within the allowed range
                                min_date = datetime.today().date()
                                if default_date < min_date:
                                    default_date = min_date

                                # Add the date input
                                date = st.date_input(
                                    "Date",
                                    value=default_date,
                                    min_value=min_date
                                )
                            with col4:
                                time = st.time_input("Time", 
                                                value=pd.to_datetime(selected_reservation['time']).time())

                            check_availability = st.form_submit_button("Check Availability")

                            if check_availability:
                                if not all([customer_name, customer_email, customer_phone]):
                                    st.error("Please fill in all customer details.")
                                else:
                                    available_tables = get_available_tables(date, time, guest_count)
                                    if available_tables:
                                        st.session_state.available_tables = available_tables
                                        st.session_state.edit_details = {
                                            'customer_name': customer_name,
                                            'customer_email': customer_email,
                                            'customer_phone': customer_phone,
                                            'date': date,
                                            'time': time,
                                            'guest_count': guest_count
                                        }
                                        st.session_state.edit_state = 'selecting_table'
                                        st.rerun()
                                    else:
                                        st.error("No tables available for this time and party size.")

                    elif st.session_state.edit_state == 'selecting_table':
                        # Display reservation details
                        st.subheader("Edit Reservation Details")
                        details = st.session_state.edit_details
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"Name: {details['customer_name']}")
                            st.write(f"Email: {details['customer_email']}")
                            st.write(f"Phone: {details['customer_phone']}")
                        with col2:
                            st.write(f"Date: {details['date']}")
                            st.write(f"Time: {details['time']}")
                            st.write(f"Guests: {details['guest_count']}")

                        # Table selection form
                        with st.form("table_selection_form"):
                            table_options = {f"Table {t.number} (Capacity: {t.capacity})": t.id 
                                        for t in st.session_state.available_tables}
                            selected_table = st.selectbox("Select Table", options=list(table_options.keys()))
                            
                            confirm_update = st.form_submit_button("Update Reservation")  # Changed variable name
                            
                            if confirm_update:  # Changed variable name
                                table_id = table_options[selected_table]
                                update_data = {
                                    'date': details['date'],
                                    'time': details['time'],
                                    'guest_count': details['guest_count'],
                                    'table_id': table_id,
                                    'customer_name': details['customer_name'],
                                    'customer_email': details['customer_email'],
                                    'customer_phone': details['customer_phone']
                                }
                                success, message = update_reservation(selected_reservation['id'], update_data)  # Function call remains the same
                                if success:
                                    st.success(message)
                                    # Reset edit state
                                    if 'edit_state' in st.session_state:
                                        del st.session_state.edit_state
                                    if 'edit_details' in st.session_state:
                                        del st.session_state.edit_details
                                    if 'available_tables' in st.session_state:
                                        del st.session_state.available_tables
                                    st.session_state.reservations = get_current_reservations()
                                    st.rerun()
                                else:
                                    st.error(message)

                        # Add a back button outside the form
                        if st.button("Back to Details"):
                            st.session_state.edit_state = 'entering_details'
                            st.rerun()
        else:
            st.info("No current reservations found.")
    
    with tab3:
        show_analytics_page()

if __name__ == "__main__":
    main()