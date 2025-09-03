import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image
import pytesseract
import io
from datetime import datetime
import re
import google.generativeai as genai

# -------------------------------
# Gemini Config (optional)
# -------------------------------
use_gemini = False
if "gemini" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        use_gemini = True
    except Exception as e:
        st.warning(f"⚠️ Gemini setup failed: {e}")

# -------------------------------
# Free OCR Function (Tesseract)
# -------------------------------
def extract_text_from_image(image):
    """Extracts raw text using Tesseract."""
    return pytesseract.image_to_string(image)

def parse_amount_with_regex(text):
    """Fallback parser using regex."""
    amounts = re.findall(r"\d+\.\d{2}|\d+", text)
    if amounts:
        return float(amounts[-1])  # assume last number is total
    return None

def parse_amount_with_gemini(text):
    """Ask Gemini to extract the most likely total amount from receipt text."""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
        Here is a receipt text:

        {text}

        Extract ONLY the final total amount the customer paid. 
        Return just the number (like 123.45) without currency symbols or extra text.
        """
        response = model.generate_content(prompt)
        raw = response.text.strip()
        match = re.search(r"\d+\.\d{2}|\d+", raw)
        if match:
            return float(match.group())
    except Exception as e:
        st.error(f"⚠️ Gemini parsing failed: {e}")
    return None

def extract_amount_from_image(image):
    """Main function to get amount (Tesseract + Gemini if available)."""
    full_text = extract_text_from_image(image)
    st.info(f"📄 Extracted Text (first 200 chars): {full_text[:200]}...")

    amount = None
    if use_gemini:
        amount = parse_amount_with_gemini(full_text)

    if not amount:
        amount = parse_amount_with_regex(full_text)

    return amount

# -------------------------------
# Expense Tracker App
# -------------------------------
st.title("💰 Expense Tracker with OCR + Gemini")

FILE_NAME = "expenses.csv"

def load_data():
    try:
        return pd.read_csv(FILE_NAME, parse_dates=["Date"])
    except FileNotFoundError:
        return pd.DataFrame(columns=["Date", "Category", "Amount"])

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

data = load_data()

# Camera or Upload
st.subheader("📷 Scan Bill")
img_file = st.camera_input("Take a picture of your bill") or st.file_uploader(
    "Or upload bill image", type=["png","jpg","jpeg"]
)

scanned_amount = None
if img_file:
    img = Image.open(img_file)
    scanned_amount = extract_amount_from_image(img)
    if scanned_amount:
        st.success(f"✅ Detected Amount: ₹ {scanned_amount:.2f}")
    else:
        st.warning("⚠️ Could not detect amount. Please enter manually.")

# Expense Form
with st.form("expense_form"):
    date = st.date_input("Date", datetime.today())
    category = st.selectbox("Category", ["Food", "Travel", "Shopping", "Bills", "Other"])
    amount = st.number_input(
        "Amount (₹)",
        min_value=0.0,
        value=scanned_amount if scanned_amount else 0.0,
        format="%.2f"
    )
    submitted = st.form_submit_button("Add Expense")

    if submitted and amount > 0:
        new_data = pd.DataFrame(
            {"Date": [date], "Category": [category], "Amount": [amount]}
        )
        data = pd.concat([data, new_data], ignore_index=True)
        save_data(data)
        st.success("✅ Expense Added!")

# Dashboard
st.subheader("📋 All Expenses")
st.dataframe(data, use_container_width=True)

if not data.empty:
    total = data["Amount"].sum()
    st.metric("Total Spent", f"₹ {total:,.2f}")

    category_summary = data.groupby("Category")["Amount"].sum().reset_index()

    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.bar(
            category_summary,
            x="Category", y="Amount", color="Category",
            title="Expenses by Category"
        )
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        fig2 = px.pie(
            category_summary,
            values="Amount", names="Category",
            title="Category Distribution", hole=0.4
        )
        st.plotly_chart(fig2, use_container_width=True)
