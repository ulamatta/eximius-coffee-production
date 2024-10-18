import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from datetime import date, timedelta
from streamlit_lottie import st_lottie
import requests

# Configure Streamlit page
st.set_page_config(
    page_title="☕ Eximius Coffee Production KPI",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Function to load Lottie animations
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# Load Lottie animation
lottie_coffee = load_lottieurl("https://assets10.lottiefiles.com/packages/lf20_jcikwtux.json")
if lottie_coffee:
    st_lottie(lottie_coffee, height=150, key="coffee")

# Centered Title with Emoji
st.markdown(
    """
    <h1 style='text-align: center; color: #4B8BBE;'>
        ☕ Eximius Coffee Production KPI Dashboard
    </h1>
    """,
    unsafe_allow_html=True
)

# Setup database connection
@st.cache_resource
def init_connection():
    engine = create_engine(st.secrets["databases"]["postgres_url"])
    return engine

engine = init_connection()

# Fetch distinct machine names and customers based on date range
def fetch_distinct_values(start_date, end_date):
    query = """
    SELECT DISTINCT machine.machine_name, sku.customer
    FROM daily_production dp
    JOIN sku ON dp.sku_id = sku.id
    JOIN machine ON dp.machine_id = machine.id
    WHERE dp.date BETWEEN %(start_date)s AND %(end_date)s
    ORDER BY machine.machine_name, sku.customer
    """
    with engine.connect() as connection:
        df = pd.read_sql_query(query, connection, params={'start_date': start_date, 'end_date': end_date})
    machine_names = sorted(df['machine_name'].dropna().unique())
    customers = sorted(df['customer'].dropna().unique())
    return machine_names, customers

# Fetch production data with proper connection management and dynamic filters
def fetch_production_data(start_date, end_date, machine=None, customer=None):
    base_query = """
    SELECT 
        dp.date, dp.schedulded_cases, dp.produced_cases, 
        dp.shift_start, dp.shift_end, sku.customer,
        sku.sku_of_product, sku.arabica, sku.robusta, sku.brazil,
        machine.machine_name
    FROM daily_production dp
    JOIN sku ON dp.sku_id = sku.id
    JOIN machine ON dp.machine_id = machine.id
    WHERE dp.date BETWEEN %(start_date)s AND %(end_date)s
    """
    filters = []
    params = {'start_date': start_date, 'end_date': end_date}
    
    if machine and machine != "All":
        filters.append("machine.machine_name = %(machine)s")
        params['machine'] = machine
    
    if customer and customer != "All":
        filters.append("sku.customer = %(customer)s")
        params['customer'] = customer
    
    if filters:
        base_query += " AND " + " AND ".join(filters)
    
    base_query += " ORDER BY dp.date, machine.machine_name"
    
    with engine.connect() as connection:
        df = pd.read_sql_query(base_query, connection, params=params)
    
    # Convert numeric columns to appropriate types
    numeric_columns = ['schedulded_cases', 'produced_cases', 'arabica', 'robusta', 'brazil']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Optionally remove leading zeroes from 'sku_of_product' if not part of identifier
    # Uncomment the following line if needed
    # df['sku_of_product'] = df['sku_of_product'].astype(str).str.lstrip('0')
    
    return df

# Sidebar filters
with st.sidebar:
    st.header("🔍 Filter Options")
    
    # Date Filter Options
    date_filter = st.selectbox(
        "📅 Select Date Range",
        options=["Last 7 Days", "Last 30 Days", "This Month", "Custom Range"]
    )
    
    today = date.today()
    
    if date_filter == "Last 7 Days":
        start_selected = today - timedelta(days=7)
        end_selected = today
    elif date_filter == "Last 30 Days":
        start_selected = today - timedelta(days=30)
        end_selected = today
    elif date_filter == "This Month":
        start_selected = today.replace(day=1)
        end_selected = today
    else:
        selected_dates = st.date_input(
            "📅 Select Custom Date Range", 
            value=(today - timedelta(days=30), today),
            min_value=today - timedelta(days=365),
            max_value=today,
        )
        if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
            start_selected, end_selected = selected_dates
        else:
            start_selected = today - timedelta(days=30)
            end_selected = today
    
    # Fetch distinct machine names and customers based on selected date range
    machine_options, customer_options = fetch_distinct_values(start_selected, end_selected)

    # Machine and Customer Filters
    machine_filter = st.selectbox("🖥️ Filter by Machine Name", ["All"] + machine_options)
    customer_filter = st.selectbox("🏷️ Filter by Customer", ["All"] + customer_options)

    # Option to Reset Filters
    if st.button("🔄 Reset Filters"):
        date_filter = "Last 30 Days"
        start_selected = today - timedelta(days=30)
        end_selected = today
        machine_filter = "All"
        customer_filter = "All"

# Fetch filtered data
data = fetch_production_data(
    start_selected, 
    end_selected,
    machine=machine_filter,
    customer=customer_filter
)

# Calculate Metrics
if not data.empty:
    total_produced = data["produced_cases"].sum()
    total_scheduled = data["schedulded_cases"].sum()

    # Calculate coffee usage
    data["total_arabica"] = data["produced_cases"] * data["arabica"]
    data["total_robusta"] = data["produced_cases"] * data["robusta"]
    data["total_brazil"] = data["produced_cases"] * data["brazil"]
    total_arabica = data["total_arabica"].sum()
    total_robusta = data["total_robusta"].sum()
    total_brazil = data["total_brazil"].sum()
    total_coffee = total_arabica + total_robusta + total_brazil

    # KPIs Section
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 🎯 Key Performance Indicators", unsafe_allow_html=True)
    
    # First Row of KPIs
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("📦 Total Produced Cases", f"{int(total_produced):,}")
    kpi2.metric("📋 Total Scheduled Cases", f"{int(total_scheduled):,}")
    kpi3.metric("☕ Total Coffee Used (lbs)", f"{int(total_coffee):,}")

    # Second Row of KPIs
    kpi4, kpi5, kpi6 = st.columns(3)
    kpi4.metric("🌱 Total Arabica Used (lbs)", f"{int(total_arabica):,}")
    kpi5.metric("🌰 Total Robusta Used (lbs)", f"{int(total_robusta):,}")
    kpi6.metric("🇧🇷 Total Brazil Used (lbs)", f"{int(total_brazil):,}")

    # Additional KPI for Machines Involved
    kpi7, = st.columns(1)
    kpi7.metric("🖥️ Machines Involved", f"{data['machine_name'].nunique()}")

    # Charts Section
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 📊 Production Performance", unsafe_allow_html=True)
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        produced_scheduled = data.groupby('date')[['produced_cases', 'schedulded_cases']].sum()
        st.bar_chart(produced_scheduled, height=300, use_container_width=True)
        st.caption("📈 Produced vs Scheduled Cases Over Time")

    with chart_col2:
        coffee_usage = data.groupby('date')[['total_arabica', 'total_robusta', 'total_brazil']].sum()
        st.line_chart(coffee_usage, height=300, use_container_width=True)
        st.caption("☕ Coffee Usage Over Time")

    # Machine Utilization
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 🖥️ Machine Utilization", unsafe_allow_html=True)
    machine_util = data.groupby('machine_name')['produced_cases'].sum().reset_index()
    machine_util_chart = machine_util.set_index('machine_name')
    st.bar_chart(machine_util_chart, height=300, use_container_width=True)
    st.caption("🔧 Produced Cases by Machine")

    # Customer Contribution
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 🏆 Customer Production Summary", unsafe_allow_html=True)
    customer_summary = data.groupby('customer')['produced_cases'].sum().reset_index()
    customer_summary_chart = customer_summary.set_index('customer')
    st.bar_chart(customer_summary_chart, height=300, use_container_width=True)
    st.caption("👥 Produced Cases by Customer")

    # Download Data Section
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 📥 Download Data", unsafe_allow_html=True)
    csv = data.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📄 Download Data as CSV",
        data=csv,
        file_name='production_data.csv',
        mime='text/csv',
    )

    # Expandable Raw Data Section (Optional)
    with st.expander("📋 View Raw Data", expanded=False):
        # Define formatters for numeric columns to remove leading zeroes
        format_dict = {
            "produced_cases": "{:,}",
            "schedulded_cases": "{:,}",
            "arabica": "{:,.2f}",
            "robusta": "{:,.2f}",
            "brazil": "{:,.2f}",
            "total_arabica": "{:,}",
            "total_robusta": "{:,}",
            "total_brazil": "{:,}",
        }
        st.dataframe(data.style.format(format_dict))
else:
    st.warning("⚠️ No data available for the selected filters.")
