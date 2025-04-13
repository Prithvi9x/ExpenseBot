import requests
import os
import json
import random
from dotenv import load_dotenv
from datetime import datetime, timedelta
from models.mongodb import get_user_expenses

# Load environment variables
load_dotenv()

def get_monthly_summary_and_suggestions(user: str) -> str:
    # Get user's expenses for the current month
    expenses = get_user_expenses(user)
    
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (current_month + timedelta(days=32)).replace(day=1)
    
    monthly_expenses = [
        e for e in expenses 
        if isinstance(e.get("created_at"), datetime) and 
        current_month <= e["created_at"] < next_month
    ]
    
    if not monthly_expenses:
        return "No expenses recorded for this month yet."
    
    total_spent = sum(e["amount"] for e in monthly_expenses)
    category_totals = {}
    for expense in monthly_expenses:
        category = expense.get("category", "other")
        category_totals[category] = category_totals.get(category, 0) + expense["amount"]
    
    # Sort categories by amount spent
    sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    
    return generate_structured_insights(total_spent, sorted_categories)

def generate_structured_insights(total_spent, sorted_categories):
    
    top_category, top_amount = sorted_categories[0]
    
    # Calculate percentages
    category_percentages = {}
    for category, amount in sorted_categories:
        percentage = (amount / total_spent) * 100
        category_percentages[category] = round(percentage, 1)
    
    # Generate insights
    response = "📊 Monthly Expense Analysis\n\n"
    
    response += "🔍 Key Spending Patterns:\n"
    
    top_spending_descriptions = [
        f"• Your highest spending is in the {top_category} category (₹{top_amount:.2f}, {category_percentages[top_category]}% of total)",
        f"• The {top_category} category dominates your expenses at ₹{top_amount:.2f} ({category_percentages[top_category]}% of total)",
        f"• You've allocated the most funds to {top_category} with ₹{top_amount:.2f} ({category_percentages[top_category]}% of total)",
        f"• {top_category.title()} is your biggest expense category at ₹{top_amount:.2f} ({category_percentages[top_category]}% of total)"
    ]
    response += random.choice(top_spending_descriptions) + "\n"
    
    # Add second highest category if available
    if len(sorted_categories) > 1:
        second_category, second_amount = sorted_categories[1]
        second_descriptions = [
            f"• Second highest spending is in {second_category} (₹{second_amount:.2f}, {category_percentages[second_category]}% of total)",
            f"• {second_category.title()} follows with ₹{second_amount:.2f} ({category_percentages[second_category]}% of total)",
            f"• You've spent ₹{second_amount:.2f} on {second_category} ({category_percentages[second_category]}% of total)"
        ]
        response += random.choice(second_descriptions) + "\n"
    
    total_spending_descriptions = [
        f"• You've spent a total of ₹{total_spent:.2f} this month",
        f"• Your monthly expenses total ₹{total_spent:.2f}",
        f"• This month's total spending is ₹{total_spent:.2f}"
    ]
    response += random.choice(total_spending_descriptions) + "\n\n"
    
    response += "💰 Money-Saving Suggestions:\n"
    
    # Generate personalized suggestions based on spending patterns
    suggestions = []
    
    if top_category == "food":
        food_suggestions = [
            "• Consider meal planning to reduce food expenses",
            "• Look for grocery deals and discounts",
            "• Try cooking in bulk and freezing meals",
            "• Explore more affordable dining options",
            "• Use cashback apps for food purchases"
        ]
        suggestions.extend(random.sample(food_suggestions, 2))
    elif top_category == "transport":
        transport_suggestions = [
            "• Explore public transportation options",
            "• Consider carpooling or ride-sharing services",
            "• Look into monthly transit passes",
            "• Plan your trips to minimize fuel consumption",
            "• Consider cycling or walking for short distances"
        ]
        suggestions.extend(random.sample(transport_suggestions, 2))
    elif top_category == "shopping":
        shopping_suggestions = [
            "• Wait for sales before making purchases",
            "• Unsubscribe from promotional emails to avoid impulse buying",
            "• Use price comparison tools before buying",
            "• Consider buying in bulk for frequently used items",
            "• Look for cashback and reward programs"
        ]
        suggestions.extend(random.sample(shopping_suggestions, 2))
    elif top_category == "entertainment" or top_category == "fun":
        entertainment_suggestions = [
            "• Look for free or low-cost entertainment options",
            "• Set a monthly entertainment budget",
            "• Explore subscription services instead of one-time purchases",
            "• Find local community events and activities",
            "• Consider hosting gatherings at home instead of going out"
        ]
        suggestions.extend(random.sample(entertainment_suggestions, 2))
    else:
        generic_suggestions = [
            f"• Consider setting a monthly budget for {top_category} activities",
            f"• Look for more cost-effective alternatives in the {top_category} category",
            f"• Research ways to reduce {top_category} expenses",
            f"• Set specific spending limits for {top_category}",
            f"• Track your {top_category} spending more closely"
        ]
        suggestions.extend(random.sample(generic_suggestions, 2))
    
    general_suggestions = [
        "• Track small expenses to avoid accumulation",
        "• Review your subscriptions and cancel unused ones",
        "• Set up automatic savings transfers",
        "• Use cash for discretionary spending to stay within budget",
        "• Consider using a budgeting app to track expenses"
    ]
    suggestions.extend(random.sample(general_suggestions, 1))
    
    for suggestion in suggestions:
        response += suggestion + "\n"
    
    response += "\n"
    
    response += "🎯 Area for Optimization:\n"
    
    # Calculate potential savings
    savings_percentage = min(30, category_percentages[top_category] // 2)
    potential_savings = top_amount * (savings_percentage / 100)
    
    optimization_descriptions = [
        f"• The {top_category} category spending could be reduced by {savings_percentage}% to save approximately ₹{potential_savings:.2f} monthly",
        f"• Consider reducing {top_category} expenses by {savings_percentage}% to free up ₹{potential_savings:.2f} each month",
        f"• Optimizing {top_category} spending by {savings_percentage}% could save you ₹{potential_savings:.2f} monthly",
        f"• A {savings_percentage}% reduction in {top_category} expenses would save you ₹{potential_savings:.2f} per month"
    ]
    response += random.choice(optimization_descriptions)
    
    return response

def get_suggestions_from_hf(prompt: str) -> str:
    # Using a more suitable model for text generation
    API_URL = "https://api-inference.huggingface.co/models/gpt2"
    headers = {
        "Authorization": f"Bearer {os.getenv('HUGGINGFACE_TOKEN')}"
    }

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_length": 500,
            "temperature": 0.7,
            "top_p": 0.9,
            "do_sample": True
        }
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()  
        
        result = response.json()
        
        # Handle different response formats
        if isinstance(result, list):
            if len(result) > 0:
                if 'generated_text' in result[0]:
                    return result[0]['generated_text'].strip()
                elif 'generated_texts' in result[0]:
                    return result[0]['generated_texts'][0].strip()
        
        # If we get here, we didn't find the expected response format
        return "Unable to generate AI insights. Using structured analysis instead."
        
    except requests.exceptions.RequestException as e:
        return f"Error connecting to AI service: {str(e)}"
    except Exception as e:
        return f"Error generating suggestions: {str(e)}" 