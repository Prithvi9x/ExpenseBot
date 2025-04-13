import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

def generate_pie_chart(expenses, title="Category‑wise Spending"):
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
    plt.title(title)
    plt.tight_layout()
    os.makedirs("static", exist_ok=True)
    plt.savefig("static/chart.png")
    plt.close()
    return True 