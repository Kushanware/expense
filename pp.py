import streamlit as st
import pandas as pd
import plotly.express as px
import cv2
import pytesseract
from PIL import Image
from datetime import datetime
import numpy as np

# File storage
FILE_NAME = "expenses.csv"

# Load/Save Data
def load_data():
    try:
        return pd.read_csv(FILE_NAME, parse_dates=["Date"])
    except FileNotFoundError:
        return pd.DataFrame(columns=["Date", "Category", "Amount"])

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

# OCR Function
def extract_amount_from_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)

    # Extract first number that looks like price
    import re
    amounts = re.findall(r"\d+\.\d{2}|\d+", text)
    if amounts:
        return float(amounts[-1])  # Pick last number (usually total)
    return None

# Streamlit UI
st.set_page_config(page_title="Expense Tracker", layout="wide")
st.title("💰 Expense Tracker with Bill Scanner")

data = load_data()

# --- Camera Upload ---
st.subheader("📷 Scan Bill")
img_file = st.camera_input("Take a picture of your bill")

scanned_amount = None
if img_file is not None:
    img = Image.open(img_file)
    img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    scanned_amount = extract_amount_from_image(img)
    if scanned_amount:
        st.success(f"✅ Detected Amount: ₹ {scanned_amount:.2f}")
    else:
        st.warning("⚠ Could not detect amount. Please enter manually.")

# --- Input Form ---
with st.form("expense_form"):
    date = st.date_input("Date", datetime.today())
    category = st.selectbox("Category", ["Food", "Travel", "Shopping", "Bills", "Other"])
    amount = st.number_input("Amount (₹)", min_value=0.0, value=scanned_amount if scanned_amount else 0.0, format="%.2f")
    submitted = st.form_submit_button("Add Expense")

    if submitted and amount > 0:
        new_data = pd.DataFrame({"Date": [date], "Category": [category], "Amount": [amount]})
        data = pd.concat([data, new_data], ignore_index=True)
        save_data(data)
        st.success("✅ Expense Added!")

# --- Data Table ---
st.subheader("📋 All Expenses")
st.dataframe(data, use_container_width=True)

if not data.empty:
    total = data["Amount"].sum()
    st.metric("Total Spent", f"₹ {total:,.2f}")

    category_summary = data.groupby("Category")["Amount"].sum().reset_index()

    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.bar(category_summary, x="Category", y="Amount", color="Category", title="Expenses by Category")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = px.pie(category_summary, values="Amount", names="Category", title="Category Distribution", hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)
