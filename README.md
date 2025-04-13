# ExpenseBot

Managing everyday expenses can quickly become overwhelming with the number of transactions we make. To simplify this, we’ve built a **Smart Expense Bot that integrates directly with WhatsApp**, eliminating the need to install another app or create new accounts. Just open WhatsApp and start tracking your expenses with ease!

Our bot is built using **Python Flask** for the backend, with **Ngrok** to expose the local server, **Twilio WhatsApp API** for messaging integration and **MongoDB** for database.

The bot offers two modes:
**Personal Expense Mode:** Add expenses, view all entries, visualize category-wise spending using a pie chart, set and view budgets for different categories and get AI-assisted reviews and suggestions.
**Group Expense Mode:** Create groups, add members, track group expenses, view group-wise spending details, see visual represenations of expenses and settle/pay these expenses wihting the bot itself.

**Features**
- Personal expense tracking
- Group expense management
- Budgeting
- Expense categorization
- Visual charts for expense analysis
- AI-powered expense insights
- Budget setting and tracking

## Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables in `.env`:
   ```
   MONGODB_URI=mongodb://localhost:27017/
   MONGODB_DB=expense_tracker
   HUGGINGFACE_TOKEN=your_huggingface_token
   RAZORPAY_KEY_ID=your_razorpay_key_id
   RAZORPAY_KEY_SECRET=your_razorpay_key_secret
   ```
4. Run the application:
   ```
   python app.py
   ```

## Usage
Send a message to the WhatsApp number associated with this application to start tracking your expenses.
