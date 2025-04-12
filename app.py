from flask import Flask, request, send_file, url_for
from twilio.twiml.messaging_response import MessagingResponse
import json
import os

import matplotlib
matplotlib.use("Agg")  
import matplotlib.pyplot as plt


app = Flask(__name__)

EXPENSES_FILE = "expenses.json"
CHART_FILE = "static/chart.png"

def load_expenses():
    if os.path.exists(EXPENSES_FILE):
        with open(EXPENSES_FILE, "r") as f:
            return json.load(f)
    return []

def save_expenses(data):
    with open(EXPENSES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def generate_pie_chart(expenses):
    category_totals = {}
    for exp in expenses:
        category_totals[exp["category"]] = category_totals.get(exp["category"], 0) + exp["amount"]

    categories = list(category_totals.keys())
    amounts = list(category_totals.values())

    if not categories:
        return False

    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct * total / 100.0))
            return f"₹{val} ({pct:.1f}%)"
        return my_autopct

    plt.figure(figsize=(6, 6))
    plt.pie(amounts, labels=categories, autopct=make_autopct(amounts), startangle=140)
    plt.title("Category-wise Spending")
    plt.tight_layout()
    os.makedirs("static", exist_ok=True)
    plt.savefig(CHART_FILE)
    plt.close()
    return True


@app.route("/chart")
def serve_chart():
    return send_file(CHART_FILE, mimetype='image/png')

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip().lower()
    resp = MessagingResponse()
    msg = resp.message()

    expenses = load_expenses()

    if incoming_msg.startswith("add"):
        try:
            parts = incoming_msg.split()
            amount = float(parts[1])
            desc = parts[2]
            category = parts[3]

            expenses.append({
                "amount": amount,
                "desc": desc,
                "category": category
            })
            save_expenses(expenses)
            msg.body(f"✅ Added ₹{amount} under {category.title()} for '{desc}'.")
        except:
            msg.body("❌ Invalid format. Use: add <amount> <desc> <category>")

    elif incoming_msg == "view all":
        if not expenses:
            msg.body("📭 No expenses recorded yet.")
        else:
            response = "📋 All Expenses:\n\n"
            for idx, exp in enumerate(expenses, 1):
                response += f"{idx}. ₹{exp['amount']} | {exp['desc']} | {exp['category'].title()}\n"
            msg.body(response)

    elif incoming_msg == "view chart":
        if generate_pie_chart(expenses):
            chart_url = request.url_root + "chart"
            msg.body("📊 Here’s your category-wise spending chart:")
            msg.media(chart_url)
        else:
            msg.body("❌ Not enough data to generate chart.")

    else:
        msg.body("👋 Welcome to Expense Bot!\n\nUse:\n"
                 "• add <amount> <desc> <category>\n"
                 "• view all – list all expenses\n"
                 "• view chart – see category-wise spending")

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True, port=5000)