from flask import Flask, request, send_file
from twilio.twiml.messaging_response import MessagingResponse
import json, os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def normalize(phone):
    return phone.strip().replace(" ", "").replace("-", "").replace("whatsapp:", "").lstrip("+")


app = Flask(__name__)

EXPENSES_FILE = "expenses.json"
GROUPS_FILE   = "groups.json"
SESSIONS_FILE = "sessions.json"
CHART_FILE    = "static/chart.png"

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_expenses():   return load_json(EXPENSES_FILE, [])
def save_expenses(d):  save_json(EXPENSES_FILE, d)

def load_groups():     return load_json(GROUPS_FILE, [])
def save_groups(d):    save_json(GROUPS_FILE, d)

def load_sessions():   return load_json(SESSIONS_FILE, {})
def save_sessions(d):  save_json(SESSIONS_FILE, d)

def generate_pie_chart(expenses):
    totals = {}
    for e in expenses:
        totals[e["category"]] = totals.get(e["category"], 0) + e["amount"]
    cats, amts = list(totals.keys()), list(totals.values())
    if not cats:
        return False

    def make_autopct(vals):
        def my_autopct(pct):
            total = sum(vals)
            val = int(round(pct * total / 100.0))
            return f"₹{val} ({pct:.1f}%)"
        return my_autopct

    plt.figure(figsize=(6,6))
    plt.pie(amts, labels=cats, autopct=make_autopct(amts), startangle=140)
    plt.title("Category‑wise Spending")
    plt.tight_layout()
    os.makedirs("static", exist_ok=True)
    plt.savefig(CHART_FILE)
    plt.close()
    return True

@app.route("/chart")
def serve_chart():
    return send_file(CHART_FILE, mimetype="image/png")
@app.route("/webhook", methods=["POST"])
def webhook():
    user = request.values.get("From")
    text = request.values.get("Body", "").strip()
    txt_l = text.lower()

    print(f"[webhook] from={user!r} body={text!r}")

    resp = MessagingResponse()
    msg  = resp.message()

    expenses = load_expenses()
    groups   = load_groups()
    sessions = load_sessions()
    sess     = sessions.get(user, {"state": None, "temp": {}})
    state    = sess["state"]

    def reset():
        sessions[user] = {"state": None, "temp": {}}
        save_sessions(sessions)

    if state is None:
        msg.body(
            "👋 Hello! Manage 'personal' or 'group' expenses?\n"
            "Reply personal / group."
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
                    amt      = float(parts[1])
                    desc     = parts[2]
                    category = parts[3]
                    expenses.append({
                        "user": user,
                        "amount": amt,
                        "desc": desc,
                        "category": category
                    })
                    save_expenses(expenses)
                    msg.body(f"✅ Added ₹{amt} under {category.title()} for '{desc}'.")
                except ValueError:
                    msg.body("❌ Invalid amount. Use: add <amount> <desc> <category>")
            else:
                msg.body("❌ Invalid format. Use: add <amount> <desc> <category>")

        elif txt_l == "view all":
            personal = [e for e in expenses if e.get("user") == user]
            if not personal:
                msg.body("📭 No personal expenses yet.")
            else:
                out = "📋 Your Personal Expenses:\n"
                for i,e in enumerate(personal,1):
                    out += f"{i}. ₹{e['amount']} | {e['desc']} | {e['category'].title()}\n"
                msg.body(out)

        elif txt_l == "view chart":
            personal = [e for e in expenses if e.get("user") == user]
            if generate_pie_chart(personal):
                chart_url = request.url_root + "chart"
                msg.body("📊 Your Personal Spending Chart:")
                msg.media(chart_url)
            else:
                msg.body("❌ No personal data to chart.")

        elif txt_l == "back":
            reset()
            msg.body("🔙 Back to main menu.")

        else:
            msg.body(
                "❓ Personal options:\n"
                "• add <amount> <desc> <category>\n"
                "• view all\n"
                "• view chart\n"
                "• back"
            )

        save_sessions(sessions)
        print(f"[webhook] responding:\n{str(resp)}")
        return str(resp)

    if state == "group_menu":
        if txt_l == "create group":
            msg.body("➕ Enter new group name:")
            sessions[user]["state"] = "creating_group_name"

        elif txt_l == "view groups":
            mine = [g for g in groups if normalize(user) in [normalize(m) for m in g["members"]]]
            if not mine:
                msg.body("📭 You're not in any groups.\nReply 'create group' or 'back'.")
            else:
                out = "👥 Your Groups:\n"
                for g in mine:
                    out += f"- {g['name']} (Members: {', '.join(g['members'])})\n"
                out += (
                    "\nTo add expense:\n"
                    "add <group_name> <amount> <desc> <category>\n"
                    "To view expenses:\n"
                    "view expenses <group_name>\n"
                    "Or 'back'."
                )
                msg.body(out)

        elif txt_l.startswith("view expenses"):
            parts = text.split()
            if len(parts) >= 3:
                grp = parts[2]
                group = next((g for g in groups if g["name"] == grp), None)
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
                            out += f"{i}. ₹{e['amount']} | {e['desc']} | {e['category'].title()} (by {e['added_by']})\n"
                            total += e["amount"]
                        out += f"\n💰 Total: ₹{total}"
                        msg.body(out)
            else:
                msg.body("❌ Invalid format. Use: view expenses <group_name>")

        elif txt_l.startswith("add"):
            parts = text.split()
            if len(parts) >= 5:
                grp, amt_s, desc, cat = parts[1], parts[2], parts[3], parts[4]
                try:
                    amt = float(amt_s)
                except ValueError:
                    msg.body("❌ Invalid amount. Use: add <group_name> <amount> <desc> <category>")
                    save_sessions(sessions); print(f"[webhook] responding:\n{str(resp)}"); return str(resp)

                group = next((g for g in groups if g["name"] == grp), None)
                if not group:
                    msg.body(f"❌ No group named '{grp}'.")
                elif normalize(user) not in [normalize(m) for m in group["members"]]:
                    msg.body("❌ You're not a member of that group.")
                else:
                    group.setdefault("expenses", []).append({
                        "added_by": user,
                        "amount": amt,
                        "desc": desc,
                        "category": cat
                    })
                    save_groups(groups)
                    msg.body(f"✅ Added ₹{amt} to '{grp}' under {cat.title()} for '{desc}'.")
            else:
                msg.body("❌ Invalid format. Use: add <group_name> <amount> <desc> <category>")

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
        if any(g["name"] == name for g in groups):
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
            groups.append({"name": name, "members": members, "expenses": []})
            save_groups(groups)
            msg.body(
                f"✅ Group '{name}' created with members {', '.join(members)}.\n"
                "You can now add group expenses:\n"
                "add <group_name> <amount> <desc> <category>\n"
                "Or 'view groups', 'back'."
            )
            sessions[user]["state"] = "group_menu"
            sessions[user]["temp"] = {}
        save_sessions(sessions)
        print(f"[webhook] responding:\n{str(resp)}")
        return str(resp)

    reset()
    msg.body("🔄 Let's start over. personal / group?")
    save_sessions(sessions)
    print(f"[webhook] responding:\n{str(resp)}")
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True, port=5000)