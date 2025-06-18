import streamlit as st
import pandas as pd
import openai
from io import StringIO

openai.api_key = st.secrets["OPENAI_API_KEY"]

def classify_transaction(description):
    prompt = f"Classify the following transaction for a South African SME accountant: '{description}'. Provide:\n1. General Ledger Account Name\n2. Account Number\n3. VAT Type (Standard, Zero, Exempt, None)\n4. VAT Percentage (15% or 0% or 0)\n5. One-line reason"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        return "Error: " + str(e)

def import_bank_statement(file):
    # Try reading with semicolon separator
    df = pd.read_csv(file, sep=';')
    df.columns = df.columns.str.lower().str.strip()

    # Rename columns to standard names
    df.rename(columns={
        'date': 'date',
        'description': 'description',
        'amount': 'value'
    }, inplace=True)

    # Convert date and value
    df['date'] = pd.to_datetime(df['date'], dayfirst=False, errors='coerce')
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Drop any rows with missing values
    df = df.dropna(subset=['date', 'description', 'value'])

    return df[['date', 'description', 'value']]

def generate_general_ledger(df):
    ledger_entries = []
    for _, row in df.iterrows():
        date, desc, amount, vat_amount = row['date'], row['description'], row['value'], float(row.get('vat_amount', 0))
        net_amount = amount - vat_amount if amount < 0 else amount - vat_amount
        ledger_entries.append({'date': date, 'description': desc, 'account_name': row['account_name'], 'account_number': row['account_number'],
                               'debit': abs(net_amount) if amount < 0 else 0, 'credit': net_amount if amount > 0 else 0})
        if vat_amount > 0:
            ledger_entries.append({'date': date, 'description': f"VAT on: {desc}", 'account_name': 'VAT Control', 'account_number': '2010',
                                   'debit': abs(vat_amount) if amount < 0 else 0, 'credit': vat_amount if amount > 0 else 0})
        ledger_entries.append({'date': date, 'description': f"Bank Entry: {desc}", 'account_name': 'Bank', 'account_number': '1000',
                               'debit': amount if amount > 0 else 0, 'credit': abs(amount) if amount < 0 else 0})
    return pd.DataFrame(ledger_entries)

def generate_trial_balance(ledger_df):
    tb = ledger_df.groupby(['account_number', 'account_name']).agg({'debit': 'sum', 'credit': 'sum'}).reset_index()
    tb['balance'] = tb['debit'] - tb['credit']
    return tb

st.title("🧾 Smart AI Bookkeeping")

uploaded_file = st.file_uploader("Upload Bank Statement (CSV format)", type="csv")
if uploaded_file:
    df = import_bank_statement(uploaded_file)
    st.subheader("🧹 Cleaned Bank Transactions")
    st.dataframe(df)

    if st.button("🤖 Classify Transactions with AI"):
        classified_df = classify_bank_dataframe(df)
        st.subheader("📊 AI-Classified Transactions")
        st.dataframe(classified_df)

        ledger_df = generate_general_ledger(classified_df)
        st.subheader("📘 General Ledger")
        st.dataframe(ledger_df)

        tb_df = generate_trial_balance(ledger_df)
        st.subheader("🧮 Trial Balance")
        st.dataframe(tb_df)
        st.markdown("**Total Debits:** R{:.2f}".format(tb_df['debit'].sum()))
        st.markdown("**Total Credits:** R{:.2f}".format(tb_df['credit'].sum()))
