from flask import Flask, request, send_file
from twilio.twiml.messaging_response import MessagingResponse

from utils.helpers import normalize
from utils.chart import generate_pie_chart
from utils.balance import calculate_group_balances
from utils.ai_insights import get_monthly_summary_and_suggestions
from utils.razorpay_integration import process_expense_payment, process_group_expense_share
from models.data import (
    load_expenses, save_expenses,
    load_groups, save_groups,
    load_sessions, save_sessions,
    add_expense, add_group, update_group,
    get_group_by_name, get_user_expenses,
    get_user_groups, get_user_budget, set_user_budget,
    get_user_budget_usage
)
from models.mongodb import get_user_id, add_phone_to_user

app = Flask(__name__)

@app.route("/chart")
def serve_chart():
    return send_file("static/chart.png", mimetype="image/png")

@app.route("/webhook", methods=["POST"])
def webhook():
    user = request.values.get("From")
    text = request.values.get("Body", "").strip()
    txt_l = text.lower()

    print(f"[webhook] from={user!r} body={text!r}")

    user_id = get_user_id(user)
    
    add_phone_to_user(user_id, user)

    resp = MessagingResponse()
    msg = resp.message()

    expenses = load_expenses()
    groups = load_groups()
    sessions = load_sessions()
    sess = sessions.get(user, {"state": None, "temp": {}})
    state = sess["state"]

    def reset():
        sessions[user] = {"state": None, "temp": {}}
        save_sessions(sessions)

    if state is None:
        msg.body(
            "👋 Hello! Manage 'personal' or 'group' expenses?\n"
            "Reply personal / group."
        )
        sessions[user] = {"state": "awaiting_scope", "temp": {}}
        save_sessions(sessions)
        print(f"[webhook] responding:\n{str(resp)}")
        return str(resp)

    if state == "awaiting_scope":
        if txt_l == "personal":
            msg.body(
                "🧑 Personal mode:\n"
                "• add <amount> <desc> <category>\n"
                "• view all\n"
                "• view chart\n"
                "Reply or 'back'."
            )
            sessions[user]["state"] = "personal_menu"

        elif txt_l == "group":
            msg.body(
                "👥 Group mode:\n"
                "• create group\n"
                "• view groups\n"
                "Reply or 'back'."
            )
            sessions[user]["state"] = "group_menu"

        else:
            msg.body("❓ Please reply 'personal' or 'group'.")
        save_sessions(sessions)
        print(f"[webhook] responding:\n{str(resp)}")
        return str(resp)

    if state == "personal_menu":
        if txt_l.startswith("add"):
            parts = text.split()
            if len(parts) >= 4:
                try:
                    amt = float(parts[1])
                    desc = parts[2]
                    category = parts[3]
                    expense = {
                        "user": user,
                        "amount": amt,
                        "desc": desc,
                        "category": category
                    }
                    
                    # Process payment for the expense (just logging, no actual payment)
                    user_id = get_user_id(user)
                    payment = process_expense_payment(expense, user_id)
                    
                    if payment:
                        add_expense(expense)
                        msg.body(f"✅ Added ₹{amt} under {category.title()} for '{desc}'.\nPayment processed: ₹{amt} deducted from your account.")
                    else:
                        msg.body(f"❌ Failed to process payment for ₹{amt}. Please try again.")
                except ValueError:
                    msg.body("❌ Invalid amount. Use: add <amount> <desc> <category>")
            else:
                msg.body("❌ Invalid format. Use: add <amount> <desc> <category>")

        elif txt_l == "view all":
            personal = get_user_expenses(user)
            if not personal:
                msg.body("📭 No personal expenses yet.")
            else:
                out = "📋 Your Personal Expenses:\n"
                for i, e in enumerate(personal, 1):
                    out += f"{i}. ₹{e['amount']} | {e['desc']} | {e['category'].title()}\n"
                msg.body(out)

        elif txt_l == "view chart":
            personal = get_user_expenses(user)
            if generate_pie_chart(personal):
                chart_url = request.url_root + "chart"
                msg.body("📊 Your Personal Spending Chart:")
                msg.media(chart_url)
            else:
                msg.body("❌ No personal data to chart.")

        elif txt_l == "monthly review":
            msg.body("🤖 Generating AI-powered insights for your expenses...")
            insights = get_monthly_summary_and_suggestions(user)
            msg.body(insights)

        elif txt_l == "set budget":
            msg.body(
                "💰 Set your monthly budget:\n"
                "Format: category1 amount1 category2 amount2 ...\n"
                "Example: food 5000 transport 2000 shopping 3000\n"
                "Or 'back' to cancel."
            )
            sessions[user]["state"] = "setting_budget"

        elif txt_l == "view budget":
            user_id = get_user_id(user)
            budget = get_user_budget(user_id)
            if not budget:
                msg.body("📭 No budget set yet. Use 'set budget' to create one.")
            else:
                usage = get_user_budget_usage(user_id)
                out = "💰 Your Monthly Budget:\n\n"
                total_budget = 0
                total_spent = 0
                
                for category, amount in budget.get("categories", {}).items():
                    spent = usage.get(category, 0)
                    remaining = amount - spent
                    total_budget += amount
                    total_spent += spent
                    
                    out += f"{category.title()}: ₹{amount}\n"
                    out += f"Spent: ₹{spent}\n"
                    out += f"Remaining: ₹{remaining}\n\n"
                
                out += f"Total Budget: ₹{total_budget}\n"
                out += f"Total Spent: ₹{total_spent}\n"
                out += f"Total Remaining: ₹{total_budget - total_spent}"
                
                msg.body(out)

        elif txt_l == "back":
            reset()
            msg.body("🔙 Back to main menu.")

        else:
            msg.body(
                "❓ Personal options:\n"
                "• add <amount> <desc> <category>\n"
                "• view all\n"
                "• view chart\n"
                "• get insights\n"
                "• set budget\n"
                "• view budget\n"
                "• back"
            )

        save_sessions(sessions)
        print(f"[webhook] responding:\n{str(resp)}")
        return str(resp)

    if state == "setting_budget":
        if txt_l == "back":
            sessions[user]["state"] = "personal_menu"
            msg.body("🔙 Back to personal menu.")
        else:
            try:
                parts = text.split()
                if len(parts) % 2 != 0:
                    raise ValueError("Invalid format")
                
                budget_data = {"categories": {}}
                for i in range(0, len(parts), 2):
                    category = parts[i].lower()
                    amount = float(parts[i + 1])
                    budget_data["categories"][category] = amount
                
                user_id = get_user_id(user)
                set_user_budget(user_id, budget_data)
                
                out = "✅ Budget set successfully:\n\n"
                for category, amount in budget_data["categories"].items():
                    out += f"{category.title()}: ₹{amount}\n"
                
                msg.body(out)
                sessions[user]["state"] = "personal_menu"
            except (ValueError, IndexError):
                msg.body(
                    "❌ Invalid format. Use:\n"
                    "category1 amount1 category2 amount2 ...\n"
                    "Example: food 5000 transport 2000 shopping 3000\n"
                    "Or 'back' to cancel."
                )
        
        save_sessions(sessions)
        print(f"[webhook] responding:\n{str(resp)}")
        return str(resp)

    if state == "group_menu":
        if txt_l == "create group":
            msg.body("➕ Enter new group name:")
            sessions[user]["state"] = "creating_group_name"

        elif txt_l == "view groups":
            mine = get_user_groups(user)
            if not mine:
                msg.body("📭 You're not in any groups.\nReply 'create group' or 'back'.")
            else:
                out = "👥 Your Groups:\n"
                for g in mine:
                    out += f"- {g['name']} (Members: {', '.join(g['members'])})\n"
                out += (
                    "\nTo add expense:\n"
                    "add <group_name> <amount> <desc> <category> <paid_by>\n"
                    "To view expenses:\n"
                    "view expenses <group_name>\n"
                    "To view chart:\n"
                    "view chart <group_name>\n"
                    "To view balances:\n"
                    "view balances <group_name>\n"
                    "To pay your share:\n"
                    "pay share <group_name>\n"
                    "Or 'back'."
                )
                msg.body(out)

        elif txt_l.startswith("pay share"):
            parts = text.split()
            if len(parts) >= 3:
                grp = parts[2]
                group = get_group_by_name(grp)
                if not group:
                    msg.body(f"❌ No group named '{grp}'.")
                elif normalize(user) not in [normalize(m) for m in group["members"]]:
                    msg.body("❌ You're not a member of that group.")
                else:
                    balances = calculate_group_balances(group)
                    if not balances:
                        msg.body(f"📭 No expenses in group '{grp}' to calculate balances.")
                    else:
                        user_balance = balances.get(normalize(user), 0)
                        if user_balance >= 0:
                            msg.body(f"✅ You don't owe anything in group '{grp}'.")
                        else:
                            amount_to_pay = abs(user_balance)
                            user_id = get_user_id(user)
                            
                            # Find the person who is owed money (has positive balance)
                            creditors = {m: b for m, b in balances.items() if b > 0}
                            if not creditors:
                                msg.body(f"❌ No one to pay in group '{grp}'.")
                            else:
                                # Get the first creditor (person who is owed money)
                                creditor = next(iter(creditors))
                                creditor_id = get_user_id(creditor)
                                
                                # Process payment for the user's share
                                payment = process_group_expense_share(
                                    expense={"desc": f"Share in {grp}", "category": "group_share"},
                                    user_id=user_id,
                                    share_amount=amount_to_pay,
                                    recipient_id=creditor_id
                                )
                                
                                if payment:
                                    msg.body(f"✅ Payment processed: ₹{amount_to_pay:.2f} sent to {creditor} for your share in group '{grp}'.")
                                else:
                                    msg.body(f"❌ Failed to process payment for ₹{amount_to_pay:.2f}. Please try again.")
            else:
                msg.body("❌ Invalid format. Use: pay share <group_name>")

        elif txt_l.startswith("view balances"):
            parts = text.split()
            if len(parts) >= 3:
                grp = parts[2]
                group = get_group_by_name(grp)
                if not group:
                    msg.body(f"❌ No group named '{grp}'.")
                elif normalize(user) not in [normalize(m) for m in group["members"]]:
                    msg.body("❌ You're not a member of that group.")
                else:
                    balances = calculate_group_balances(group)
                    if not balances:
                        msg.body(f"📭 No expenses in group '{grp}' to calculate balances.")
                    else:
                        out = f"💰 Balances in group '{grp}':\n\n"
                        
                        out += "📊 Expense Summary:\n"
                        total_paid = {normalize(member): 0 for member in group["members"]}
                        for expense in group["expenses"]:
                            paid_by = normalize(expense.get("paid_by", expense.get("added_by")))
                            amount = expense["amount"]
                            total_paid[paid_by] += amount
                            out += f"- {expense.get('paid_by', expense.get('added_by'))} paid ₹{amount} for {expense['desc']}\n"
                        
                        out += "\n💰 Net Balances:\n"
                        for member, balance in balances.items():
                            original_member = next(m for m in group["members"] if normalize(m) == member)
                            if balance > 0:
                                out += f"- {original_member} is owed ₹{balance:.2f}\n"
                            elif balance < 0:
                                out += f"- {original_member} owes ₹{abs(balance):.2f}\n"
                            else:
                                out += f"- {original_member} is settled\n"
                        
                        out += "\n🔄 Settlement Plan:\n"
                        debtors = {m: b for m, b in balances.items() if b < 0}
                        creditors = {m: b for m, b in balances.items() if b > 0}
                        
                        for debtor, debt in debtors.items():
                            original_debtor = next(m for m in group["members"] if normalize(m) == debtor)
                            remaining_debt = abs(debt)
                            for creditor, credit in creditors.items():
                                if remaining_debt <= 0 or credit <= 0:
                                    continue
                                original_creditor = next(m for m in group["members"] if normalize(m) == creditor)
                                payment = min(remaining_debt, credit)
                                out += f"- {original_debtor} should pay ₹{payment:.2f} to {original_creditor}\n"
                                remaining_debt -= payment
                                creditors[creditor] -= payment
                        
                        # Add option to pay your share
                        user_balance = balances.get(normalize(user), 0)
                        if user_balance < 0:
                            out += f"\n💳 To pay your share of ₹{abs(user_balance):.2f}, reply: pay share {grp}"
                        
                        msg.body(out)
            else:
                msg.body("❌ Invalid format. Use: view balances <group_name>")

        elif txt_l.startswith("view chart"):
            parts = text.split()
            if len(parts) >= 3:
                grp = parts[2]
                group = get_group_by_name(grp)
                if not group:
                    msg.body(f"❌ No group named '{grp}'.")
                elif normalize(user) not in [normalize(m) for m in group["members"]]:
                    msg.body("❌ You're not a member of that group.")
                else:
                    expenses = group.get("expenses", [])
                    if not expenses:
                        msg.body(f"📭 No expenses in group '{grp}' to chart.")
                    else:
                        if generate_pie_chart(expenses, f"Category‑wise Spending in {grp}"):
                            chart_url = request.url_root + "chart"
                            msg.body(f"📊 Spending Chart for group '{grp}':")
                            msg.media(chart_url)
                        else:
                            msg.body("❌ Could not generate chart.")
            else:
                msg.body("❌ Invalid format. Use: view chart <group_name>")

        elif txt_l.startswith("view expenses"):
            parts = text.split()
            if len(parts) >= 3:
                grp = parts[2]
                group = get_group_by_name(grp)
                if not group:
                    msg.body(f"❌ No group named '{grp}'.")
                elif normalize(user) not in [normalize(m) for m in group["members"]]:
                    msg.body("❌ You're not a member of that group.")
                else:
                    expenses = group.get("expenses", [])
                    if not expenses:
                        msg.body(f"📭 No expenses in group '{grp}' yet.")
                    else:
                        out = f"📋 Expenses in group '{grp}':\n"
                        total = 0
                        for i, e in enumerate(expenses, 1):
                            paid_by = e.get('paid_by', e['added_by'])
                            out += f"{i}. ₹{e['amount']} | {e['desc']} | {e['category'].title()} (by {e['added_by']}, paid by {paid_by})\n"
                            total += e["amount"]
                        out += f"\n💰 Total: ₹{total}"
                        msg.body(out)
            else:
                msg.body("❌ Invalid format. Use: view expenses <group_name>")

        elif txt_l.startswith("add"):
            parts = text.split()
            if len(parts) >= 6:
                grp, amt_s, desc, cat, paid_by = parts[1], parts[2], parts[3], parts[4], parts[5]
                try:
                    amt = float(amt_s)
                except ValueError:
                    msg.body("❌ Invalid amount. Use: add <group_name> <amount> <desc> <category> <paid_by>")
                    save_sessions(sessions)
                    print(f"[webhook] responding:\n{str(resp)}")
                    return str(resp)

                group = get_group_by_name(grp)
                if not group:
                    msg.body(f"❌ No group named '{grp}'.")
                elif normalize(user) not in [normalize(m) for m in group["members"]]:
                    msg.body("❌ You're not a member of that group.")
                elif normalize(paid_by) not in [normalize(m) for m in group["members"]]:
                    msg.body("❌ The person who paid is not a member of this group.")
                else:
                    expense = {
                        "added_by": user,
                        "amount": amt,
                        "desc": desc,
                        "category": cat,
                        "paid_by": paid_by
                    }
                    
                    # Calculate the user's share of the expense
                    num_members = len(group["members"])
                    user_share = amt / num_members
                    
                    # Process payment for the user's share of the expense
                    user_id = get_user_id(user)
                    
                    # If the user is the one who paid, no need to deduct their share as they've already paid the full amount in real life
                    if normalize(user) == normalize(paid_by):
                        payment = process_expense_payment({
                            "user": user,
                            "amount": amt,
                            "desc": f"{desc} in {grp}",
                            "category": cat
                        }, user_id)
                        
                        if payment:
                            group.setdefault("expenses", []).append(expense)
                            update_group(grp, {"expenses": group["expenses"]})
                            msg.body(f"✅ Added ₹{amt} to '{grp}' under {cat.title()} for '{desc}' (paid by you).\nExpense logged successfully.")
                        else:
                            msg.body(f"❌ Failed to log expense for ₹{amt}. Please try again.")
                    else:
                        payment = process_expense_payment({
                            "user": user,
                            "amount": user_share,
                            "desc": f"Share of {desc} in {grp}",
                            "category": cat
                        }, user_id)
                        
                        if payment:
                            group.setdefault("expenses", []).append(expense)
                            update_group(grp, {"expenses": group["expenses"]})
                            msg.body(f"✅ Added ₹{amt} to '{grp}' under {cat.title()} for '{desc}' (paid by {paid_by}).\nYour share of ₹{user_share:.2f} has been deducted from your account.")
                        else:
                            msg.body(f"❌ Failed to process payment for your share of ₹{user_share:.2f}. Please try again.")
            else:
                msg.body("❌ Invalid format. Use: add <group_name> <amount> <desc> <category> <paid_by>")

        elif txt_l == "back":
            reset()
            msg.body("🔙 Back to main menu.")

        else:
            msg.body(
                "❓ Group options:\n"
                "• create group\n"
                "• view groups\n"
                "• back"
            )

        save_sessions(sessions)
        print(f"[webhook] responding:\n{str(resp)}")
        return str(resp)

    if state == "creating_group_name":
        name = text
        if get_group_by_name(name):
            msg.body("❌ That name's taken. Enter another group name:")
        else:
            sessions[user]["temp"]["group_name"] = name
            sessions[user]["state"] = "creating_group_members"
            msg.body(
                "👥 Now enter members' phone numbers (E.164),\n"
                "separated by spaces (include yourself)."
            )
        save_sessions(sessions)
        print(f"[webhook] responding:\n{str(resp)}")
        return str(resp)

    if state == "creating_group_members":
        members = text.split()
        if not all(m.startswith("+") for m in members):
            msg.body(
                "❌ Invalid format. Use E.164 (e.g. +123456789).\n"
                "Try again:"
            )
        else:
            name = sessions[user]["temp"]["group_name"]
            group = {"name": name, "members": members, "expenses": []}
            add_group(group)
            msg.body(
                f"✅ Group '{name}' created with members {', '.join(members)}.\n"
                "You can now add group expenses:\n"
                "add <group_name> <amount> <desc> <category> <paid_by>\n"
                "Or 'view groups', 'back'."
            )
            sessions[user]["state"] = "group_menu"
            sessions[user]["temp"] = {}
        save_sessions(sessions)
        print(f"[webhook] responding:\n{str(resp)}")
        return str(resp)

    reset()
    msg.body("🔄 Let's start over. personal / group?")
    save_sessions(sessions)
    print(f"[webhook] responding:\n{str(resp)}")
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True, port=5000)