from utils.helpers import normalize

def calculate_group_balances(group):
    if not group.get("expenses"):
        return None
    
    balances = {normalize(member): 0 for member in group["members"]}
    
    total_amount = 0
    payments = {normalize(member): 0 for member in group["members"]}
    
    for expense in group["expenses"]:
        amount = expense["amount"]
        paid_by = normalize(expense.get("paid_by", expense.get("added_by")))
        total_amount += amount
        payments[paid_by] += amount
    
    equal_share = total_amount / len(group["members"])
    
    for member in balances:
        balances[member] = payments[member] - equal_share
    
    return balances 