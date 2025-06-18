import streamlit as st
import pandas as pd
import openai

# ✅ Page settings
st.set_page_config(
    page_title="Matthew's AI Bookkeeper",
    page_icon="📘",
    layout="wide"
)

openai.api_key = ["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"]

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
    df = pd.read_csv(file, sep=';')
    df.columns = df.columns.str.lower().str.strip()
    df.rename(columns={
        'date': 'date',
        'description': 'description',
        'amount': 'value'
    }, inplace=True)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['date', 'description', 'value'])
    return df[['date', 'description', 'value']]

def classify_bank_dataframe(df):
    classified_data = []
    for _, row in df.iterrows():
        result = classify_transaction(row['description'])
        lines = result.split("\n")

        # Default values
        account_name = "Unknown"
        account_number = "9999"
        vat_type = "None"
        vat_percent = 0.0
        reason = "Could not extract fields"

        for line in lines:
            if "General Ledger Account Name" in line:
                account_name = line.split(":", 1)[-1].strip()
            elif "Account Number" in line:
                account_number = line.split(":", 1)[-1].strip()
            elif "VAT Type" in line:
                vat_type = line.split(":", 1)[-1].strip()
            elif "VAT Percentage" in line:
                try:
                    vat_percent = float(line.split(":", 1)[-1].replace('%', '').strip())
                except:
                    vat_percent = 0.0
            elif "One-line reason" in line:
                reason = line.split(":", 1)[-1].strip()

        vat_amount = abs(row['value']) * (vat_percent / 100) if vat_type.lower() == 'standard' else 0
        classified_data.append({
            'date': row['date'], 'description': row['description'], 'value': row['value'],
            'account_name': account_name, 'account_number': account_number,
            'vat_type': vat_type, 'vat_percent': vat_percent,
            'vat_amount': round(vat_amount, 2), 'ai_reason': reason
        })
    return pd.DataFrame(classified_data)

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

st.title("📘 Matthew's AI Bookkeeper")

uploaded_file = st.file_uploader("Upload Bank Statement (.csv with semicolon ';')", type="csv")
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
