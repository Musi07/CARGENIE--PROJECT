from flask import Flask, request, jsonify, render_template_string, session
from fuzzywuzzy import process
import csv
import os
import time 
import re 

app = Flask(__name__)
app.secret_key = 'car_genie_secret_key'

# --- Configuration ---
# Exchange rates relative to 1 USD
EXCHANGE_RATES = {
    'USD': 1.0,
    'BDT': 120.0,  # 1 USD = 120 Taka
    'EUR': 0.92,   # 1 USD = 0.92 Euro
    'INR': 83.0    # 1 USD = 83 Rupees
}

# --- Part 1: Data Loading ---
def load_knowledge_base(filename='cars.csv'):
    filepath = os.path.join(os.path.dirname(__file__), filename)
    knowledge_base = []
    try:
        with open(filepath, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                clean_row = {key.strip(): val.strip() for key, val in row.items()}
                knowledge_base.append(clean_row)
        print(f"Knowledge base loaded successfully with {len(knowledge_base)} cars.")
    except FileNotFoundError:
        print(f"Error: The file at '{filepath}' was not found.")
        return None
    except Exception as e:
        print(f"Error loading knowledge base: {e}")
        return None
    return knowledge_base

CAR_DATA = load_knowledge_base()

def get_car_details(model_name, car_data):
    if not car_data:
        return None
    for car in car_data:
        if car['Model'] == model_name:
            return car
    return None

# --- Helper: Detect Currency in User Text ---
def detect_currency(text):
    text = text.lower()
    if 'bdt' in text or 'taka' in text or 'bangladesh' in text:
        return 'BDT'
    if 'eur' in text or 'euro' in text:
        return 'EUR'
    if 'inr' in text or 'rupee' in text or 'india' in text:
        return 'INR'
    if 'usd' in text or 'dollar' in text:
        return 'USD'
    return None 

# --- Helper: Format Price with Conversion ---
def format_price(price_usd, target_currency='USD'):
    try:
        price_val = float(price_usd)
    except (ValueError, TypeError):
        return "N/A"

    rate = EXCHANGE_RATES.get(target_currency, 1.0)
    converted_price = price_val * rate

    if target_currency == 'BDT':
        return f"৳{converted_price:,.0f} BDT"
    elif target_currency == 'EUR':
        return f"€{converted_price:,.0f} EUR"
    elif target_currency == 'INR':
        return f"₹{converted_price:,.0f} INR"
    else:
        return f"${converted_price:,.0f} USD"

# --- 'parse_user_input' (FIXED LOGIC ORDER) ---
def parse_user_input(user_text, car_data):
    user_text = user_text.lower()
    
    # 1. Conversational intents (Highest Priority)
    conv_intents = {
        'greeting': ['hello', 'hi', 'hey', 'salam'],
        'goodbye': ['bye', 'goodbye', 'quit', 'exit'],
        'thanks': ['thanks', 'thank you', 'appreciate it'],
    }
    for intent, keywords in conv_intents.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', user_text):
                return intent, None

    # 2. Recommendation Intent
    if any(k in user_text for k in ['best', 'most', 'cheapest', 'recommend me']):
        criteria = {}
        car_types = set(car['Type'].lower() for car in car_data if 'Type' in car)
        for car_type in car_types:
            if car_type in user_text:
                criteria['type'] = car_type
                break
        if any(k in user_text for k in ['cheapest', 'lowest price']):
            criteria['sort_by'] = 'price_asc'
        elif any(k in user_text for k in ['most efficient', 'best mileage', 'highest mileage']):
            criteria['sort_by'] = 'mileage_desc'
        
        if 'sort_by' in criteria:
            return 'get_recommendation', criteria 

    # 3. Filter Intent
    filter_keywords = ['find', 'show me', 'looking for', 'under', 'over', 'cheaper than', 'less than', 'more than']
    if any(keyword in user_text for keyword in filter_keywords):
        criteria = {}
        car_types = set(car['Type'].lower() for car in car_data if 'Type' in car)
        for car_type in car_types:
            if car_type in user_text:
                criteria['type'] = car_type
                break
        price_match = re.search(r'(\$)?([0-9,]+)', user_text)
        if price_match:
            price_str = price_match.group(2).replace(',', '') 
            try:
                price_num = float(price_str)
                if any(k in user_text for k in ['under', 'less than', 'cheaper than']):
                    criteria['price_less_than'] = price_num
                elif any(k in user_text for k in ['over', 'more than']):
                    criteria['price_more_than'] = price_num
            except ValueError:
                pass 
        companies = set(car['Company'].lower() for car in car_data if 'Company' in car)
        for company in companies:
            if company in user_text:
                criteria['company'] = company
                break
        if criteria: 
            return 'filter_cars', criteria

    # --- LOGIC CHANGE HERE ---
    # We removed the "Company Check" from here.
    # We will check for specific Cars FIRST.
    
    # 4. Check for specific Car Model
    matched_entity = None
    if car_data:
        model_list = [car['Model'] for car in car_data if 'Model' in car]
        best_match, score = process.extractOne(user_text, model_list)
        # High threshold to avoid bad guesses
        if score > 78: 
            matched_entity = best_match 
            
    # 5. Find the task intent (price, mileage, etc.)
    task_intents = {
        'get_price': ['price', 'cost', 'how much'],
        'get_mileage': ['mileage', 'fuel', 'kmpl', 'range', 'milage', 'millage'], 
        'get_engine': ['engine', 'cc', 'horsepower'],
        'get_availability': ['available', 'country', 'countries', 'sell in'],
        'get_all_info': ['tell me about', 'details', 'info', 'information on']
    }
    matched_intent = None
    for intent, keywords in task_intents.items():
        if any(keyword in user_text for keyword in keywords):
            matched_intent = intent
            break

    # --- DECISION TIME ---

    # A. If we found a specific CAR (e.g. "Corolla"), that wins!
    if matched_entity:
        if not matched_intent:
            matched_intent = 'get_all_info' # Default to telling about the car
        return matched_intent, matched_entity

    # B. If we found NO car, *then* check if they asked about a COMPANY (e.g. "Toyota")
    # This prevents "Toyota Corolla" from triggering the Company summary.
    if car_data:
        companies = set(car['Company'].lower() for car in car_data if 'Company' in car)
        for company in companies:
            if company in user_text:
                return 'get_company_info', company 

    # C. Return whatever intent we found (or None)
    return matched_intent, None

# --- 'filter_cars' ---
def filter_cars(criteria, car_data):
    matches = []
    if not car_data:
        return matches
    for car in car_data:
        passes_all_checks = True
        if 'type' in criteria:
            if car.get('Type', '').lower() != criteria['type']:
                passes_all_checks = False
                continue 
        if 'company' in criteria:
            if car.get('Company', '').lower() != criteria['company']:
                passes_all_checks = False
                continue
        if 'price_less_than' in criteria:
            try:
                car_price = float(car.get('Price_Base_USD', 'inf'))
                if car_price >= criteria['price_less_than']:
                    passes_all_checks = False
                    continue
            except (ValueError, TypeError):
                passes_all_checks = False 
                continue
        if 'price_more_than' in criteria:
            try:
                car_price = float(car.get('Price_Base_USD', '-inf'))
                if car_price <= criteria['price_more_than']:
                    passes_all_checks = False
                    continue
            except (ValueError, TypeError):
                passes_all_checks = False 
                continue
        if passes_all_checks:
            matches.append(car)
    return matches

# --- 'generate_response' (UPDATED with currency) ---
def generate_response(intent, details, currency='USD'): 
    if intent == 'greeting':
        return "Hello! How can I help you with car information today?"
    if intent == 'goodbye':
        return "Goodbye! Have a great day."
    if intent == 'thanks':
        return "You're welcome! Is there anything else I can help with?"

    if intent == 'get_company_info':
        company_name = details 
        models = [car['Model'] for car in CAR_DATA if car.get('Company', '').lower() == company_name]
        model_list_str = ", ".join(models)
        
        if company_name == 'tesla':
            return (f"<b>Tesla, Inc.</b> is an American company known for revolutionizing the electric vehicle (EV) market.<br><br>"
                    f"In my database, I have these Tesla models: <b>{model_list_str}</b>.")
        elif company_name == 'ford':
            return (f"<b>Ford Motor Company</b> is one of America's oldest and largest automakers.<br><br>"
                    f"In my database, I have these Ford models: <b>{model_list_str}</b>.")
        elif company_name == 'toyota':
            return (f"<b>Toyota Motor Corporation</b> is known worldwide for reliability and efficiency.<br><br>"
                    f"In my database, I have these Toyota models: <b>{model_list_str}</b>.")
        elif company_name == 'bmw':
            return (f"<b>BMW</b> is a German luxury automaker famous for performance.<br><br>"
                    f"In my database, I have these BMW models: <b>{model_list_str}</b>.")
        elif company_name == 'honda':
             return (f"<b>Honda</b> is known for well-engineered and reliable cars.<br><br>"
                    f"In my database, I have these Honda models: <b>{model_list_str}</b>.")
        else:
             return (f"I don't have a summary for <b>{company_name.title()}</b>, but I do have these models:<br><b>{model_list_str}</b>")

    if intent == 'get_recommendation':
        criteria = details
        matches = []
        if 'type' in criteria:
            matches = filter_cars({'type': criteria['type']}, CAR_DATA)
        else:
            matches = list(CAR_DATA) 
        if not matches:
            return "I'm sorry, I couldn't find any cars for that recommendation."

        sort_key = criteria.get('sort_by')
        if sort_key == 'price_asc':
            try:
                sorted_matches = sorted(matches, key=lambda car: float(car.get('Price_Base_USD', 'inf')))
                top_car = sorted_matches[0]
                type_str = criteria.get('type', 'car')
                price_str = format_price(top_car.get('Price_Base_USD'), currency)
                return f"The cheapest <b>{type_str}</b> in my database is the <b>{top_car['Company']} {top_car['Model']}</b>, starting at <b>{price_str}</b>."
            except Exception as e:
                return "I had trouble sorting the prices for that request."
        if sort_key == 'mileage_desc':
            try:
                sorted_matches = sorted(matches, key=lambda car: float(car.get('Mileage_kmpl', '0')), reverse=True)
                top_car = sorted_matches[0]
                type_str = criteria.get('type', 'car')
                mileage_response = generate_response('get_mileage', top_car, currency) 
                return f"The most efficient <b>{type_str}</b> I found is the <b>{top_car['Company']} {top_car['Model']}</b>.<br>{mileage_response}"
            except Exception as e:
                return "I had trouble sorting the mileage for that request."
        return "I can find the cheapest or most fuel-efficient car. What would you like?"

    if intent == 'filter_cars':
        criteria = details 
        matches = filter_cars(criteria, CAR_DATA)
        if not matches:
            return "I'm sorry, I couldn't find any cars that match your criteria."
        response = f"I found <b>{len(matches)} cars</b> matching your criteria:<br><br>"
        for car in matches:
            price_str = format_price(car.get('Price_Base_USD'), currency)
            response += f"• <b>{car.get('Company')} {car.get('Model')}</b> ({car.get('Type')}) - Starts at {price_str}<br>"
        return response

    car_details = details 
    if not car_details:
        return "I'm sorry, I couldn't find information for that car. Please check the model name."
    if not intent:
         return f"What would you like to know about the {car_details.get('Company')} {car_details.get('Model')}? You can ask about its price, mileage, or for all details."

    company, model = car_details.get('Company'), car_details.get('Model')
    
    if intent == 'get_price':
        base_price = format_price(car_details.get('Price_Base_USD'), currency)
        top_price = format_price(car_details.get('Price_TopTrim_USD'), currency)
        notes = car_details.get('Notes')
        response = f"The {company} {model} starts at around <b>{base_price}</b>."
        if car_details.get('Price_TopTrim_USD'):
            response += f"<br>For higher-end trims, it can go up to approximately <b>{top_price}</b>."
        if notes:
            response += f"<br><br><em>(Note: {notes})</em>"
        return response

    elif intent == 'get_mileage':
        if car_details.get('Engine_CC') == '0': 
            return f"The {company} {model} is an electric vehicle (EV) with an estimated range of <b>{car_details.get('Mileage_kmpl')} km</b> per charge."
        else:
            return f"The {company} {model} has a mileage of <b>{car_details.get('Mileage_kmpl')} kmpl</b>."

    elif intent == 'get_engine':
        if car_details.get('Engine_CC') == '0': 
            return f"The {company} {model} is powered by an <b>Electric Motor</b>."
        else:
            return f"The {company} {model} comes with a <b>{car_details.get('Engine_CC')} CC</b> engine."

    elif intent == 'get_availability':
        return f"The {company} {model} is available in these countries: {car_details.get('Available_Countries')}."
    
    elif intent == 'get_all_info':
        price_response = generate_response('get_price', car_details, currency)
        mileage_response = generate_response('get_mileage', car_details, currency)
        engine_response = generate_response('get_engine', car_details, currency)
        
        image_url = car_details.get('Image_URL')
        image_html = ""
        if image_url:
            image_html = f"""
            <div class="image-wrapper" style="margin-top: 10px;">
                <button class="show-img-btn" onclick="toggleImage(this)">📸 Show Image</button>
                <div class="car-image-container" style="display: none; margin-top: 10px;">
                    <img src="{image_url}" alt="{company} {model}" style="max-width:100%; border-radius: 8px;">
                </div>
            </div>
            """
        
        return (f"Here are the details for the <b>{company} {model}</b>:<br>"
                f"- <b>Year:</b> {car_details.get('Year')}<br>"
                f"- <b>Type:</b> {car_details.get('Type')}<br>"
                f"- <b>Price:</b> {price_response}<br>"
                f"- <b>Efficiency:</b> {mileage_response}<br>"
                f"- <b>Engine:</b> {engine_response}"
                f"{image_html}")
    
    return "I'm sorry, I didn't understand that. You can ask me about price, mileage, or general details of a car."

# --- Part 3: Web Server (Flask) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Car Genie</title>
    <style>
        /* --- Variables for Themes --- */
        :root {
            /* Dark Mode (Default) */
            --dark-bg: #131314;
            --input-bg: #1e1f20;
            --text-color: #e3e3e3;
            --text-secondary: #9b9b9b;
            --chip-bg: #2a2a2d;
            --chip-hover: #3b3b3e;
            --user-msg-bg: #2a2a2d;
            --bot-msg-bg: #2a2a2d;
            --shadow-color: rgba(0,0,0,0.3);
            --btn-hover-bg: #3b3b3e;
        }
        
        /* Light Mode Class */
        .light-mode {
            --dark-bg: #ffffff;
            --input-bg: #f0f2f5;
            --text-color: #1f1f1f;
            --text-secondary: #5f6368;
            --chip-bg: #e3e3e3;
            --chip-hover: #d1d1d1;
            --user-msg-bg: #e3e3e3;
            --bot-msg-bg: #f1f3f4;
            --shadow-color: rgba(0,0,0,0.1);
            --btn-hover-bg: #e0e0e0;
        }

        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            background-color: var(--dark-bg); 
            color: var(--text-color);
            margin: 0; 
            padding: 20px; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            min-height: 95vh; 
            transition: background-color 0.3s, color 0.3s;
        }
        .main-container {
            width: 100%;
            max-width: 800px;
            height: 90vh;
            display: flex;
            flex-direction: column;
            justify-content: flex-end; 
        }
        
        /* Header & Settings */
        .app-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 0 10px 15px 10px; 
            font-size: 1.25rem; 
            font-weight: 500;
            color: var(--text-secondary); 
            position: relative;
        }
        .app-header img {
            height: 28px; 
            width: auto;
        }
        .header-spacer {
            flex-grow: 1; 
        }
        
        /* Icons (Reset, Settings) */
        .header-btn {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 24px;
            cursor: pointer;
            transition: color 0.2s;
            padding: 0 5px;
            line-height: 1;
        }
        .header-btn:hover {
            color: var(--text-color);
        }

        /* Compact Settings Modal */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .modal-content {
            background-color: var(--input-bg);
            padding: 15px; 
            border-radius: 16px; 
            width: 240px; 
            box-shadow: 0 4px 20px var(--shadow-color);
            color: var(--text-color);
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            font-size: 1rem; 
            font-weight: bold;
        }
        .close-modal {
            cursor: pointer;
            font-size: 20px;
        }
        .setting-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0; 
            border-bottom: 1px solid var(--chip-bg);
            font-size: 0.9rem; 
        }
        .setting-item:last-child {
            border-bottom: none;
        }
        
        /* Compact Toggle Switch */
        .switch {
            position: relative;
            display: inline-block;
            width: 40px;
            height: 20px;
            transform: scale(0.8); 
        }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: #ccc;
            transition: .4s;
            border-radius: 34px;
        }
        .slider:before {
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 2px;
            bottom: 2px;
            background-color: white;
            transition: .4s;
            border-radius: 50%;
        }
        input:checked + .slider { background-color: #2196F3; }
        input:checked + .slider:before { transform: translateX(20px); }
        
        /* Compact Clear Button */
        .clear-btn {
            width: 100%; 
            background-color: #ff4d4d; 
            color: white; 
            border: none;
            border-radius: 12px;
            padding: 6px 10px;
            font-size: 12px;
            cursor: pointer;
        }
        
        /* Normal Chat Styles */
        .chat-box { 
            flex-grow: 1; 
            padding: 20px 0; 
            overflow-y: auto; 
            display: flex; 
            flex-direction: column; 
            gap: 15px; 
            scrollbar-width: thin;
            scrollbar-color: var(--chip-bg) transparent;
        }
        .greeting {
            font-size: 3.5rem;
            font-weight: 500;
            text-align: center;
            color: var(--text-secondary);
            margin: auto; 
        }
        .greeting img { display: none; }
        .message { 
            padding: 12px 18px; 
            border-radius: 20px; 
            max-width: 75%; 
            line-height: 1.5; 
            word-wrap: break-word;
        }
        .user-message { 
            background: var(--user-msg-bg); 
            color: var(--text-color); 
            align-self: flex-end; 
            border-radius: 20px 20px 5px 20px; 
        }
        .bot-message { 
            background-color: var(--bot-msg-bg); 
            color: var(--text-color); 
            align-self: flex-start; 
            border-radius: 20px 20px 20px 5px; 
        }
        
        /* New Show/Hide Button Styles */
        .show-img-btn {
            background-color: var(--chip-bg);
            color: var(--text-color);
            border: 1px solid var(--chip-hover);
            border-radius: 12px;
            padding: 6px 12px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: background-color 0.2s;
            margin-top: 5px;
        }
        .show-img-btn:hover {
            background-color: var(--chip-hover);
        }

        /* Typing Indicator */
        .typing-indicator {
            display: flex;
            align-items: center;
            padding: 8px 0; 
        }
        .typing-indicator div {
            width: 6px; 
            height: 6px; 
            border-radius: 50%;
            background-color: var(--text-secondary);
            animation: typing-bounce 1.2s infinite ease-in-out;
            margin: 0 2px; 
        }
        .typing-indicator div:nth-child(1) { animation-delay: -0.24s; }
        .typing-indicator div:nth-child(2) { animation-delay: -0.12s; }
        @keyframes typing-bounce {
            0%, 80%, 100% { transform: scale(0); } 
            40% { transform: scale(1.0); }
        }
        
        /* Input Area */
        .input-container {
            position: relative;
            display: flex;
            align-items: center;
            background-color: var(--input-bg);
            border-radius: 28px;
            padding: 5px 5px 5px 20px;
            box-shadow: 0 4px 12px var(--shadow-color);
        }
        #userInput { 
            flex-grow: 1; 
            background: transparent;
            border: none;
            color: var(--text-color);
            font-size: 16px; 
            outline: none; 
            padding: 15px 0;
            line-height: 1.5;
        }
        .input-icon-btn {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 18px;
            padding: 10px;
            cursor: pointer;
            transition: color 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .input-icon-btn:hover { color: var(--text-color); }
        
        #sendButton { 
            background-color: var(--chip-bg); 
            color: var(--text-color); 
            border: none; 
            border-radius: 50%; 
            width: 44px;
            height: 44px;
            margin-left: 10px; 
            cursor: pointer; 
            font-size: 20px; 
            display: flex;
            justify-content: center;
            align-items: center;
            transition: background-color 0.2s;
        }
        #sendButton:hover { background-color: var(--btn-hover-bg); }
        
        /* Suggestion Chips */
        .suggestion-area {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            padding: 20px 0;
            justify-content: center; 
        }
        .suggestion-btn {
            background-color: var(--chip-bg);
            color: var(--text-color);
            border: none;
            border-radius: 16px;
            padding: 8px 14px;
            font-size: 14px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .suggestion-btn:hover { background-color: var(--btn-hover-bg); }

        /* Font Size Classes */
        .large-font { font-size: 1.2em; }
    </style>
</head>
<body>
    <!-- Settings Modal -->
    <div class="modal-overlay" id="settingsModal">
        <div class="modal-content">
            <div class="modal-header">
                <span>Settings</span>
                <span class="close-modal" onclick="toggleSettings()">×</span>
            </div>
            
            <div class="setting-item">
                <span>Light Mode</span>
                <label class="switch">
                    <input type="checkbox" id="themeToggle">
                    <span class="slider"></span>
                </label>
            </div>

            <div class="setting-item">
                <span>Large Text</span>
                <label class="switch">
                    <input type="checkbox" id="fontToggle">
                    <span class="slider"></span>
                </label>
            </div>

            <div class="setting-item">
                <span>Show Logo</span>
                <label class="switch">
                    <input type="checkbox" id="logoToggle" checked>
                    <span class="slider"></span>
                </label>
            </div>

            <div class="setting-item" style="justify-content: center; padding-top: 10px;">
                <button class="clear-btn" onclick="clearChatHistory()">
                    Clear Chat History
                </button>
            </div>
        </div>
    </div>

    <div class="main-container" id="mainContainer">
        
        <!-- HEADER: Settings (Left), Logo, Title, Reset (Right) -->
        <div class="app-header">
            <button class="header-btn" title="Settings" onclick="toggleSettings()">⚙️</button>
            
            <img src="{{ url_for('static', filename='images/logo.png') }}" alt="Car Genie Logo" id="appLogo">
            <span>Car Genie</span>
            
            <div class="header-spacer"></div>
            
            <button id="resetButton" class="header-btn" title="Back to Home" style="display: none;" onclick="resetChat()">&#8634;</button> 
        </div>
        
        <div class="chat-box" id="chatBox">
            <div class="greeting" id="greeting">Hello, User!</div>
        </div>
        
        <div class="prompt-area">
            <div class="input-container">
                <button class="input-icon-btn" title="Attach File">＋</button>
                <input type="text" id="userInput" placeholder="Ask Car Genie..." autocomplete="off">
                <button class="input-icon-btn" title="Voice Input">🎤</button>
                <button id="sendButton" title="Send">➤</button> 
            </div>
            
            <div class="suggestion-area" id="suggestionArea">
                <button class="suggestion-btn">Find cars under $30000</button>
                <button class="suggestion-btn">Show me all SUVs</button>
                <button class="suggestion-btn">Cheapest car?</button>
                <button class="suggestion-btn">Most efficient car?</button>
            </div>
        </div>

    </div>

    <script>
        const chatBox = document.getElementById('chatBox');
        const userInput = document.getElementById('userInput');
        const sendButton = document.getElementById('sendButton');
        const greeting = document.getElementById('greeting');
        const suggestionArea = document.getElementById('suggestionArea');
        const resetButton = document.getElementById('resetButton');
        
        // Settings Elements
        const settingsModal = document.getElementById('settingsModal');
        const themeToggle = document.getElementById('themeToggle');
        const fontToggle = document.getElementById('fontToggle');
        const logoToggle = document.getElementById('logoToggle');
        const appLogo = document.getElementById('appLogo');
        const mainContainer = document.getElementById('mainContainer');

        // --- Toggle Image Function (Global Scope) ---
        window.toggleImage = function(btn) {
            const imgContainer = btn.nextElementSibling;
            if (imgContainer.style.display === 'none') {
                imgContainer.style.display = 'block';
                btn.textContent = '🙈 Hide Image';
            } else {
                imgContainer.style.display = 'none';
                btn.textContent = '📸 Show Image';
            }
        }

        // --- Settings Logic ---
        function toggleSettings() {
            if (settingsModal.style.display === 'flex') {
                settingsModal.style.display = 'none';
            } else {
                settingsModal.style.display = 'flex';
            }
        }

        themeToggle.addEventListener('change', function() {
            if (this.checked) {
                document.body.classList.add('light-mode');
            } else {
                document.body.classList.remove('light-mode');
            }
        });

        fontToggle.addEventListener('change', function() {
            if (this.checked) {
                mainContainer.classList.add('large-font');
            } else {
                mainContainer.classList.remove('large-font');
            }
        });

        logoToggle.addEventListener('change', function() {
            if (this.checked) {
                appLogo.style.display = 'block';
            } else {
                appLogo.style.display = 'none';
            }
        });

        function clearChatHistory() {
            chatBox.innerHTML = ''; 
            chatBox.appendChild(greeting); 
            greeting.style.display = 'block'; 
            suggestionArea.style.display = 'flex'; 
            resetButton.style.display = 'none';
            fetch('/reset_memory', { method: 'POST' });
            toggleSettings(); // Close modal
        }

        // Close modal if clicked outside
        window.onclick = function(event) {
            if (event.target == settingsModal) {
                settingsModal.style.display = "none";
            }
        }

        // --- Chat Logic ---
        const suggestionButtons = document.querySelectorAll('.suggestion-btn');
        suggestionButtons.forEach(button => {
            button.addEventListener('click', () => {
                const suggestionText = button.innerText;
                userInput.value = suggestionText;
                sendMessage();
            });
        });
        
        async function sendMessage() {
            const userText = userInput.value.trim();
            if (userText === '') return;

            if (greeting.style.display !== 'none') {
                greeting.style.display = 'none';
                suggestionArea.style.display = 'none';
                resetButton.style.display = 'block'; 
            }

            addMessage(userText, 'user-message');
            userInput.value = '';

            try {
                const typingIndicatorHTML = `
                    <div class="typing-indicator">
                        <div></div>
                        <div></div>
                        <div></div>
                    </div>`;
                const typingIndicator = addMessage(typingIndicatorHTML, 'bot-message');
                
                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: userText })
                });
                const data = await response.json();
                
                chatBox.removeChild(typingIndicator);
                addMessage(data.answer, 'bot-message');

            } catch (error) {
                console.error('Error:', error);
                addMessage('Sorry, something went wrong. Please try again.', 'bot-message');
            }
        }

        function addMessage(text, className) {
            const messageElement = document.createElement('div');
            messageElement.classList.add('message', className);
            messageElement.innerHTML = text; 
            chatBox.appendChild(messageElement);
            chatBox.scrollTop = chatBox.scrollHeight;
            return messageElement; 
        }
        
        function resetChat() {
            clearChatHistory();
        }
        
        sendButton.addEventListener('click', sendMessage);
        resetButton.addEventListener('click', resetChat); 
        
        userInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault(); 
                sendMessage();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/reset_memory', methods=['POST'])
