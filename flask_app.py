from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from fuzzywuzzy import process
import csv
import os
import time 
import re 

app = Flask(__name__)

# --- Part 1: Data Loading ---
def load_knowledge_base(filename='cars.csv'):
    """Loads car data. The path is relative to this 'app.py' file."""
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
        print(f"Error: The file at '{filepath}' was not found. Make sure cars.csv is in the same folder as flask_app.py.")
        return None
    except Exception as e:
        print(f"An error occurred loading the knowledge base: {e}")
        return None
    return knowledge_base

CAR_DATA = load_knowledge_base()

def get_car_details(model_name, car_data):
    """Finds the full details for a car given its model name."""
    if not car_data:
        return None
    for car in car_data:
        if car['Model'] == model_name:
            return car
    return None

# --- 'parse_user_input' for Recommendations ---
def parse_user_input(user_text, car_data):
    """Parses user input to find intent and entity/criteria."""
    user_text = user_text.lower()
    
    # Check for conversational intents first
    conv_intents = {
        'greeting': ['hello', 'hi', 'hey', 'salam'],
        'goodbye': ['bye', 'goodbye', 'quit', 'exit'],
        'thanks': ['thanks', 'thank you', 'appreciate it'],
    }
    for intent, keywords in conv_intents.items():
        if any(keyword in user_text for keyword in keywords):
            return intent, None

    # --- NEW: Check for Recommendation Intent (before filter) ---
    if any(k in user_text for k in ['best', 'most', 'cheapest', 'recommend me']):
        criteria = {}
        
        # Check for car type
        car_types = set(car['Type'].lower() for car in car_data if 'Type' in car)
        for car_type in car_types:
            if car_type in user_text:
                criteria['type'] = car_type
                break
        
        # Check for sorting keyword
        if any(k in user_text for k in ['cheapest', 'lowest price']):
            criteria['sort_by'] = 'price_asc'
        elif any(k in user_text for k in ['most efficient', 'best mileage', 'highest mileage']):
            criteria['sort_by'] = 'mileage_desc'
        
        if 'sort_by' in criteria:
            return 'get_recommendation', criteria # e.g., {'type': 'suv', 'sort_by': 'price_asc'}
    # --- End of Recommendation Intent ---

    # --- Check for Filter Intent ---
    filter_keywords = ['find', 'show me', 'looking for', 'under', 'over', 'cheaper than', 'less than', 'more than']
    if any(keyword in user_text for keyword in filter_keywords):
        criteria = {}
        
        # 1. Find Type criteria
        car_types = set(car['Type'].lower() for car in car_data if 'Type' in car)
        for car_type in car_types:
            if car_type in user_text:
                criteria['type'] = car_type
                break
        
        # 2. Find Price criteria (using Regular Expressions)
        price_match = re.search(r'(\$)?([0-9,]+)', user_text)
        if price_match:
            price_str = price_match.group(2).replace(',', '') # Get '30000'
            try:
                price_num = float(price_str)
                
                if any(k in user_text for k in ['under', 'less than', 'cheaper than']):
                    criteria['price_less_than'] = price_num
                elif any(k in user_text for k in ['over', 'more than']):
                    criteria['price_more_than'] = price_num
            except ValueError:
                pass # Not a valid number

        # 3. Find Company criteria
        companies = set(car['Company'].lower() for car in car_data if 'Company' in car)
        for company in companies:
            if company in user_text:
                criteria['company'] = company
                break
        
        if criteria: # If we found any criteria, it's a filter intent
            return 'filter_cars', criteria

    # --- End of Filter Intent ---

    # If not filter, find the car entity
    matched_entity = None
    if car_data:
        model_list = [car['Model'] for car in car_data if 'Model' in car]
        best_match, score = process.extractOne(user_text, model_list)
        if score > 50: # Confidence threshold
            matched_entity = best_match # This is the correct model name, e.g., "Mustang"
            
    # Now find the task intent
    task_intents = {
        'get_price': ['price', 'cost', 'how much'],
        'get_mileage': ['mileage', 'fuel', 'kmpl', 'range'],
        'get_engine': ['engine', 'cc', 'horsepower'],
        'get_availability': ['available', 'country', 'countries', 'sell in'],
        'get_all_info': ['tell me about', 'details', 'info', 'information on']
    }
    matched_intent = None
    for intent, keywords in task_intents.items():
        if any(keyword in user_text for keyword in keywords):
            matched_intent = intent
            break
            
    # --- *** NEW LOGIC BLOCK! *** ---
    # If we found an intent (like 'get_all_info') but NO car *model*...
    if matched_intent and not matched_entity:
        # ...let's check if they just gave us a *company* name.
        companies = set(car['Company'].lower() for car in car_data if 'Company' in car)
        for company in companies:
            if company in user_text:
                # They did! This is a 'get_company_info' intent.
                return 'get_company_info', company # e.g., 'get_company_info', 'tesla'
    # --- *** END OF NEW LOGIC BLOCK *** ---
            
    # If we found a car but no specific task, default to 'get_all_info'
    if not matched_intent and matched_entity:
        matched_intent = 'get_all_info'
        
    return matched_intent, matched_entity

