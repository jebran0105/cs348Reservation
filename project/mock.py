import streamlit as st
import pandas as pd
from sqlalchemy import func
from datetime import datetime

def fetch_key_metrics(start_date, end_date):
    session = SessionLocal()
    try:
        # Convert start and end dates to datetime objects
        start_date = datetime.strptime(str(start_date), "%Y-%m-%d")
        end_date = datetime.strptime(str(end_date), "%Y-%m-%d")

        # Total Reservations
        total_reservations = session.query(func.count(Reservation.id)).filter(
            Reservation.date >= start_date, Reservation.date <= end_date
        ).scalar()

        # Average Party Size
        avg_party_size = session.query(func.avg(Reservation.guest_count)).filter(
            Reservation.date >= start_date, Reservation.date <= end_date
        ).scalar()
        avg_party_size = round(avg_party_size, 1) if avg_party_size else 0

        # Table Utilization
        total_tables = session.query(func.count(Table.id)).scalar()
        reserved_tables_count = session.query(func.count(Reservation.id.distinct())).filter(
            Reservation.date >= start_date, Reservation.date <= end_date
        ).scalar()
        table_utilization = (reserved_tables_count / total_tables * 100) if total_tables > 0 else 0

        return {
            'total_reservations': total_reservations,
            'avg_party_size': avg_party_size,
            'table_utilization': round(table_utilization, 1)
        }
    except Exception as e:
        st.error(f"Error fetching key metrics: {str(e)}")
        return {
            'total_reservations': 0,
            'avg_party_size': 0.0,
            'table_utilization': 0.0
        }
    finally:
        session.close()


def show_analytics_page():
    st.title("Reservation Analytics")

    # Create sidebar for filters
    st.sidebar.header("Filters")

    # Date Range Filter
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("From Date", value=pd.to_datetime('2024-01-01'))
    with col2:
        end_date = st.date_input("To Date", value=pd.to_datetime('2024-03-31'))

    # Section Filter
    sections = ['All Sections', 'Main Floor', 'Patio', 'Private Room']
    selected_section = st.sidebar.selectbox("Select Section", sections)

    # Table Filter
    tables = ['All Tables', 'Table 1', 'Table 2', 'Table 3', 'Table 4', 'Table 5', 'Table 6']
    selected_table = st.sidebar.selectbox("Select Table", tables)

    # Party Size Range
    size_ranges = ['All Sizes', '1-2 guests', '3-4 guests', '5+ guests']
    selected_size = st.sidebar.selectbox("Party Size", size_ranges)

    # Fetch key metrics from the database
    metrics = fetch_key_metrics(start_date, end_date)

    # Display metrics in a dashboard layout
    st.subheader("Key Metrics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Reservations", metrics['total_reservations'])
        st.metric("Average Party Size", f"{metrics['avg_party_size']:.1f} guests")
    with col2:
        st.metric("Peak Hour", "TBD")  # We'll calculate this next
        st.metric("Most Popular Section", "TBD")  # We'll calculate this next
    with col3:
        st.metric("Table Utilization", f"{metrics['table_utilization']}%")
        st.metric("Average Duration", "TBD mins")  # Placeholder for now

    # Note: The placeholders ("TBD") for Peak Hour, Most Popular Section, and Average Duration
    # will be replaced once we write queries to fetch these specific details.

    # Sample daily reservation data for now (replace this with real data fetching logic)
    daily_data = pd.DataFrame({
        'Date': pd.date_range(start='2024-01-01', end='2024-03-31', freq='D'),
        'Reservations': [0] * 91,  # Replace with actual reservation counts
        'Avg_Party_Size': [0] * 91  # Replace with actual average party sizes
    })

    # Charts
    st.subheader("Reservation Trends")
    tab1, tab2 = st.tabs(["Daily Reservations", "Party Size Distribution"])
    
    with tab1:
        # Line chart for daily reservations
        st.line_chart(daily_data.set_index('Date')['Reservations'])
        
    with tab2:
        # Bar chart for party size distribution
        party_sizes = pd.DataFrame({
            'Party_Size': ['1-2', '3-4', '5-6', '7+'],
            'Count': [0, 0, 0, 0]  # Replace with actual counts
        })
        st.bar_chart(party_sizes.set_index('Party_Size'))

    # Section utilization (replace with real data)
    section_data = pd.DataFrame({
        'Section': ['Main Floor', 'Patio', 'Private Room'],
        'Utilization': [0, 0, 0]  # Replace with actual utilization percentages
    })
    st.bar_chart(section_data.set_index('Section'))

    # Detailed reservation data (replace with real data)
    detailed_data = pd.DataFrame({
        'Date': pd.date_range(start='2024-01-01', end='2024-01-10'),
        'Total_Reservations': [0] * 10,  # Replace with actual data
        'Avg_Party_Size': [0] * 10,  # Replace with actual data
        'Most_Popular_Table': ['Table 1'] * 10,  # Replace with actual data
        'Peak_Hour': ['6 PM'] * 10  # Replace with actual data
    })
    st.dataframe(detailed_data, use_container_width=True)

    # Download report button
    if st.button("Download Report"):
        st.success("Report downloaded! (This is a mockup)")

# Add this to your existing tabs in main()
tab1, tab2, tab3 = st.tabs(["Make Reservation", "View Reservations", "Analytics"])
with tab3:
    show_analytics_page()