def reset_memory():
    session.pop('last_car_model', None)
    return '', 204

@app.route('/ask', methods=['POST'])
def ask():
    if not CAR_DATA:
        return jsonify({'answer': 'I am sorry, my knowledge base of cars could not be loaded.'})

    user_message = request.json['message']
    
    # 1. Detect currency from message
    req_currency = detect_currency(user_message)
    if not req_currency:
        req_currency = 'USD' # Default to USD if no specific currency mentioned

    intent, details = parse_user_input(user_message, CAR_DATA)
    car_details = None
    
    last_car_context = session.get('last_car_model')

    if intent in ['get_price', 'get_mileage', 'get_engine', 'get_all_info', 'get_availability'] and not details:
        if last_car_context:
            details = last_car_context
            car_details = get_car_details(details, CAR_DATA)

    if intent not in ['greeting', 'goodbye', 'thanks', 'filter_cars', 'get_recommendation', 'get_company_info']:
        if details: 
            car_details = get_car_details(details, CAR_DATA)
            session['last_car_model'] = details
        response_text = generate_response(intent, car_details, req_currency)
    elif intent in ['filter_cars', 'get_recommendation']:
        response_text = generate_response(intent, details, req_currency)
    elif intent == 'get_company_info':
        response_text = generate_response(intent, details, req_currency)
    else:
        response_text = generate_response(intent, None, req_currency)
    
    time.sleep(1.5) 
    return jsonify({'answer': response_text})

if __name__ == '__main__':
    app.run(debug=True)