# --- 'filter_cars' Search Engine Function ---
def filter_cars(criteria, car_data):
    """Filters the car database based on given criteria."""
    matches = []
    if not car_data:
        return matches
        
    for car in car_data:
        passes_all_checks = True
        
        # 1. Check Type
        if 'type' in criteria:
            if car.get('Type', '').lower() != criteria['type']:
                passes_all_checks = False
                continue 
        
        # 2. Check Company
        if 'company' in criteria:
            if car.get('Company', '').lower() != criteria['company']:
                passes_all_checks = False
                continue
        
        # 3. Check Price (Less Than)
        if 'price_less_than' in criteria:
            try:
                car_price = float(car.get('Price_Base_USD', 'inf'))
                if car_price >= criteria['price_less_than']:
                    passes_all_checks = False
                    continue
            except (ValueError, TypeError):
                passes_all_checks = False 
                continue

        # 4. Check Price (More Than)
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


# --- 'generate_response' to handle recommendations ---
def generate_response(intent, details): # 'details' is either car_details (dict), criteria (dict), company_name (str), or None
    # Handle conversational intents first
    if intent == 'greeting':
        return "Hello! How can I help you with car information today?"
    if intent == 'goodbye':
        return "Goodbye! Have a great day."
    if intent == 'thanks':
        return "You're welcome! Is there anything else I can help with?"

    # --- *** NEW: Handle Company Info Intent *** ---
    if intent == 'get_company_info':
        company_name = details # 'details' is the company name string
        
        # Get a list of models for this company
        models = [car['Model'] for car in CAR_DATA if car.get('Company', '').lower() == company_name]
        model_list_str = ", ".join(models)
        
        # Hard-coded summaries
        if company_name == 'tesla':
            return (f"<b>Tesla, Inc.</b> is an American company known for revolutionizing the electric vehicle (EV) market. "
                    f"They focus on high-performance electric cars with advanced technology and software.<br><br>"
                    f"In my database, I have these Tesla models: <b>{model_list_str}</b>.")
        
        elif company_name == 'ford':
            return (f"<b>Ford Motor Company</b> is one of America's oldest and largest automakers, founded in 1903. "
                    f"They are famous for mass-producing cars and for iconic models like the Mustang and F-150 truck.<br><br>"
                    f"In my database, I have these Ford models: <b>{model_list_str}</b>.")
        
        elif company_name == 'toyota':
            return (f"<b>Toyota Motor Corporation</b> is a Japanese multinational manufacturer known worldwide for its reliability, efficiency, and quality vehicles "
                    f"like the Camry and Corolla.<br><br>"
                    f"In my database, I have these Toyota models: <b>{model_list_str}</b>.")

        elif company_name == 'bmw':
            return (f"<b>BMW (Bayerische Motoren Werke AG)</b> is a German luxury automaker famous for its performance, "
                    f"high-quality engineering, and distinctive 'kidney grille' design.<br><br>"
                    f"In my database, I have these BMW models: <b>{model_list_str}</b>.")
        
        elif company_name == 'honda':
             return (f"<b>Honda Motor Co., Ltd.</b> is a Japanese public company known for its well-engineered and reliable cars and motorcycles, "
                    f"with popular models like the Civic and CR-V.<br><br>"
                    f"In my database, I have these Honda models: <b>{model_list_str}</b>.")
        
        # A fallback for other companies in our DB
        elif company_name in [car['Company'].lower() for car in CAR_DATA if 'Company' in car]:
             return (f"I don't have a detailed summary for <b>{company_name.title()}</b>, but I do have these models in my database:<br>"
                    f"<b>{model_list_str}</b>")
    # --- *** End of Company Info Intent *** ---

    # --- Handle Recommendation Intent ---
    if intent == 'get_recommendation':
        criteria = details
        matches = []
        
        # First, filter by type if provided (e.g., "cheapest SUV")
        if 'type' in criteria:
            matches = filter_cars({'type': criteria['type']}, CAR_DATA)
        else:
            matches = list(CAR_DATA) # Start with all cars

        if not matches:
            return "I'm sorry, I couldn't find any cars for that recommendation."

        # Now, sort the matches
        sort_key = criteria.get('sort_by')
        
        if sort_key == 'price_asc':
            try:
                # Sort by Price_Base_USD (float), handling errors
                sorted_matches = sorted(
                    matches, 
                    key=lambda car: float(car.get('Price_Base_USD', 'inf'))
                )
                top_car = sorted_matches[0]
                type_str = criteria.get('type', 'car')
                return f"The cheapest <b>{type_str}</b> in my database is the <b>{top_car['Company']} {top_car['Model']}</b>, starting at <b>${top_car['Price_Base_USD']}</b>."
            except Exception as e:
                print(f"Error sorting by price: {e}")
                return "I had trouble sorting the prices for that request."

        if sort_key == 'mileage_desc':
            try:
                # Sort by Mileage_kmpl (float, descending), handling errors
                sorted_matches = sorted(
                    matches, 
                    key=lambda car: float(car.get('Mileage_kmpl', '0')), 
                    reverse=True
                )
                top_car = sorted_matches[0]
                type_str = criteria.get('type', 'car')
                # Re-use our smart mileage logic!
                mileage_response = generate_response('get_mileage', top_car) 
                return f"The most efficient <b>{type_str}</b> I found is the <b>{top_car['Company']} {top_car['Model']}</b>.<br>{mileage_response}"
            except Exception as e:
                print(f"Error sorting by mileage: {e}")
                return "I had trouble sorting the mileage for that request."
        
        return "I can find the cheapest or most fuel-efficient car. What would you like?"

    # --- Handle Filter Intent ---
    if intent == 'filter_cars':
        criteria = details # In this case, 'details' is our criteria dictionary
        matches = filter_cars(criteria, CAR_DATA)
        
        if not matches:
            return "I'm sorry, I couldn't find any cars that match your criteria."
        
        # Build a nice list of the cars we found
        response = f"I found <b>{len(matches)} cars</b> matching your criteria:<br><br>"
        for car in matches:
            response += f"• <b>{car.get('Company')} {car.get('Model')}</b> ({car.get('Type')}) - Starts at ${car.get('Price_Base_USD')}<br>"
        return response
    # --- End of Filter Intent ---

    # Handle fallback cases
    car_details = details # Now we know 'details' is car_details
    if not car_details:
        return "I'm sorry, I couldn't find information for that car. Please check the model name."
    if not intent:
         return f"What would you like to know about the {car_details.get('Company')} {car_details.get('Model')}? You can ask about its price, mileage, or for all details."

    # --- Handle "Smart" Car-Specific Responses ---
    company, model = car_details.get('Company'), car_details.get('Model')
    
    # 1. SMART RESPONSE: get_price
    if intent == 'get_price':
        base_price = car_details.get('Price_Base_USD')
        top_price = car_details.get('Price_TopTrim_USD')
        notes = car_details.get('Notes')
        
        response = f"The {company} {model} starts at around <b>${base_price} USD</b>."
        if top_price:
            response += f"<br>For higher-end trims, it can go up to approximately <b>${top_price} USD</b>."
        if notes:
            response += f"<br><br><em>(Note: {notes})</em>"
        return response

    # 2. SMART RESPONSE: get_mileage (handles EVs)
    elif intent == 'get_mileage':
        if car_details.get('Engine_CC') == '0': # Check if it's an EV
            return f"The {company} {model} is an electric vehicle (EV) with an estimated range of <b>{car_details.get('Mileage_kmpl')} km</b> per charge."
        else:
            return f"The {company} {model} has a mileage of <b>{car_details.get('Mileage_kmpl')} kmpl</b>."

    # 3. SMART RESPONSE: get_engine (handles EVs)
    elif intent == 'get_engine':
        if car_details.get('Engine_CC') == '0': # Check if it's an EV
            return f"The {company} {model} is powered by an <b>Electric Motor</b>."
        else:
            return f"The {company} {model} comes with a <b>{car_details.get('Engine_CC')} CC</b> engine."

    elif intent == 'get_availability':
        return f"The {company} {model} is available in these countries: {car_details.get('Available_Countries')}."
    
    # 4. SMART RESPONSE: get_all_info (with new price data and working image)
    elif intent == 'get_all_info':
        # Re-use the smart logic from above
        price_response = generate_response('get_price', car_details)
        mileage_response = generate_response('get_mileage', car_details)
        engine_response = generate_response('get_engine', car_details)
        
        image_url = car_details.get('Image_URL')
        image_html = f'<img src="{image_url}" alt="{company} {model}" style="max-width:100%; border-radius: 8px; margin-top: 10px;">' if image_url else ""
        
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
        :root {
            --dark-bg: #131314;
            --input-bg: #1e1f20;
            --text-color: #e3e3e3;
            --text-secondary: #9b9b9b;
            --chip-bg: #2a2a2d;
            --chip-hover: #3b3b3e;
            --accent-blue: #8ab4f8;
            --user-message-bg: #2a2a2d; /* User messages are dark grey */
            --bot-message-bg: #2a2a2d; /* Bot messages are also dark grey */
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
        }
        .main-container {
            width: 100%;
            max-width: 800px;
            height: 90vh;
            display: flex;
            flex-direction: column;
            justify-content: flex-end; 
        }
        
        /* Persistent App Header */
        .app-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 0 10px 15px 10px; 
            font-size: 1.25rem; /* 20px */
            font-weight: 500;
            color: var(--text-secondary); 
        }
        .app-header img {
            height: 28px; 
            width: auto;
        }
        
        /* --- NEW: Spacer and Reset Button Styles --- */
        .header-spacer {
            flex-grow: 1; /* This pushes the reset button to the right */
        }
        #resetButton {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 24px;
            cursor: pointer;
            transition: color 0.2s;
            padding: 0;
            line-height: 1;
        }
        #resetButton:hover {
            color: var(--text-color);
        }
        /* --- End of New Styles --- */


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
        .greeting img {
           display: none; 
        }
        .message { 
            padding: 12px 18px; 
            border-radius: 20px; 
            max-width: 75%; 
            line-height: 1.5; 
            word-wrap: break-word;
        }
        .user-message { 
            background: var(--user-message-bg); 
            color: var(--text-color); 
            align-self: flex-end; 
            border-radius: 20px 20px 5px 20px; 
        }
        .bot-message { 
            background-color: var(--bot-message-bg); 
            color: var(--text-color); 
            align-self: flex-start; 
            border-radius: 20px 20px 20px 5px; 
        }
        
        /* Typing Indicator CSS (Smaller) */
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
            0%, 80%, 100% {
                transform: scale(0);
            } 40% {
                transform: scale(1.0);
            }
        }
        
        /* Input Area */
        .input-container {
            position: relative;
            display: flex;
            align-items: center;
            background-color: var(--input-bg);
            border-radius: 28px;
            padding: 5px 5px 5px 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
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
        #sendButton:hover { 
            background-color: var(--chip-hover); 
        }
        
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
        .suggestion-btn:hover {
            background-color: var(--chip-hover);
        }
    </style>
