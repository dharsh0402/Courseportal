from flask import Flask, render_template, request, redirect, url_for, session
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import requests
from waitress import serve

app = Flask(__name__)

app.secret_key = 'Secret_key'

# ExchangeRatesAPI key and base URL
api_key = '31f2e5a47b509a44c492b2033c80f708'
base_url = 'http://api.exchangeratesapi.io/v1/'

# Connecting to MongoDB Atlas
uri = "mongodb+srv://dharshan2104:dharshan0402@swiftswap.kcnspyk.mongodb.net/?retryWrites=true&w=majority"
# Creating a new client and connecting to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Confirming a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You are now successfully connected to MongoDB!")
    print(" Goto url : http://127.0.0.1:5002/")
except Exception as e:
    print(e)

# Selecting the database and collections
db = client['swiftswap']
users_collection = db['users']
conversion_history_collection = db['conversion_history']

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Checking if the username is not already taken
        if not users_collection.find_one({'username': username}):
            # Storing the new user with plain text password in MongoDB
            new_user = {'username': username, 'password': password}
            users_collection.insert_one(new_user)
            session['username'] = username
            return redirect(url_for('home'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Checking for user credentials in MongoDB
        user = users_collection.find_one({'username': username})

        if user and user['password'] == password:
            session['username'] = user['username']
            return redirect(url_for('home'))

    return render_template('login.html', error="Invalid credentials")

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/')
def home():
    if 'username' in session:
        currencies = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'SEK', 'NZD']
        return render_template('converter.html', currencies=currencies)
    
    return redirect(url_for('login'))

@app.route('/convert', methods=['POST'])
def convert():
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        amount = float(request.form['amount'])
        from_currency = request.form['from_currency']
        to_currency = request.form['to_currency']

        # Get live exchange rate using ExchangeRatesAPI
        exchange_rate = get_exchange_rate(from_currency, to_currency)

        if exchange_rate is not None:
            converted_amount = round(amount * exchange_rate, 2)

            # Storing the conversion history in MongoDB
            conversion_entry = {
                'username': session['username'],
                'from_currency': from_currency,
                'to_currency': to_currency,
                'amount': amount,
                'converted_amount': converted_amount
            }
            conversion_history_collection.insert_one(conversion_entry)

            return render_template('converter.html', result=converted_amount)

    except Exception as e:
        print(f"Error during conversion: {e}")

    # Handle any errors or redirect to the converter page with an error message
    return render_template('converter.html', error="Invalid conversion data")

def get_exchange_rate(from_currency, to_currency):
    try:
        # Using ExchangeRatesAPI
        url = f"{base_url}convert?from={from_currency}&to={to_currency}&amount=1&access_key={api_key}"
        response = requests.get(url)
        data = response.json()

        # Check if the API request was successful
        if data.get('success'):
            return data.get('result')

        # If request was not successful, print the error message for debugging
        print(f"API request was not successful. Error: {data.get('error')}")
        return None

    except Exception as e:
        print(f"Error fetching exchange rate: {e}")
        return None


@app.route('/history')
def conversion_history():
    if 'username' in session:
        # to retrieve conversion history for the current user from MongoDB
        user_history = conversion_history_collection.find({'username': session['username']})
        return render_template('history.html', user_history=user_history)

    return redirect(url_for('login'))

if __name__ == '__main__':
    serve(app, host='127.0.0.1', port=5002)


