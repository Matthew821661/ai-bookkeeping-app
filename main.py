import streamlit as st
import pandas as pd
import openai
import json

# ✅ Page Settings
st.set_page_config(
    page_title="Mattrade's AI bookkeeping",
    page_icon="📘",
    layout="wide"
)

# 🔑 OpenAI Key (⚠️ Do NOT hardcode in production)
openai.api_key = "sk-proj-your-key-here"  # replace with your actual key

# ✅ GPT Function
def classify_transaction(description):
    prompt = f"""Classify the following transaction for a South African SME accountant:
'{description}'.

Return only a JSON response with the following fields:
- general_ledger_account_name
- account_number
- vat_type
- vat_percentage
- reason

Example:
{{
  "general_ledger_account_name": "Stationery",
  "account_number": "6100",
  "vat_type": "Standard",
  "vat_percentage": 15,
  "reason": "Office supplies purchased"
}}"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        content = response.choices[0].message['content'].strip()
        result_json = json.loads(content)
        return result_json
    except Exception as e:
        return {
            "general_ledger_account_name": "Unknown",
            "account_number": "9999",
            "vat_type": "None",
            "vat_percentage": 0.0,
            "reason": f"Error: {e}"
        }

# ✅ CSV Importer
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

# ✅ AI Classification Logic
def classify_bank_dataframe(df):
    classified_data = []
    for _, row in df.iterrows():
        result = classify_transaction(row['description'])

        vat_type = result.get('vat_type', 'None')
        vat_percentage = result.get('vat_percentage', 0.0)
        vat_amount = abs(row['value']) * (vat_percentage / 100) if vat_type.lower() == 'standard' else 0

        classified_data.append({
            'date': row['date'],
            'description': row['description'],
            'value': row['value'],
            'account_name': result.get('general_ledger_account_name', 'Unknown'),
            'account_number': result.get('account_number', '9999'),
            'vat_type': vat_type,
            'vat_percent': vat_percentage,
            'vat_amount': round(vat_amount, 2),
            'ai_reason': result.get('reason', 'No reason')
        })

    return pd.DataFrame(classified_data)

# ✅ General Ledger Generator
def generate_general_ledger(df):
    ledger_entries = []
    for _, row in df.iterrows():
        date, desc, amount, vat_amount = row['date'], row['description'], row['value'], float(row.get('vat_amount', 0))
        net_amount = amount - vat_amount

        # Main entry
        ledger_entries.append({
            'date': date,
            'description': desc,
            'account_name': row['account_name'],
            'account_number': row['account_number'],
            'debit': abs(net_amount) if amount < 0 else 0,
            'credit': net_amount if amount > 0 else 0
        })

        # VAT control
        if vat_amount > 0:
            ledger_entries.append({
                'date': date,
                'description': f"VAT on: {desc}",
                'account_name': 'VAT Control',
                'account_number': '2010',
                'debit': abs(vat_amount) if amount < 0 else 0,
                'credit': vat_amount if amount > 0 else 0
            })

        # Bank entry
        ledger_entries.append({
            'date': date,
            'description': f"Bank Entry: {desc}",
            'account_name': 'Bank',
            'account_number': '1000',
            'debit': amount if amount > 0 else 0,
            'credit': abs(amount) if amount < 0 else 0
        })

    return pd.DataFrame(ledger_entries)

# ✅ Trial Balance Generator
def generate_trial_balanc
 