</head>
<body>
    <div class="main-container">
        
        <div class="app-header">
            <img src="{{ url_for('static', filename='images/logo.png') }}" alt="Car Genie Logo">
            <span>Car Genie</span>
            <!-- --- NEW: Spacer and Reset Button --- -->
            <div class="header-spacer"></div>
            <button id="resetButton" title="Reset Chat" style="display: none;">&#8634;</button> 
        </div>
        
        <div class="chat-box" id="chatBox">
            <div class="greeting" id="greeting">Hello, User!</div>
        </div>
        
        <div class="prompt-area">
            <div class="input-container">
                <input type="text" id="userInput" placeholder="Ask Car Genie..." autocomplete="off">
                <button id="sendButton" title="Send">➤</button> 
            </div>
            
            <!-- --- *** NEW: Updated Suggestion Buttons for Recommender *** --- -->
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
        const resetButton = document.getElementById('resetButton'); // --- NEW: Get Reset Button ---

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
                resetButton.style.display = 'block'; // --- NEW: Show the reset button ---
            }

            addMessage(userText, 'user-message');
            userInput.value = '';

            try {
                // Add the 3-dot typing indicator
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
        
        // --- NEW: Reset Chat Function ---
        function resetChat() {
            // Clear the chat box but keep the greeting element (which is hidden)
            chatBox.innerHTML = ''; 
            chatBox.appendChild(greeting); // Put the greeting back in
            
            greeting.style.display = 'block'; // Show greeting
            suggestionArea.style.display = 'flex'; // Show suggestions
            resetButton.style.display = 'none'; // Hide reset button
        }
        
        sendButton.addEventListener('click', sendMessage);
        resetButton.addEventListener('click', resetChat); // --- NEW: Add click listener for reset ---
        
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

# --- Python logic for routes ---
@app.route('/')
def home():
    """Renders the main chat page."""
    return render_template_string(HTML_TEMPLATE)

# --- *** UPDATED: 'ask' function to handle all intents *** ---
@app.route('/ask', methods=['POST'])
def ask():
    """Receives questions from the user and returns the bot's answer."""
    if not CAR_DATA:
        return jsonify({'answer': 'I am sorry, my knowledge base of cars could not be loaded.'})

    user_message = request.json['message']
    
    # 'details' will either be None, a car model (str), or a criteria (dict)
    intent, details = parse_user_input(user_message, CAR_DATA)
    
    car_details = None
    if intent not in ['greeting', 'goodbye', 'thanks', 'filter_cars', 'get_recommendation', 'get_company_info']:
        if details: # 'details' is a car model string
            car_details = get_car_details(details, CAR_DATA)
        response_text = generate_response(intent, car_details)
    elif intent in ['filter_cars', 'get_recommendation']:
        # 'details' is our criteria dictionary
        response_text = generate_response(intent, details)
    elif intent == 'get_company_info':
        # 'details' is the company name string
        response_text = generate_response(intent, details)
    else:
        # 'details' is None (for greetings, etc.)
        response_text = generate_response(intent, None)
    
    # Add our 1.5 second artificial delay
    time.sleep(1.5) 
    
    return jsonify({'answer': response_text})

# Run the application
if __name__ == '__main__':
    # The debug=True flag allows you to see errors and automatically reloads the server when you save changes.
    app.run(debug=True)