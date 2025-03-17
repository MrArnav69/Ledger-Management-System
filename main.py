import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import uuid
import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
import tempfile
import threading
from tkinter import Tk, filedialog
from pathlib import Path
import base64
import re
import io
import subprocess
subprocess.run(["pip", "run", "pandas numpy datetime plotly tempfile threading pathlib"])

using_firebase = False

# Set page configuration
st.set_page_config(
    page_title="Ledger Management System",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Firebase configuration
firebaseConfig = {
    "apiKey": "AIzaSyC8QHJTmgtol1PE44BT2AyfQR31rXtzEAE",
    "authDomain": "ledger-application.firebaseapp.com",
    "databaseURL": "https://ledger-application-default-rtdb.firebaseio.com",
    "projectId": "ledger-application",
    "storageBucket": "ledger-application.firebasestorage.app",
    "messagingSenderId": "241611587874",
    "appId": "1:241611587874:web:15280b2c161f83a903657b"
}

# Initialize Firebase
if st.session_state.get('enable_firebase', False) and firebaseConfig["apiKey"] != "YOUR_API_KEY":
    try:
        import pyrebase
        firebase = pyrebase.initialize_app(firebaseConfig)
        db = firebase.database()
        using_firebase = True
    except ImportError:
        st.sidebar.error("Could not import pyrebase. Using local storage.")
        using_firebase = False

# Initialize session state variables
# Initialize session state for storing variables
if 'settings' not in st.session_state:
    st.session_state.settings = {
        "theme": "light",
        "auto_backup": True,
        "auto_calculate_balance": True,
        "date_format": "%Y-%m-%d",
        "currency_symbol": "₹",  # Make sure this is set
        "notification_enabled": True,
        "auto_save_interval": 5
    }
else:
    # Ensure currency_symbol exists in settings
    if "currency_symbol" not in st.session_state.settings:
        st.session_state.settings["currency_symbol"] = "₹"




if 'current_customer' not in st.session_state:
    st.session_state.current_customer = None
if 'current_supplier' not in st.session_state:
    st.session_state.current_supplier = None
if 'edit_customer' not in st.session_state:
    st.session_state.edit_customer = None
if 'edit_supplier' not in st.session_state:
    st.session_state.edit_supplier = None
if 'edit_transaction' not in st.session_state:
    st.session_state.edit_transaction = None
if 'confirm_delete_customer' not in st.session_state:
    st.session_state.confirm_delete_customer = None
if 'confirm_delete_supplier' not in st.session_state:
    st.session_state.confirm_delete_supplier = None
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

# File paths for local storage
DATA_DIR = "data"
CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers.json")
SUPPLIERS_FILE = os.path.join(DATA_DIR, "suppliers.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
CUSTOMER_TRANSACTIONS_DIR = os.path.join(DATA_DIR, "customer_transactions")
SUPPLIER_TRANSACTIONS_DIR = os.path.join(DATA_DIR, "supplier_transactions")

# Create data directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CUSTOMER_TRANSACTIONS_DIR, exist_ok=True)
os.makedirs(SUPPLIER_TRANSACTIONS_DIR, exist_ok=True)

# Apply theme
# Fix for the light theme optimization
def apply_theme():
    theme = st.session_state.settings["theme"]
    if theme == "dark":
        # Dark theme
        st.markdown("""
        <style>
        .stApp, .stTabs, .main {
            background-color: #1E1E1E;
            color: #FFFFFF;
        }
        .stButton>button {
            background-color: #4CAF50;
            color: white;
            border-radius: 5px;
        }
        .stTextInput>div>div>input, .stSelectbox>div>div>div, .stNumberInput>div>div>input {
            background-color: #333333;
            color: white;
        }
        .css-1d391kg {
            background-color: #333333;
        }
        .stDataFrame {
            background-color: #2D2D2D;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        # Light theme - improved
        st.markdown("""
        <style>
        .stApp, .stTabs, .main {
            background-color: #FFFFFF;
            color: #000000;
        }
        .stButton>button {
            background-color: #4CAF50;
            color: white;
            border-radius: 5px;
        }
        .stDataFrame {
            background-color: #F0F2F6;
        }
        .metric-card {
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            border-radius: 8px;
        }
        .stTextInput>div>div>input, .stSelectbox>div>div>div, .stNumberInput>div>div>input {
            border: 1px solid #E0E0E0;
            border-radius: 4px;
        }
        .stForm {
            background-color: #F9F9F9;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #E0E0E0;
        }
        </style>
        """, unsafe_allow_html=True)


apply_theme()

# Custom CSS for layout
st.markdown("""
<style>
.card {
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}
.metric-card {
    text-align: center;
    padding: 15px;
    border-radius: 8px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}
.metric-value {
    font-size: 28px;
    font-weight: bold;
}
.metric-label {
    font-size: 16px;
    color: #666;
}
.success-message {
    padding: 10px;
    background-color: #E8F5E9;
    border-left: 5px solid #4CAF50;
    margin-bottom: 10px;
}
.warning-message {
    padding: 10px;
    background-color: #FFF8E1;
    border-left: 5px solid #FFC107;
    margin-bottom: 10px;
}
.error-message {
    padding: 10px;
    background-color: #FFEBEE;
    border-left: 5px solid #F44336;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# Function to save Excel file using tkinter dialog
# Fix for the Excel export on Mac
def save_excel_file(dataframe, default_filename="ledger_export.xlsx"):
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
        # Save the dataframe to the temporary file
        dataframe.to_excel(tmp.name, index=False, engine='openpyxl')
        temp_filename = tmp.name
    
    # Create a download button instead of using tkinter
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        dataframe.to_excel(writer, index=False)
    
    buffer.seek(0)
    
    # Create a download button
    st.download_button(
        label="Download Excel file",
        data=buffer,
        file_name=default_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # Clean up the temporary file
    try:
        os.unlink(temp_filename)
    except:
        pass
    
    return True


# Format currency
def format_currency(amount):
    currency_symbol = st.session_state.settings["currency_symbol"]
    return f"{currency_symbol}{amount:,.2f}"

# Format date
def format_date(date_str):
    try:
        date_format = st.session_state.settings["date_format"]
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime(date_format)
    except:
        return date_str

# Helper function to construct transaction date string with separators
# Fix for the date formatting function
def format_date_input(date_str):
    if not date_str:
        return ""
    
    # Remove any existing dashes or slashes
    clean_date = date_str.replace("-", "").replace("/", "")
    
    # Format as YYYY-MM-DD
    if len(clean_date) >= 8:
        return f"{clean_date[:4]}-{clean_date[4:6]}-{clean_date[6:8]}"
    elif len(clean_date) >= 6:
        return f"{clean_date[:4]}-{clean_date[4:6]}-"  # Add dash after month
    elif len(clean_date) >= 4:
        return f"{clean_date[:4]}-"  # Add dash after year
    else:
        return clean_date



# Validate date format
# Fix for the validate_date function (it was incomplete in the original code)
def validate_date(date_str):
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, date_str):
        return False
    
    try:
        datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


# Firebase data functions
# Fix for the db not defined error in load_settings function
def load_settings():
    if using_firebase:
        try:
            settings = db.child("settings").get().val()
            if not settings:
                # Default settings
                settings = {
                    "theme": "light",
                    "auto_backup": True,
                    "auto_calculate_balance": True,
                    "date_format": "%Y-%m-%d",
                    "currency_symbol": "₹",
                    "notification_enabled": True,
                    "auto_save_interval": 5,
                    "auto_date_format": True
                }
                db.child("settings").set(settings)
            else:
                # Ensure all required keys exist
                required_keys = {
                    "theme": "light",
                    "auto_backup": True,
                    "auto_calculate_balance": True,
                    "date_format": "%Y-%m-%d",
                    "currency_symbol": "₹",
                    "notification_enabled": True,
                    "auto_save_interval": 5,
                    "auto_date_format": True
                }
                for key, default_value in required_keys.items():
                    if key not in settings:
                        settings[key] = default_value
            
            return settings
        except Exception as e:
            st.error(f"Error loading settings from Firebase: {e}")
    
    # Fallback to local storage
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                
                # Ensure all required keys exist
                required_keys = {
                    "theme": "light",
                    "auto_backup": True,
                    "auto_calculate_balance": True,
                    "date_format": "%Y-%m-%d",
                    "currency_symbol": "₹",
                    "notification_enabled": True,
                    "auto_save_interval": 5,
                    "auto_date_format": True
                }
                for key, default_value in required_keys.items():
                    if key not in settings:
                        settings[key] = default_value
                
                return settings
    except Exception as e:
        st.error(f"Error loading settings from local storage: {e}")
    
    # Default settings if nothing else works
    return {
        "theme": "light",
        "auto_backup": True,
        "auto_calculate_balance": True,
        "date_format": "%Y-%m-%d",
        "currency_symbol": "₹",
        "notification_enabled": True,
        "auto_save_interval": 5,
        "auto_date_format": True
    }



def save_settings(settings_data):
    if using_firebase:
        try:
            db.child("settings").set(settings_data)
            return True
        except Exception as e:
            st.error(f"Error saving settings to Firebase: {e}")
    
    # Fallback to local storage
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings_data, f)
        return True
    except Exception as e:
        st.error(f"Error saving settings locally: {e}")
        return False

def load_customers():
    if using_firebase:
        try:
            customers = db.child("customers").get().val()
            if customers:
                return customers
            return {}
        except Exception as e:
            st.error(f"Error loading customers from Firebase: {e}")
    
    # Fallback to local storage
    if os.path.exists(CUSTOMERS_FILE):
        try:
            with open(CUSTOMERS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    
    return {}

def save_customer(customer_id, customer_data):
    if using_firebase:
        try:
            db.child("customers").child(customer_id).set(customer_data)
            return True
        except Exception as e:
            st.error(f"Error saving customer to Firebase: {e}")
    
    # Fallback to local storage
    try:
        customers = load_customers()
        customers[customer_id] = customer_data
        with open(CUSTOMERS_FILE, 'w') as f:
            json.dump(customers, f)
        return True
    except Exception as e:
        st.error(f"Error saving customer locally: {e}")
        return False

def delete_customer(customer_id):
    if using_firebase:
        try:
            db.child("customers").child(customer_id).remove()
            db.child("customer_transactions").child(customer_id).remove()
            return True
        except Exception as e:
            st.error(f"Error deleting customer from Firebase: {e}")
    
    # Fallback to local storage
    try:
        customers = load_customers()
        if customer_id in customers:
            del customers[customer_id]
            with open(CUSTOMERS_FILE, 'w') as f:
                json.dump(customers, f)
            
            # Delete transactions
            customer_trans_file = os.path.join(CUSTOMER_TRANSACTIONS_DIR, f"{customer_id}.json")
            if os.path.exists(customer_trans_file):
                os.remove(customer_trans_file)
            
            return True
    except Exception as e:
        st.error(f"Error deleting customer locally: {e}")
        return False

def load_suppliers():
    if using_firebase:
        try:
            suppliers = db.child("suppliers").get().val()
            if suppliers:
                return suppliers
            return {}
        except Exception as e:
            st.error(f"Error loading suppliers from Firebase: {e}")
    
    # Fallback to local storage
    if os.path.exists(SUPPLIERS_FILE):
        try:
            with open(SUPPLIERS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    
    return {}

def save_supplier(supplier_id, supplier_data):
    if using_firebase:
        try:
            db.child("suppliers").child(supplier_id).set(supplier_data)
            return True
        except Exception as e:
            st.error(f"Error saving supplier to Firebase: {e}")
    
    # Fallback to local storage
    try:
        suppliers = load_suppliers()
        suppliers[supplier_id] = supplier_data
        with open(SUPPLIERS_FILE, 'w') as f:
            json.dump(suppliers, f)
        return True
    except Exception as e:
        st.error(f"Error saving supplier locally: {e}")
        return False

def delete_supplier(supplier_id):
    if using_firebase:
        try:
            db.child("suppliers").child(supplier_id).remove()
            db.child("supplier_transactions").child(supplier_id).remove()
            return True
        except Exception as e:
            st.error(f"Error deleting supplier from Firebase: {e}")
    
    # Fallback to local storage
    try:
        suppliers = load_suppliers()
        if supplier_id in suppliers:
            del suppliers[supplier_id]
            with open(SUPPLIERS_FILE, 'w') as f:
                json.dump(suppliers, f)
            
            # Delete transactions
            supplier_trans_file = os.path.join(SUPPLIER_TRANSACTIONS_DIR, f"{supplier_id}.json")
            if os.path.exists(supplier_trans_file):
                os.remove(supplier_trans_file)
            
            return True
    except Exception as e:
        st.error(f"Error deleting supplier locally: {e}")
        return False

def load_transactions(entity_type, entity_id):
    if using_firebase:
        try:
            transactions = db.child(f"{entity_type}_transactions").child(entity_id).get().val()
            if transactions:
                return transactions
            return {}
        except Exception as e:
            st.error(f"Error loading transactions from Firebase: {e}")
    
    # Fallback to local storage
    trans_file = os.path.join(
        CUSTOMER_TRANSACTIONS_DIR if entity_type == "customer" else SUPPLIER_TRANSACTIONS_DIR,
        f"{entity_id}.json"
    )
    
    if os.path.exists(trans_file):
        try:
            with open(trans_file, 'r') as f:
                return json.load(f)
        except:
            pass
    
    return {}

def save_transaction(entity_type, entity_id, transaction_id, transaction_data):
    if using_firebase:
        try:
            db.child(f"{entity_type}_transactions").child(entity_id).child(transaction_id).set(transaction_data)
            return True
        except Exception as e:
            st.error(f"Error saving transaction to Firebase: {e}")
    
    # Fallback to local storage
    try:
        trans_file = os.path.join(
            CUSTOMER_TRANSACTIONS_DIR if entity_type == "customer" else SUPPLIER_TRANSACTIONS_DIR,
            f"{entity_id}.json"
        )
        
        transactions = {}
        if os.path.exists(trans_file):
            with open(trans_file, 'r') as f:
                transactions = json.load(f)
        
        transactions[transaction_id] = transaction_data
        
        with open(trans_file, 'w') as f:
            json.dump(transactions, f)
        
        return True
    except Exception as e:
        st.error(f"Error saving transaction locally: {e}")
        return False

def delete_transaction(entity_type, entity_id, transaction_id):
    if using_firebase:
        try:
            db.child(f"{entity_type}_transactions").child(entity_id).child(transaction_id).remove()
            return True
        except Exception as e:
            st.error(f"Error deleting transaction from Firebase: {e}")
    
    # Fallback to local storage
    try:
        trans_file = os.path.join(
            CUSTOMER_TRANSACTIONS_DIR if entity_type == "customer" else SUPPLIER_TRANSACTIONS_DIR,
            f"{entity_id}.json"
        )
        
        if os.path.exists(trans_file):
            with open(trans_file, 'r') as f:
                transactions = json.load(f)
            
            if transaction_id in transactions:
                del transactions[transaction_id]
                
                with open(trans_file, 'w') as f:
                    json.dump(transactions, f)
                
                return True
    except Exception as e:
        st.error(f"Error deleting transaction locally: {e}")
        return False

def calculate_balance(transactions_list):
    balance = 0
    for transaction in transactions_list:
        debit = float(transaction.get('debit', 0))
        credit = float(transaction.get('credit', 0))
        balance += credit - debit
    return balance

# Load settings at startup
st.session_state.settings = load_settings()

# Main app title
st.title("📒 Ledger Management System")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Customers", "Suppliers", "Settings"])

# Dashboard Tab
with tab1:
    st.header("Dashboard")
    
    # Load all data for dashboard
    all_customers = load_customers()
    all_suppliers = load_suppliers()
    
    # Calculate total receivables and payables
    total_receivable = 0
    total_payable = 0
    
    for customer_id, customer in all_customers.items():
        customer_transactions = load_transactions("customer", customer_id)
        if customer_transactions:
            customer_balance = calculate_balance(list(customer_transactions.values()))
            if customer_balance > 0:  # Positive balance means customer owes money (receivable)
                total_receivable += customer_balance
            else:  # Negative balance means we owe customer (payable)
                total_payable -= customer_balance
    
    for supplier_id, supplier in all_suppliers.items():
        supplier_transactions = load_transactions("supplier", supplier_id)
        if supplier_transactions:
            supplier_balance = calculate_balance(list(supplier_transactions.values()))
            if supplier_balance < 0:  # Negative balance means we owe supplier (payable)
                total_payable -= supplier_balance
            else:  # Positive balance means supplier owes us (receivable)
                total_receivable += supplier_balance
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="background-color: #E3F2FD;">
            <div class="metric-value">{format_currency(total_receivable)}</div>
            <div class="metric-label">You Get (Total Receivable)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="background-color: #FFEBEE;">
            <div class="metric-value">{format_currency(total_payable)}</div>
            <div class="metric-label">You Give (Total Payable)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        net_balance = total_receivable - total_payable
        background_color = "#E8F5E9" if net_balance >= 0 else "#FFEBEE"
        
        st.markdown(f"""
        <div class="metric-card" style="background-color: {background_color};">
            <div class="metric-value">{format_currency(net_balance)}</div>
            <div class="metric-label">Net Balance</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Display customer and supplier counts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="background-color: #F3E5F5;">
            <div class="metric-value">{len(all_customers)}</div>
            <div class="metric-label">Total Customers</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="background-color: #FFF3E0;">
            <div class="metric-value">{len(all_suppliers)}</div>
            <div class="metric-label">Total Suppliers</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Recent transactions
    st.subheader("Recent Transactions")
    
    # Combine all transactions
    all_transactions = []
    
    for customer_id, customer in all_customers.items():
        customer_transactions = load_transactions("customer", customer_id)
        if customer_transactions:
            for trans_id, transaction in customer_transactions.items():
                transaction['entity_name'] = customer.get('name', 'Unknown')
                transaction['entity_type'] = 'Customer'
                transaction['id'] = trans_id
                transaction['entity_id'] = customer_id
                all_transactions.append(transaction)
    
    for supplier_id, supplier in all_suppliers.items():
        supplier_transactions = load_transactions("supplier", supplier_id)
        if supplier_transactions:
            for trans_id, transaction in supplier_transactions.items():
                transaction['entity_name'] = supplier.get('name', 'Unknown')
                transaction['entity_type'] = 'Supplier'
                transaction['id'] = trans_id
                transaction['entity_id'] = supplier_id
                all_transactions.append(transaction)
    
    # Sort by date (most recent first)
    all_transactions.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    # Display recent transactions (top 10)
    if all_transactions:
        recent_transactions = all_transactions[:10]
        
        # Create DataFrame for display
        df_transactions = []
        
        for transaction in recent_transactions:
            debit = float(transaction.get('debit', 0))
            credit = float(transaction.get('credit', 0))
            
            df_transactions.append({
                "Date": format_date(transaction.get('date', '')),
                "Entity": f"{transaction.get('entity_name', '')} ({transaction.get('entity_type', '')})",
                "Particulars": transaction.get('particular', ''),
                "Debit": format_currency(debit) if debit > 0 else "",
                "Credit": format_currency(credit) if credit > 0 else ""
            })
        
        df = pd.DataFrame(df_transactions)
        st.dataframe(df, use_container_width=True)
        
        # Action for selected transaction
        if st.button("View Transaction Details", key="view_recent_trans"):
            if len(recent_transactions) > 0:
                selected_trans = recent_transactions[0]
                entity_type = selected_trans.get('entity_type', '').lower()
                entity_id = selected_trans.get('entity_id', '')
                
                if entity_type == 'customer':
                    st.session_state.current_customer = entity_id
                    st.rerun()
                elif entity_type == 'supplier':
                    st.session_state.current_supplier = entity_id
                    st.rerun()
    else:
        st.info("No transactions found. Add your first transaction in the Customers or Suppliers tab.")
    
    # Financial charts
    st.subheader("Financial Overview")
    
    # Prepare data for charts
    monthly_data = {}
    
    for transaction in all_transactions:
        try:
            date_parts = transaction.get('date', '').split('-')
            if len(date_parts) >= 2:
                year_month = f"{date_parts[0]}-{date_parts[1]}"
                
                if year_month not in monthly_data:
                    monthly_data[year_month] = {'debit': 0, 'credit': 0}
                
                debit = float(transaction.get('debit', 0))
                credit = float(transaction.get('credit', 0))
                
                monthly_data[year_month]['debit'] += debit
                monthly_data[year_month]['credit'] += credit
        except:
            pass
    
    # Create DataFrame for chart
    chart_data = []
    for month, values in monthly_data.items():
        chart_data.append({
            'Month': month,
            'Debit': values['debit'],
            'Credit': values['credit'],
            'Net': values['credit'] - values['debit']
        })
    
    chart_df = pd.DataFrame(chart_data)
    
    if not chart_df.empty:
        # Sort by month
        chart_df = chart_df.sort_values('Month')
        
        # Create charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Line chart for debit and credit
            fig = px.line(
                chart_df, 
                x='Month', 
                y=['Debit', 'Credit'],
                title='Monthly Debit and Credit',
                labels={'value': 'Amount', 'variable': 'Type'},
                color_discrete_map={'Debit': '#FF6B6B', 'Credit': '#4CAF50'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Bar chart for net balance
            fig = px.bar(
                chart_df,
                x='Month',
                y='Net',
                title='Monthly Net Balance',
                labels={'Net': 'Net Balance'},
                color='Net',
                color_continuous_scale=['#FF6B6B', '#FFFFFF', '#4CAF50'],
                color_continuous_midpoint=0
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Pie chart for receivables vs payables
        fig = px.pie(
            names=['Receivable', 'Payable'],
            values=[total_receivable, total_payable],
            title='Receivables vs Payables',
            color_discrete_sequence=['#4CAF50', '#FF6B6B']
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No transaction data available for charts.")

# Customers Tab
with tab2:
    st.header("Customers")
    
    # Add new customer form
    with st.expander("Add New Customer", expanded=False):
        with st.form("add_customer_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_name = st.text_input("Customer Name*")
                new_phone = st.text_input("Phone Number*")
            
            with col2:
                new_email = st.text_input("Email (Optional)")
                new_address = st.text_area("Address (Optional)")
            
            submitted = st.form_submit_button("Add Customer")
            if submitted:
                if not new_name or not new_phone:
                    st.error("Name and Phone Number are required!")
                else:
                    # Check if customer with same phone already exists
                    all_customers = load_customers()
                    exists = False
                    for customer in all_customers.values():
                        if customer.get('phone') == new_phone:
                            exists = True
                            break
                    
                    if exists:
                        st.error(f"Customer with phone number {new_phone} already exists!")
                    else:
                        customer_id = str(uuid.uuid4())
                        customer_data = {
                            'name': new_name,
                            'phone': new_phone,
                            'email': new_email,
                            'address': new_address,
                            'created_on': datetime.datetime.now().strftime('%Y-%m-%d')
                        }
                        
                        if save_customer(customer_id, customer_data):
                            st.success(f"Customer {new_name} added successfully!")
                            # Clear form fields by rerunning
                            st.rerun()
    
    # Search and filter customers
    all_customers = load_customers()
    
    if not all_customers:
        st.info("No customers found. Add your first customer using the form above.")
    else:
        # Search box
        search_query = st.text_input("Search customers by name or phone", "")
        
        # Filter customers based on search query
        filtered_customers = {}
        for customer_id, customer in all_customers.items():
            if (search_query.lower() in customer.get('name', '').lower() or 
                search_query in customer.get('phone', '')):
                filtered_customers[customer_id] = customer
        
        # Display customers in a table
        if filtered_customers:
            # Prepare data for display
            customer_data = []
            
            for customer_id, customer in filtered_customers.items():
                # Load transactions for this customer
                transactions = load_transactions("customer", customer_id)
                # Calculate balance
                balance = 0
                if transactions:
                    balance = calculate_balance(list(transactions.values()))
                
                # Add to display data
                customer_data.append({
                    "ID": customer_id,
                    "Name": customer.get('name', ''),
                    "Phone": customer.get('phone', ''),
                    "Balance": format_currency(balance),
                    "Status": "Due" if balance > 0 else "Advance" if balance < 0 else "Settled"
                })
            
            # Create DataFrame
            df = pd.DataFrame(customer_data)
            
            # Display table
            st.dataframe(df.set_index("ID"), use_container_width=True)
            
            # Customer selection for detailed view
            selected_customer_id = st.selectbox(
                "Select customer to view details",
                options=list(filtered_customers.keys()),
                format_func=lambda x: filtered_customers[x].get('name', 'Unknown'),
                key="customer_select"
            )
            
            if selected_customer_id:
                st.session_state.current_customer = selected_customer_id
        else:
            st.info("No customers match your search criteria.")
    
    # Display customer profile and ledger
    if st.session_state.current_customer:
        customer_id = st.session_state.current_customer
        customer = all_customers.get(customer_id, {})
        
        if customer:
            # Customer profile section
            st.subheader(f"Customer Profile: {customer.get('name', 'Unknown')}")
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**Phone:** {customer.get('phone', 'N/A')}")
                st.write(f"**Email:** {customer.get('email', 'N/A')}")
                st.write(f"**Address:** {customer.get('address', 'N/A')}")
                st.write(f"**Customer since:** {format_date(customer.get('created_on', 'N/A'))}")
            
            with col2:
                # Load transactions
                transactions = load_transactions("customer", customer_id)
                
                # Calculate balance
                balance = 0
                if transactions:
                    balance = calculate_balance(list(transactions.values()))
                
                # Display balance
                balance_color = "#F44336" if balance > 0 else "#4CAF50" if balance < 0 else "#FFC107"
                st.markdown(f"""
                <div style="background-color: {balance_color}; color: white; padding: 10px; border-radius: 5px; text-align: center;">
                    <h3 style="margin: 0;">Balance: {format_currency(balance)}</h3>
                    <p style="margin: 0;">Status: {"Due" if balance > 0 else "Advance" if balance < 0 else "Settled"}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                # Action buttons
                if st.button("Edit Customer", key=f"edit_customer_{customer_id}"):
                    st.session_state.edit_customer = customer_id
                
                if st.button("Delete Customer", key=f"delete_customer_{customer_id}"):
                    st.session_state.confirm_delete_customer = customer_id
            
            # Edit customer form
            if st.session_state.edit_customer == customer_id:
                with st.form(f"edit_customer_form_{customer_id}"):
                    st.subheader("Edit Customer")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        edit_name = st.text_input("Customer Name*", value=customer.get('name', ''))
                        edit_phone = st.text_input("Phone Number*", value=customer.get('phone', ''))
                    
                    with col2:
                        edit_email = st.text_input("Email", value=customer.get('email', ''))
                        edit_address = st.text_area("Address", value=customer.get('address', ''))
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        update_submitted = st.form_submit_button("Update Customer")
                    
                    with col2:
                        cancel = st.form_submit_button("Cancel")
                    
                    if update_submitted:
                        if not edit_name or not edit_phone:
                            st.error("Name and Phone Number are required!")
                        else:
                            # Check if phone number is already used by another customer
                            phone_exists = False
                            for cid, cust in all_customers.items():
                                if cid != customer_id and cust.get('phone') == edit_phone:
                                    phone_exists = True
                                    break
                            
                            if phone_exists:
                                st.error(f"Phone number {edit_phone} is already used by another customer!")
                            else:
                                # Update customer data
                                updated_customer = {
                                    'name': edit_name,
                                    'phone': edit_phone,
                                    'email': edit_email,
                                    'address': edit_address,
                                    'created_on': customer.get('created_on', datetime.datetime.now().strftime('%Y-%m-%d'))
                                }
                                
                                if save_customer(customer_id, updated_customer):
                                    st.success("Customer updated successfully!")
                                    st.session_state.edit_customer = None
                                    st.rerun()
                    
                    if cancel:
                        st.session_state.edit_customer = None
                        st.rerun()
            
            # Confirm delete dialog
            if st.session_state.confirm_delete_customer == customer_id:
                st.warning(f"Are you sure you want to delete customer '{customer.get('name', 'Unknown')}'? This will also delete all transactions.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Yes, Delete", key=f"confirm_delete_customer_{customer_id}"):
                        if delete_customer(customer_id):
                            st.success("Customer deleted successfully!")
                            st.session_state.confirm_delete_customer = None
                            st.session_state.current_customer = None
                            st.rerun()
                
                with col2:
                    if st.button("Cancel", key=f"cancel_delete_customer_{customer_id}"):
                        st.session_state.confirm_delete_customer = None
                        st.rerun()
            
            # Customer ledger section
            st.subheader("Ledger Book")
            
            # Add new transaction
            with st.expander("Add New Transaction", expanded=False):
                with st.form(f"add_customer_transaction_form_{customer_id}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        date_input = st.text_input(
                            "Date (YYYY-MM-DD)*", 
                            value=datetime.datetime.now().strftime('%Y-%m-%d'),
                            help="Format: YYYY-MM-DD",
                            key="customer_date_input"
                        )
                        
                        # Format date as user types if auto-format is enabled
                        if st.session_state.settings.get("auto_date_format", True):
                            date_input = format_date_input(date_input)
                        
                        particular = st.text_area(
                            "Particulars*", 
                            help="Description of the transaction",
                            key="customer_particular"
                        )
                    
                    with col2:
                        debit = st.number_input(
                            "Debit Amount", 
                            min_value=0.0, 
                            format="%.2f",
                            help="Amount to be added to customer's account (customer gives money)",
                            key="customer_debit"
                        )
                        
                        credit = st.number_input(
                            "Credit Amount", 
                            min_value=0.0, 
                            format="%.2f",
                            help="Amount to be subtracted from customer's account (customer takes money/goods)",
                            key="customer_credit"
                        )
                    
                    transaction_submitted = st.form_submit_button("Add Transaction")
                    
                    if transaction_submitted:
                        if not validate_date(date_input):
                            st.error("Please enter a valid date in YYYY-MM-DD format!")
                        elif not particular:
                            st.error("Particulars are required!")
                        elif debit == 0 and credit == 0:
                            st.error("Either Debit or Credit amount must be greater than zero!")
                        else:
                            transaction_id = str(uuid.uuid4())
                            transaction_data = {
                                'date': date_input,
                                'particular': particular,
                                'debit': str(debit),
                                'credit': str(credit)
                            }
                            
                            if save_transaction("customer", customer_id, transaction_id, transaction_data):
                                st.success("Transaction added successfully!")
                                st.rerun()
            
            # Display transactions
            transactions = load_transactions("customer", customer_id)
            
            if not transactions:
                st.info("No transactions recorded yet.")
            else:
                # Convert to list and sort by date
                transactions_list = list(transactions.values())
                for t in transactions_list:
                    t['id'] = next((k for k, v in transactions.items() if v == t), None)
                
                transactions_list.sort(key=lambda x: x.get('date', ''))
                
                # Create DataFrame for display
                df_transactions = []
                running_balance = 0
                total_debit = 0
                total_credit = 0
                
                for transaction in transactions_list:
                    debit = float(transaction.get('debit', 0))
                    credit = float(transaction.get('credit', 0))
                    running_balance += debit - credit
                    total_debit += debit
                    total_credit += credit
                    
                    df_transactions.append({
                        "ID": transaction.get('id', ''),
                        "Date": format_date(transaction.get('date', '')),
                        "Particulars": transaction.get('particular', ''),
                        "Debit": format_currency(debit) if debit > 0 else "",
                        "Credit": format_currency(credit) if credit > 0 else "",
                        "Balance": format_currency(running_balance)
                    })
                
                # Add totals row
                df_transactions.append({
                    "ID": "",
                    "Date": "",
                    "Particulars": "TOTAL",
                    "Debit": format_currency(total_debit),
                    "Credit": format_currency(total_credit),
                    "Balance": format_currency(running_balance)
                })
                
                df = pd.DataFrame(df_transactions)
                st.dataframe(df.set_index("ID"), use_container_width=True)
                
                # Export to Excel
                if st.button("Export Ledger to Excel", key=f"export_customer_{customer_id}"):
                    # Create a more detailed DataFrame for export
                    export_df = pd.DataFrame([
                        {
                            "Date": t.get('date', ''),
                            "Particulars": t.get('particular', ''),
                            "Debit": float(t.get('debit', 0)),
                            "Credit": float(t.get('credit', 0))
                        } for t in transactions_list
                    ])
                    
                    # Calculate running balance
                    balance = 0
                    balances = []
                    for _, row in export_df.iterrows():
                        balance += row['Debit'] - row['Credit']
                        balances.append(balance)
                    
                    export_df['Balance'] = balances
                    
                    # Add totals row
                    export_df.loc[len(export_df)] = [
                        "", "TOTAL", 
                        export_df['Debit'].sum(), 
                        export_df['Credit'].sum(), 
                        balance
                    ]
                    
                    # Add customer information at the top
                    customer_info = pd.DataFrame({
                        'Customer Information': ['Name:', 'Phone:', 'Email:', 'Address:', 'Created On:'],
                        'Value': [
                            customer.get('name', ''),
                            customer.get('phone', ''),
                            customer.get('email', ''),
                            customer.get('address', ''),
                            customer.get('created_on', '')
                        ]
                    })
                    
                    # Save to Excel using tkinter dialog
                    filename = f"customer_ledger_{customer.get('name', 'unknown').replace(' ', '_')}.xlsx"
                    if save_excel_file(export_df, filename):
                        st.success("Ledger exported successfully!")
                
                # Transaction actions
                st.subheader("Transaction Actions")
                
                selected_transaction_id = st.selectbox(
                    "Select transaction",
                    options=[t.get('id', '') for t in transactions_list if t.get('id', '')],
                    format_func=lambda x: next((f"{t.get('date', '')} - {t.get('particular', '')}" for t in transactions_list if t.get('id', '') == x), ""),
                    key="customer_transaction_select"
                )
                
                if selected_transaction_id:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("Edit Transaction", key=f"edit_customer_trans_{selected_transaction_id}"):
                            st.session_state.edit_transaction = {
                                'id': selected_transaction_id,
                                'entity_type': 'customer',
                                'entity_id': customer_id
                            }
                    
                    with col2:
                        if st.button("Delete Transaction", key=f"delete_customer_trans_{selected_transaction_id}"):
                            if delete_transaction("customer", customer_id, selected_transaction_id):
                                st.success("Transaction deleted successfully!")
                                st.rerun()
            
            # Edit transaction form
            if (st.session_state.edit_transaction and 
                st.session_state.edit_transaction['entity_type'] == 'customer' and 
                st.session_state.edit_transaction['entity_id'] == customer_id):
                
                transaction_id = st.session_state.edit_transaction['id']
                transaction = transactions.get(transaction_id, {})
                
                if transaction:
                    with st.form(f"edit_customer_transaction_form_{transaction_id}"):
                        st.subheader("Edit Transaction")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            edit_date = st.text_input(
                                "Date (YYYY-MM-DD)*", 
                                value=transaction.get('date', ''),
                                help="Format: YYYY-MM-DD",
                                key="edit_customer_date"
                            )
                            
                            # Format date as user types if auto-format is enabled
                            # Format date as user types if auto-format is enabled
                            if st.session_state.settings.get("auto_date_format", True):
                                edit_date = format_date_input(edit_date)
                            
                            edit_particular = st.text_area(
                                "Particulars*", 
                                value=transaction.get('particular', ''),
                                help="Description of the transaction",
                                key="edit_customer_particular"
                            )
                        
                        with col2:
                            edit_debit = st.number_input(
                                "Debit Amount", 
                                min_value=0.0, 
                                value=float(transaction.get('debit', 0)),
                                format="%.2f",
                                help="Amount to be added to customer's account (customer gives money)",
                                key="edit_customer_debit"
                            )
                            
                            edit_credit = st.number_input(
                                "Credit Amount", 
                                min_value=0.0, 
                                value=float(transaction.get('credit', 0)),
                                format="%.2f",
                                help="Amount to be subtracted from customer's account (customer takes money/goods)",
                                key="edit_customer_credit"
                            )
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            update_trans_submitted = st.form_submit_button("Update Transaction")
                        
                        with col2:
                            cancel_trans = st.form_submit_button("Cancel")
                        
                        if update_trans_submitted:
                            if not validate_date(edit_date):
                                st.error("Please enter a valid date in YYYY-MM-DD format!")
                            elif not edit_particular:
                                st.error("Particulars are required!")
                            elif edit_debit == 0 and edit_credit == 0:
                                st.error("Either Debit or Credit amount must be greater than zero!")
                            else:
                                updated_transaction = {
                                    'date': edit_date,
                                    'particular': edit_particular,
                                    'debit': str(edit_debit),
                                    'credit': str(edit_credit)
                                }
                                
                                if save_transaction("customer", customer_id, transaction_id, updated_transaction):
                                    st.success("Transaction updated successfully!")
                                    st.session_state.edit_transaction = None
                                    st.rerun()
                        
                        if cancel_trans:
                            st.session_state.edit_transaction = None
                            st.rerun()

# Suppliers Tab
with tab3:
    st.header("Suppliers")
    
    # Add new supplier form
    with st.expander("Add New Supplier", expanded=False):
        with st.form("add_supplier_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_name = st.text_input("Supplier Name*", key="supplier_name")
                new_phone = st.text_input("Phone Number*", key="supplier_phone")
            
            with col2:
                new_email = st.text_input("Email (Optional)", key="supplier_email")
                new_address = st.text_area("Address (Optional)", key="supplier_address")
            
            submitted = st.form_submit_button("Add Supplier")
            if submitted:
                if not new_name or not new_phone:
                    st.error("Name and Phone Number are required!")
                else:
                    # Check if supplier with same phone already exists
                    all_suppliers = load_suppliers()
                    exists = False
                    for supplier in all_suppliers.values():
                        if supplier.get('phone') == new_phone:
                            exists = True
                            break
                    
                    if exists:
                        st.error(f"Supplier with phone number {new_phone} already exists!")
                    else:
                        supplier_id = str(uuid.uuid4())
                        supplier_data = {
                            'name': new_name,
                            'phone': new_phone,
                            'email': new_email,
                            'address': new_address,
                            'created_on': datetime.datetime.now().strftime('%Y-%m-%d')
                        }
                        
                        if save_supplier(supplier_id, supplier_data):
                            st.success(f"Supplier {new_name} added successfully!")
                            # Clear form fields by rerunning
                            st.rerun()
    
    # Search and filter suppliers
    all_suppliers = load_suppliers()
    
    if not all_suppliers:
        st.info("No suppliers found. Add your first supplier using the form above.")
    else:
        # Search box
        search_query = st.text_input("Search suppliers by name or phone", "", key="supplier_search")
        
        # Filter suppliers based on search query
        filtered_suppliers = {}
        for supplier_id, supplier in all_suppliers.items():
            if (search_query.lower() in supplier.get('name', '').lower() or 
                search_query in supplier.get('phone', '')):
                filtered_suppliers[supplier_id] = supplier
        
        # Display suppliers in a table
        if filtered_suppliers:
            # Prepare data for display
            supplier_data = []
            
            for supplier_id, supplier in filtered_suppliers.items():
                # Load transactions for this supplier
                transactions = load_transactions("supplier", supplier_id)
                
                # Calculate balance
                balance = 0
                if transactions:
                    balance = calculate_balance(list(transactions.values()))
                
                # Add to display data
                supplier_data.append({
                    "ID": supplier_id,
                    "Name": supplier.get('name', ''),
                    "Phone": supplier.get('phone', ''),
                    "Balance": format_currency(balance),
                    "Status": "Due" if balance < 0 else "Advance" if balance > 0 else "Settled"
                })
            
            # Create DataFrame
            df = pd.DataFrame(supplier_data)
            
            # Display table
            st.dataframe(df.set_index("ID"), use_container_width=True)
            
            # Supplier selection for detailed view
            selected_supplier_id = st.selectbox(
                "Select supplier to view details",
                options=list(filtered_suppliers.keys()),
                format_func=lambda x: filtered_suppliers[x].get('name', 'Unknown'),
                key="supplier_select"
            )
            
            if selected_supplier_id:
                st.session_state.current_supplier = selected_supplier_id
        else:
            st.info("No suppliers match your search criteria.")
    
    # Display supplier profile and ledger
    if st.session_state.current_supplier:
        supplier_id = st.session_state.current_supplier
        supplier = all_suppliers.get(supplier_id, {})
        
        if supplier:
            # Supplier profile section
            st.subheader(f"Supplier Profile: {supplier.get('name', 'Unknown')}")
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**Phone:** {supplier.get('phone', 'N/A')}")
                st.write(f"**Email:** {supplier.get('email', 'N/A')}")
                st.write(f"**Address:** {supplier.get('address', 'N/A')}")
                st.write(f"**Supplier since:** {format_date(supplier.get('created_on', 'N/A'))}")
            
            with col2:
                # Load transactions
                transactions = load_transactions("supplier", supplier_id)
                
                # Calculate balance
                balance = 0
                if transactions:
                    balance = calculate_balance(list(transactions.values()))
                
                # Display balance
                balance_color = "#F44336" if balance < 0 else "#4CAF50" if balance > 0 else "#FFC107"
                st.markdown(f"""
                <div style="background-color: {balance_color}; color: white; padding: 10px; border-radius: 5px; text-align: center;">
                    <h3 style="margin: 0;">Balance: {format_currency(balance)}</h3>
                    <p style="margin: 0;">Status: {"Due" if balance < 0 else "Advance" if balance > 0 else "Settled"}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                # Action buttons
                if st.button("Edit Supplier", key=f"edit_supplier_{supplier_id}"):
                    st.session_state.edit_supplier = supplier_id
                
                if st.button("Delete Supplier", key=f"delete_supplier_{supplier_id}"):
                    st.session_state.confirm_delete_supplier = supplier_id
            
            # Edit supplier form
            if st.session_state.edit_supplier == supplier_id:
                with st.form(f"edit_supplier_form_{supplier_id}"):
                    st.subheader("Edit Supplier")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        edit_name = st.text_input("Supplier Name*", value=supplier.get('name', ''))
                        edit_phone = st.text_input("Phone Number*", value=supplier.get('phone', ''))
                    
                    with col2:
                        edit_email = st.text_input("Email", value=supplier.get('email', ''))
                        edit_address = st.text_area("Address", value=supplier.get('address', ''))
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        update_submitted = st.form_submit_button("Update Supplier")
                    
                    with col2:
                        cancel = st.form_submit_button("Cancel")
                    
                    if update_submitted:
                        if not edit_name or not edit_phone:
                            st.error("Name and Phone Number are required!")
                        else:
                            # Check if phone number is already used by another supplier
                            phone_exists = False
                            for sid, supp in all_suppliers.items():
                                if sid != supplier_id and supp.get('phone') == edit_phone:
                                    phone_exists = True
                                    break
                            
                            if phone_exists:
                                st.error(f"Phone number {edit_phone} is already used by another supplier!")
                            else:
                                # Update supplier data
                                updated_supplier = {
                                    'name': edit_name,
                                    'phone': edit_phone,
                                    'email': edit_email,
                                    'address': edit_address,
                                    'created_on': supplier.get('created_on', datetime.datetime.now().strftime('%Y-%m-%d'))
                                }
                                
                                if save_supplier(supplier_id, updated_supplier):
                                    st.success("Supplier updated successfully!")
                                    st.session_state.edit_supplier = None
                                    st.rerun()
                    
                    if cancel:
                        st.session_state.edit_supplier = None
                        st.rerun()
            
            # Confirm delete dialog
            if st.session_state.confirm_delete_supplier == supplier_id:
                st.warning(f"Are you sure you want to delete supplier '{supplier.get('name', 'Unknown')}'? This will also delete all transactions.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Yes, Delete", key=f"confirm_delete_supplier_{supplier_id}"):
                        if delete_supplier(supplier_id):
                            st.success("Supplier deleted successfully!")
                            st.session_state.confirm_delete_supplier = None
                            st.session_state.current_supplier = None
                            st.rerun()
                
                with col2:
                    if st.button("Cancel", key=f"cancel_delete_supplier_{supplier_id}"):
                        st.session_state.confirm_delete_supplier = None
                        st.rerun()
            
            # Supplier ledger section
            st.subheader("Ledger Book")
            
            # Add new transaction
            with st.expander("Add New Transaction", expanded=False):
                with st.form(f"add_supplier_transaction_form_{supplier_id}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        date_input = st.text_input(
                            "Date (YYYY-MM-DD)*", 
                            value=datetime.datetime.now().strftime('%Y-%m-%d'),
                            help="Format: YYYY-MM-DD",
                            key="supplier_date_input"
                        )
                        
                        # Format date as user types if auto-format is enabled
                        if st.session_state.settings.get("auto_date_format", True):
                            date_input = format_date_input(date_input)
                        
                        particular = st.text_area(
                            "Particulars*", 
                            help="Description of the transaction",
                            key="supplier_particular"
                        )
                    
                    with col2:
                        debit = st.number_input(
                            "Debit Amount", 
                            min_value=0.0, 
                            format="%.2f",
                            help="Amount to be added to supplier's account (you give money to supplier)",
                            key="supplier_debit"
                        )
                        
                        credit = st.number_input(
                            "Credit Amount", 
                            min_value=0.0, 
                            format="%.2f",
                            help="Amount to be subtracted from supplier's account (you get goods/money from supplier)",
                            key="supplier_credit"
                        )
                    
                    transaction_submitted = st.form_submit_button("Add Transaction")
                    
                    if transaction_submitted:
                        if not validate_date(date_input):
                            st.error("Please enter a valid date in YYYY-MM-DD format!")
                        elif not particular:
                            st.error("Particulars are required!")
                        elif debit == 0 and credit == 0:
                            st.error("Either Debit or Credit amount must be greater than zero!")
                        else:
                            transaction_id = str(uuid.uuid4())
                            transaction_data = {
                                'date': date_input,
                                'particular': particular,
                                'debit': str(debit),
                                'credit': str(credit)
                            }
                            
                            if save_transaction("supplier", supplier_id, transaction_id, transaction_data):
                                st.success("Transaction added successfully!")
                                st.rerun()
            
            # Display transactions
            transactions = load_transactions("supplier", supplier_id)
            
            if not transactions:
                st.info("No transactions recorded yet.")
            else:
                # Convert to list and sort by date
                transactions_list = list(transactions.values())
                for t in transactions_list:
                    t['id'] = next((k for k, v in transactions.items() if v == t), None)
                
                transactions_list.sort(key=lambda x: x.get('date', ''))
                
                # Create DataFrame for display
                df_transactions = []
                running_balance = 0
                total_debit = 0
                total_credit = 0
                
                for transaction in transactions_list:
                    debit = float(transaction.get('debit', 0))
                    credit = float(transaction.get('credit', 0))
                    running_balance += credit - debit  # For suppliers, credit increases balance, debit decreases
                    total_debit += debit
                    total_credit += credit
                    
                    df_transactions.append({
                        "ID": transaction.get('id', ''),
                        "Date": format_date(transaction.get('date', '')),
                        "Particulars": transaction.get('particular', ''),
                        "Debit": format_currency(debit) if debit > 0 else "",
                        "Credit": format_currency(credit) if credit > 0 else "",
                        "Balance": format_currency(running_balance)
                    })
                
                # Add totals row
                df_transactions.append({
                    "ID": "",
                    "Date": "",
                    "Particulars": "TOTAL",
                    "Debit": format_currency(total_debit),
                    "Credit": format_currency(total_credit),
                    "Balance": format_currency(running_balance)
                })
                
                df = pd.DataFrame(df_transactions)
                st.dataframe(df.set_index("ID"), use_container_width=True)
                
                # Export to Excel
                if st.button("Export Ledger to Excel", key=f"export_supplier_{supplier_id}"):
                    # Create a more detailed DataFrame for export
                    export_df = pd.DataFrame([
                        {
                            "Date": t.get('date', ''),
                            "Particulars": t.get('particular', ''),
                            "Debit": float(t.get('debit', 0)),
                            "Credit": float(t.get('credit', 0))
                        } for t in transactions_list
                    ])
                    
                    # Calculate running balance
                    balance = 0
                    balances = []
                    for _, row in export_df.iterrows():
                        balance += row['Credit'] - row['Debit']  # For suppliers
                        balances.append(balance)
                    
                    export_df['Balance'] = balances
                    
                    # Add totals row
                    export_df.loc[len(export_df)] = [
                        "", "TOTAL", 
                        export_df['Debit'].sum(), 
                        export_df['Credit'].sum(), 
                        balance
                    ]
                    
                    # Add supplier information at the top
                    supplier_info = pd.DataFrame({
                        'Supplier Information': ['Name:', 'Phone:', 'Email:', 'Address:', 'Created On:'],
                        'Value': [
                            supplier.get('name', ''),
                            supplier.get('phone', ''),
                            supplier.get('email', ''),
                            supplier.get('address', ''),
                            supplier.get('created_on', '')
                        ]
                    })
                    
                    # Save to Excel using tkinter dialog
                    filename = f"supplier_ledger_{supplier.get('name', 'unknown').replace(' ', '_')}.xlsx"
                    if save_excel_file(export_df, filename):
                        st.success("Ledger exported successfully!")
                
                # Transaction actions
                st.subheader("Transaction Actions")
                
                selected_transaction_id = st.selectbox(
                    "Select transaction",
                    options=[t.get('id', '') for t in transactions_list if t.get('id', '')],
                    format_func=lambda x: next((f"{t.get('date', '')} - {t.get('particular', '')}" for t in transactions_list if t.get('id', '') == x), ""),
                    key="supplier_transaction_select"
                )
                
                if selected_transaction_id:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("Edit Transaction", key=f"edit_supplier_trans_{selected_transaction_id}"):
                            st.session_state.edit_transaction = {
                                'id': selected_transaction_id,
                                'entity_type': 'supplier',
                                'entity_id': supplier_id
                            }
                    
                    with col2:
                        if st.button("Delete Transaction", key=f"delete_supplier_trans_{selected_transaction_id}"):
                            if delete_transaction("supplier", supplier_id, selected_transaction_id):
                                st.success("Transaction deleted successfully!")
                                st.rerun()
            
            # Edit transaction form
            if (st.session_state.edit_transaction and 
                st.session_state.edit_transaction['entity_type'] == 'supplier' and 
                st.session_state.edit_transaction['entity_id'] == supplier_id):
                
                transaction_id = st.session_state.edit_transaction['id']
                transaction = transactions.get(transaction_id, {})
                
                if transaction:
                    with st.form(f"edit_supplier_transaction_form_{transaction_id}"):
                        st.subheader("Edit Transaction")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            edit_date = st.text_input(
                                "Date (YYYY-MM-DD)*", 
                                value=transaction.get('date', ''),
                                help="Format: YYYY-MM-DD",
                                key="edit_supplier_date"
                            )
                            
                            # Format date as user types if auto-format is enabled
                            if st.session_state.settings.get("auto_date_format", True):
                                edit_date = format_date_input(edit_date)
                            
                            edit_particular = st.text_area(
                                "Particulars*", 
                                value=transaction.get('particular', ''),
                                help="Description of the transaction",
                                key="edit_supplier_particular"
                            )
                        
                        with col2:
                            edit_debit = st.number_input(
                                "Debit Amount", 
                                min_value=0.0, 
                                value=float(transaction.get('debit', 0)),
                                format="%.2f",
                                help="Amount to be added to supplier's account (you give money to supplier)",
                                key="edit_supplier_debit"
                            )
                            
                            edit_credit = st.number_input(
                                "Credit Amount", 
                                min_value=0.0, 
                                value=float(transaction.get('credit', 0)),
                                format="%.2f",
                                help="Amount to be subtracted from supplier's account (you get goods/money from supplier)",
                                key="edit_supplier_credit"
                            )
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            update_trans_submitted = st.form_submit_button("Update Transaction")
                        
                        with col2:
                            cancel_trans = st.form_submit_button("Cancel")
                        
                        if update_trans_submitted:
                            if not validate_date(edit_date):
                                st.error("Please enter a valid date in YYYY-MM-DD format!")
                            elif not edit_particular:
                                st.error("Particulars are required!")
                            elif edit_debit == 0 and edit_credit == 0:
                                st.error("Either Debit or Credit amount must be greater than zero!")
                            else:
                                updated_transaction = {
                                    'date': edit_date,
                                    'particular': edit_particular,
                                    'debit': str(edit_debit),
                                    'credit': str(edit_credit)
                                }
                                
                                if save_transaction("supplier", supplier_id, transaction_id, updated_transaction):
                                    st.success("Transaction updated successfully!")
                                    st.session_state.edit_transaction = None
                                    st.rerun()
                        
                        if cancel_trans:
                            st.session_state.edit_transaction = None
                            st.rerun()

# Settings Tab
with tab4:
    st.header("Settings")
    
    # Create tabs for different settings categories
    settings_tab1, settings_tab2, settings_tab3 = st.tabs(["General", "Appearance", "Data Management"])
    
    # General Settings
    with settings_tab1:
        st.subheader("General Settings")
        
        with st.form("general_settings_form"):
            currency_symbol = st.text_input(
                "Currency Symbol", 
                value=st.session_state.settings.get("currency_symbol", "₹"),
                help="Symbol to use for currency display"
            )
            
            date_format_options = {
                "%Y-%m-%d": "YYYY-MM-DD (e.g., 2023-01-31)",
                "%d/%m/%Y": "DD/MM/YYYY (e.g., 31/01/2023)",
                "%m/%d/%Y": "MM/DD/YYYY (e.g., 01/31/2023)",
                "%d-%m-%Y": "DD-MM-YYYY (e.g., 31-01-2023)",
                "%d %b %Y": "DD MMM YYYY (e.g., 31 Jan 2023)"
            }
            
            date_format = st.selectbox(
                "Date Display Format",
                options=list(date_format_options.keys()),
                format_func=lambda x: date_format_options[x],
                index=list(date_format_options.keys()).index(
                    st.session_state.settings.get("date_format", "%Y-%m-%d")
                )
            )
            
            auto_date_format = st.checkbox(
                "Auto-format dates while typing",
                value=st.session_state.settings.get("auto_date_format", True),
                help="Automatically add separators while typing dates"
            )
            
            auto_calculate_balance = st.checkbox(
                "Auto-calculate balance",
                value=st.session_state.settings.get("auto_calculate_balance", True),
                help="Automatically calculate running balance for transactions"
            )
            
            notification_enabled = st.checkbox(
                "Enable notifications",
                value=st.session_state.settings.get("notification_enabled", True),
                help="Show success/error notifications"
            )
            
            submitted = st.form_submit_button("Save General Settings")
            
            if submitted:
                # Update settings
                st.session_state.settings.update({
                    "currency_symbol": currency_symbol,
                    "date_format": date_format,
                    "auto_date_format": auto_date_format,
                    "auto_calculate_balance": auto_calculate_balance,
                    "notification_enabled": notification_enabled
                })
                
                # Save to storage
                if save_settings(st.session_state.settings):
                    st.success("General settings saved successfully!")
    
    # Appearance Settings
    with settings_tab2:
        st.subheader("Appearance Settings")
        
        with st.form("appearance_settings_form"):
            theme = st.radio(
                "Application Theme",
                options=["light", "dark"],
                index=0 if st.session_state.settings.get("theme", "light") == "light" else 1,
                help="Choose between light and dark theme"
            )
            
            submitted = st.form_submit_button("Save Appearance Settings")
            
            if submitted:
                # Update settings
                st.session_state.settings["theme"] = theme
                
                # Save to storage
                if save_settings(st.session_state.settings):
                    st.success("Appearance settings saved successfully!")
                    # Apply theme immediately
                    apply_theme()
                    st.rerun()
    
    # Data Management Settings
    with settings_tab3:
        st.subheader("Data Management")
        
        # Backup data
        st.write("### Backup Data")
        st.write("Create a backup of all your data that you can restore later.")
        
        if st.button("Create Backup"):
            try:
                # Load all data
                all_customers = load_customers()
                all_suppliers = load_suppliers()
                
                # Create backup data structure
                backup_data = {
                    "customers": all_customers,
                    "suppliers": all_suppliers,
                    "settings": st.session_state.settings,
                    "customer_transactions": {},
                    "supplier_transactions": {}
                }
                
                # Add transactions
                for customer_id in all_customers:
                    backup_data["customer_transactions"][customer_id] = load_transactions("customer", customer_id)
                
                for supplier_id in all_suppliers:
                    backup_data["supplier_transactions"][supplier_id] = load_transactions("supplier", supplier_id)
                
                # Convert to JSON
                backup_json = json.dumps(backup_data, indent=2)
                
                # Create download link
                b64 = base64.b64encode(backup_json.encode()).decode()
                filename = f"ledger_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                href = f'<a href="data:application/json;base64,{b64}" download="{filename}">Download Backup File</a>'
                
                st.markdown(href, unsafe_allow_html=True)
                st.success("Backup created successfully! Click the link above to download.")
            except Exception as e:
                st.error(f"Error creating backup: {e}")
        
        # Restore data
        st.write("### Restore Data")
        st.write("Restore data from a previously created backup file.")
        st.warning("This will overwrite your current data. Make sure to create a backup first.")
        
        uploaded_file = st.file_uploader("Upload backup file", type=["json"])
        
        if uploaded_file is not None:
            if st.button("Restore Data"):
                try:
                    # Load backup data
                    backup_data = json.loads(uploaded_file.getvalue().decode())
                    
                    # Validate backup data structure
                    required_keys = ["customers", "suppliers", "settings", "customer_transactions", "supplier_transactions"]
                    if not all(key in backup_data for key in required_keys):
                        st.error("Invalid backup file format. Missing required data.")

                        st.stop()
                    
                    # Restore settings
                    st.session_state.settings = backup_data["settings"]
                    save_settings(backup_data["settings"])
                    
                    # Restore customers and their transactions
                    for customer_id, customer in backup_data["customers"].items():
                        save_customer(customer_id, customer)
                        
                        # Restore customer transactions
                        if customer_id in backup_data["customer_transactions"]:
                            for trans_id, transaction in backup_data["customer_transactions"][customer_id].items():
                                save_transaction("customer", customer_id, trans_id, transaction)
                    
                    # Restore suppliers and their transactions
                    for supplier_id, supplier in backup_data["suppliers"].items():
                        save_supplier(supplier_id, supplier)
                        
                        # Restore supplier transactions
                        if supplier_id in backup_data["supplier_transactions"]:
                            for trans_id, transaction in backup_data["supplier_transactions"][supplier_id].items():
                                save_transaction("supplier", supplier_id, trans_id, transaction)
                    
                    st.success("Data restored successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error restoring data: {e}")
        
        # Reset data
        st.write("### Reset Data")
        st.write("Reset all data to start fresh. This will delete all customers, suppliers, and transactions.")
        st.error("This action cannot be undone. Make sure to create a backup first.")
        
        if st.button("Reset All Data"):
            confirm = st.text_input("Type 'CONFIRM' to reset all data")
            
            if confirm == "CONFIRM":
                try:
                    # Reset Firebase data if using Firebase
                    if using_firebase:
                        db.child("customers").remove()
                        db.child("suppliers").remove()
                        db.child("customer_transactions").remove()
                        db.child("supplier_transactions").remove()
                    
                    # Reset local data
                    if os.path.exists(DATA_DIR):
                        import shutil
                        shutil.rmtree(DATA_DIR)
                        os.makedirs(DATA_DIR, exist_ok=True)
                        os.makedirs(CUSTOMER_DIR, exist_ok=True)
                        os.makedirs(SUPPLIER_DIR, exist_ok=True)
                        os.makedirs(CUSTOMER_TRANSACTIONS_DIR, exist_ok=True)
                        os.makedirs(SUPPLIER_TRANSACTIONS_DIR, exist_ok=True)
                    
                    # Keep settings but reset session state
                    st.session_state.current_customer = None
                    st.session_state.current_supplier = None
                    
                    st.success("All data has been reset successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error resetting data: {e}")

# Initialize required directories
DATA_DIR = "data"
CUSTOMER_DIR = os.path.join(DATA_DIR, "customers")
SUPPLIER_DIR = os.path.join(DATA_DIR, "suppliers")
CUSTOMER_TRANSACTIONS_DIR = os.path.join(DATA_DIR, "customer_transactions")
SUPPLIER_TRANSACTIONS_DIR = os.path.join(DATA_DIR, "supplier_transactions")

# Create directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CUSTOMER_DIR, exist_ok=True)
os.makedirs(SUPPLIER_DIR, exist_ok=True)
os.makedirs(CUSTOMER_TRANSACTIONS_DIR, exist_ok=True)
os.makedirs(SUPPLIER_TRANSACTIONS_DIR, exist_ok=True)

# Helper functions for data storage
def save_settings(settings_data):
    if using_firebase:
        try:
            db.child("settings").set(settings_data)
            return True
        except Exception as e:
            st.error(f"Error saving settings to Firebase: {e}")
    
    # Fallback to local storage
    try:
        settings_file = os.path.join(DATA_DIR, "settings.json")
        with open(settings_file, 'w') as f:
            json.dump(settings_data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving settings locally: {e}")
        return False

def save_customer(customer_id, customer_data):
    if using_firebase:
        try:
            db.child("customers").child(customer_id).set(customer_data)
            return True
        except Exception as e:
            st.error(f"Error saving customer to Firebase: {e}")
    
    # Fallback to local storage
    try:
        customer_file = os.path.join(CUSTOMER_DIR, f"{customer_id}.json")
        with open(customer_file, 'w') as f:
            json.dump(customer_data, f, indent=2)
        
        # Update customer index
        index_file = os.path.join(CUSTOMER_DIR, "index.json")
        index_data = {}
        
        if os.path.exists(index_file):
            with open(index_file, 'r') as f:
                index_data = json.load(f)
        
        index_data[customer_id] = customer_data
        
        with open(index_file, 'w') as f:
            json.dump(index_data, f, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Error saving customer locally: {e}")
        return False

def delete_customer(customer_id):
    if using_firebase:
        try:
            db.child("customers").child(customer_id).remove()
            db.child("customer_transactions").child(customer_id).remove()
            return True
        except Exception as e:
            st.error(f"Error deleting customer from Firebase: {e}")
    
    # Fallback to local storage
    try:
        # Delete customer file
        customer_file = os.path.join(CUSTOMER_DIR, f"{customer_id}.json")
        if os.path.exists(customer_file):
            os.remove(customer_file)
        
        # Delete transactions file
        transactions_file = os.path.join(CUSTOMER_TRANSACTIONS_DIR, f"{customer_id}.json")
        if os.path.exists(transactions_file):
            os.remove(transactions_file)
        
        # Update customer index
        index_file = os.path.join(CUSTOMER_DIR, "index.json")
        if os.path.exists(index_file):
            with open(index_file, 'r') as f:
                index_data = json.load(f)
            
            if customer_id in index_data:
                del index_data[customer_id]
            
            with open(index_file, 'w') as f:
                json.dump(index_data, f, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Error deleting customer locally: {e}")
        return False

def save_supplier(supplier_id, supplier_data):
    if using_firebase:
        try:
            db.child("suppliers").child(supplier_id).set(supplier_data)
            return True
        except Exception as e:
            st.error(f"Error saving supplier to Firebase: {e}")
    
    # Fallback to local storage
    try:
        supplier_file = os.path.join(SUPPLIER_DIR, f"{supplier_id}.json")
        with open(supplier_file, 'w') as f:
            json.dump(supplier_data, f, indent=2)
        
        # Update supplier index
        index_file = os.path.join(SUPPLIER_DIR, "index.json")
        index_data = {}
        
        if os.path.exists(index_file):
            with open(index_file, 'r') as f:
                index_data = json.load(f)
        
        index_data[supplier_id] = supplier_data
        
        with open(index_file, 'w') as f:
            json.dump(index_data, f, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Error saving supplier locally: {e}")
        return False

def delete_supplier(supplier_id):
    if using_firebase:
        try:
            db.child("suppliers").child(supplier_id).remove()
            db.child("supplier_transactions").child(supplier_id).remove()
            return True
        except Exception as e:
            st.error(f"Error deleting supplier from Firebase: {e}")
    
    # Fallback to local storage
    try:
        # Delete supplier file
        supplier_file = os.path.join(SUPPLIER_DIR, f"{supplier_id}.json")
        if os.path.exists(supplier_file):
            os.remove(supplier_file)
        
        # Delete transactions file
        transactions_file = os.path.join(SUPPLIER_TRANSACTIONS_DIR, f"{supplier_id}.json")
        if os.path.exists(transactions_file):
            os.remove(transactions_file)
        
        # Update supplier index
        index_file = os.path.join(SUPPLIER_DIR, "index.json")
        if os.path.exists(index_file):
            with open(index_file, 'r') as f:
                index_data = json.load(f)
            
            if supplier_id in index_data:
                del index_data[supplier_id]
            
            with open(index_file, 'w') as f:
                json.dump(index_data, f, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Error deleting supplier locally: {e}")
        return False

# Helper function for date validation
def validate_date(date_str):
    try:
        datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

# Helper function to format date input
def format_date_input(date_str):
    if not date_str:
        return ""
    
    # Remove any existing separators
    date_str = date_str.replace("-", "").replace("/", "")
    
    # Format as YYYY-MM-DD
    if len(date_str) >= 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    elif len(date_str) >= 6:
        return f"{date_str[:4]}-{date_str[4:6]}-"
    elif len(date_str) >= 4:
        return f"{date_str[:4]}-"
    else:
        return date_str

# Initialize session state variables
if 'edit_customer' not in st.session_state:
    st.session_state.edit_customer = None
if 'edit_supplier' not in st.session_state:
    st.session_state.edit_supplier = None
if 'edit_transaction' not in st.session_state:
    st.session_state.edit_transaction = None
if 'confirm_delete_customer' not in st.session_state:
    st.session_state.confirm_delete_customer = None
if 'confirm_delete_supplier' not in st.session_state:
    st.session_state.confirm_delete_supplier = None

# Determine if we're using Firebase or local storage
using_firebase = False
if firebaseConfig["apiKey"] != "YOUR_API_KEY":
    using_firebase = True
else:
    st.sidebar.warning("Firebase not configured. Using local storage.")

# Add a footer
st.markdown("""
---
<div style="text-align: center; color: #888;">
    <p>Ledger Management System | Version 1.0</p>
    <p>Developed by Mr.Arnav Gupta</p>
    <p>© 2025 All Rights Reserved</p>
</div>
""", unsafe_allow_html=True)
