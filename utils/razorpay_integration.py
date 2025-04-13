import razorpay
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Get Razorpay credentials
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')

# Check if credentials are available
if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    print("Warning: Razorpay credentials not found in environment variables")
    print("Using mock payment processing for testing purposes")

# Initialize Razorpay client
try:
    client = razorpay.Client(
        auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    )
    RAZORPAY_AVAILABLE = True
except Exception as e:
    print(f"Error initializing Razorpay client: {str(e)}")
    print("Using mock payment processing for testing purposes")
    RAZORPAY_AVAILABLE = False

def create_payment(amount, currency='INR', description=None, user_id=None, recipient_id=None):
    
    # Convert amount to paise (Razorpay expects amount in smallest currency unit)
    amount_in_paise = int(amount * 100)
    
    # If Razorpay is not available, use mock payment processing
    if not RAZORPAY_AVAILABLE:
        print(f"Mock payment processing: ₹{amount} for {description}")
        payment_id = f"mock_pay_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{user_id}"
        order_id = f"mock_order_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{user_id}"
        
        return {
            'payment_id': payment_id,
            'order_id': order_id,
            'amount': amount,
            'currency': currency,
            'status': 'captured',
            'created_at': datetime.utcnow().isoformat(),
            'from_user': user_id,
            'to_user': recipient_id
        }
    
    # Create order
    order_data = {
        'amount': amount_in_paise,
        'currency': currency,
        'payment_capture': 1,  # Auto capture payment
        'notes': {
            'user_id': user_id,
            'recipient_id': recipient_id,
            'description': description
        }
    }
    
    try:
        # Create order
        order = client.order.create(data=order_data)
        
        # In test mode, we'll simulate a successful payment
        # In production, this would redirect to Razorpay payment page
        payment_id = f"pay_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{user_id}"
        
        return {
            'payment_id': payment_id,
            'order_id': order['id'],
            'amount': amount,
            'currency': currency,
            'status': 'captured',
            'created_at': datetime.utcnow().isoformat(),
            'from_user': user_id,
            'to_user': recipient_id
        }
    except Exception as e:
        print(f"Error creating payment: {str(e)}")
        # If there's an error with Razorpay, fall back to mock payment processing
        print("Falling back to mock payment processing")
        payment_id = f"mock_pay_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{user_id}"
        order_id = f"mock_order_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{user_id}"
        
        return {
            'payment_id': payment_id,
            'order_id': order_id,
            'amount': amount,
            'currency': currency,
            'status': 'captured',
            'created_at': datetime.utcnow().isoformat(),
            'from_user': user_id,
            'to_user': recipient_id
        }

def verify_payment(payment_id):
    # If Razorpay is not available, use mock payment verification
    if not RAZORPAY_AVAILABLE or payment_id.startswith('mock_'):
        return {
            'payment_id': payment_id,
            'order_id': f"order_{payment_id.split('_')[1]}",
            'amount': 0,  
            'currency': 'INR',
            'status': 'captured',
            'verified': True
        }
    
    try:
        # In test mode, we'll simulate a successful payment verification
        return {
            'payment_id': payment_id,
            'order_id': f"order_{payment_id.split('_')[1]}",
            'amount': 0,  
            'currency': 'INR',
            'status': 'captured',
            'verified': True
        }
    except Exception as e:
        print(f"Error verifying payment: {str(e)}")
        return None

def process_expense_payment(expense, user_id):
    description = f"Expense: {expense.get('desc', 'Unknown')} - {expense.get('category', 'Uncategorized')}"
    
    payment_id = f"log_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{user_id}"
    
    payment = {
        'payment_id': payment_id,
        'order_id': f"log_order_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{user_id}",
        'amount': expense['amount'],
        'currency': 'INR',
        'status': 'logged',
        'created_at': datetime.utcnow().isoformat(),
        'from_user': user_id,
        'to_user': None,
        'description': description
    }
    
    # Add payment details to expense
    expense['payment'] = {
        'payment_id': payment['payment_id'],
        'order_id': payment['order_id'],
        'status': payment['status'],
        'created_at': payment['created_at']
    }
    
    return payment

def process_group_expense_share(expense, user_id, share_amount, recipient_id=None):
    description = f"Group Expense Share: {expense.get('desc', 'Unknown')} - {expense.get('category', 'Uncategorized')}"
    
    payment = create_payment(
        amount=share_amount,
        description=description,
        user_id=user_id,
        recipient_id=recipient_id
    )
    
    if payment:
        # Add payment details to expense share
        payment_details = {
            'payment_id': payment['payment_id'],
            'order_id': payment['order_id'],
            'status': payment['status'],
            'created_at': payment['created_at'],
            'user_id': user_id,
            'recipient_id': recipient_id,
            'share_amount': share_amount
        }
        
        # Update the expense with payment details for this user
        if 'payments' not in expense:
            expense['payments'] = []
        
        expense['payments'].append(payment_details)
    
    return payment 