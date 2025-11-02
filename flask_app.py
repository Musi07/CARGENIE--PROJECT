from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from fuzzywuzzy import process
import csv
import os
import time 

app = Flask(__name__)

# --- Python logic (mostly unchanged) ---
# ... (load_knowledge_base, get_car_details, parse_user_input, generate_response functions are all identical) ...
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
        print(f"Error: The file at '{filepath}' was not found. Make sure cars.csv is in the same folder as flask_app.py.")
        return None
    except Exception as e:
        print(f"An error occurred loading the knowledge base: {e}")
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

def parse_user_input(user_text, car_data):
    user_text = user_text.lower()
    conv_intents = {
        'greeting': ['hello', 'hi', 'hey', 'salam'],
        'goodbye': ['bye', 'goodbye', 'quit', 'exit'],
        'thanks': ['thanks', 'thank you', 'appreciate it'],
    }
    for intent, keywords in conv_intents.items():
        if any(keyword in user_text for keyword in keywords):
            return intent, None
    matched_entity = None
    if car_data:
        model_list = [car['Model'] for car in car_data]
        best_match, score = process.extractOne(user_text, [m.lower() for m in model_list])
        if score > 50:
            for car in car_data:
                if car['Model'].lower() == best_match:
                    matched_entity = car['Model']
                    break
    task_intents = {
        'get_price': ['price', 'cost', 'how much'],
        'get_mileage': ['mileage', 'fuel', 'kmpl'],
        'get_engine': ['engine', 'cc', 'horsepower'],
        'get_availability': ['available', 'country', 'countries', 'sell in'],
        'get_all_info': ['tell me about', 'details', 'info', 'information on']
    }
    matched_intent = None
    for intent, keywords in task_intents.items():
        if any(keyword in user_text for keyword in keywords):
            matched_intent = intent
            break
    if not matched_intent and matched_entity:
        matched_intent = 'get_all_info'
    return matched_intent, matched_entity

def generate_response(intent, car_details):
    if intent == 'greeting':
        return "Hello! How can I help you with car information today?"
    if intent == 'goodbye':
        return "Goodbye! Have a great day."
    if intent == 'thanks':
        return "You're welcome! Is there anything else I can help with?"
    if not car_details:
        return "I'm sorry, I couldn't find information for that car. Please check the model name."
    
    company, model = car_details['Company'], car_details['Model']
    
    if intent == 'get_price':
        return f"The price of the {company} {model} is ${car_details['Price_USD']} USD."
    elif intent == 'get_mileage':
        return f"The {company} {model} has a mileage of {car_details['Mileage_kmpl']} kmpl."
    elif intent == 'get_engine':
        return f"The {company} {model} comes with a {car_details['Engine_CC']} CC engine."
    elif intent == 'get_availability':
        return f"The {company} {model} is available in these countries: {car_details['Available_Countries']}."
    
    elif intent == 'get_all_info':
        return (f"Here are the details for the {company} {model}:<br>"
                f"- Year: {car_details['Year']}<br>"
                f"- Type: {car_details['Type']}<br>"
                f"- Price: ${car_details['Price_USD']} USD<br>"
                f"- Mileage: {car_details['Mileage_kmpl']} kmpl<br>"
                f"- Engine: {car_details['Engine_CC']} CC")
    else:
        return "I'm sorry, I didn't understand that. You can ask me about price, mileage, or general details of a car."

# --- Part 2: Web Server (Flask) ---

# --- *** NEW: Complete UI Overhaul (HTML, CSS, JS) *** ---
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
            --user-message-bg: linear-gradient(90deg, #3B82F6, #2563EB);
            --bot-message-bg: #2a2a2d;
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
            justify-content: flex-end; /* Pushes input area to the bottom */
        }
        
        /* --- NEW: Persistent App Header --- */
        .app-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 0 10px 15px 10px; /* Space at the bottom */
            font-size: 1.25rem; /* 20px */
            font-weight: 500;
            color: var(--text-secondary); /* Subtle text color */
        }
        .app-header img {
            height: 28px; /* A smaller, cleaner logo size */
            width: auto;
        }
        /* --- End of App Header --- */

        .chat-box { 
            flex-grow: 1; /* Takes up available space */
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
            margin: auto; /* Centers greeting when chat is empty */
            /* Removed flex properties, as logo is no longer in here */
        }
        .greeting img {
           display: none; /* Logo is no longer in here */
        }
        .message { 
            padding: 12px 18px; 
            border-radius: 20px; 
            max-width: 75%; 
            line-height: 1.5; 
            word-wrap: break-word;
        }
        .user-message { 
            background: var(--bot-message-bg); /* CHANGED from var(--user-message-bg) */ 
            color: var(--text-color); /* CHANGED from white */ 
            align-self: flex-end; 
            border-radius: 20px 20px 5px 20px; 
        }
        .bot-message { 
            background-color: var(--bot-message-bg); 
            color: var(--text-color); 
            align-self: flex-start; 
            border-radius: 20px 20px 20px 5px; 
        }
        
        /* --- NEW: Typing Indicator CSS --- */
        .typing-indicator {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 8px 0; /* --- CHANGED: Reduced vertical space --- */
        }
        .typing-indicator div {
            width: 6px;  /* --- CHANGED: Made smaller --- */
            height: 6px; /* --- CHANGED: Made smaller --- */
            margin: 0 2px; /* --- CHANGED: Reduced space --- */
            background-color: var(--text-secondary);
            border-radius: 50%;
            animation: typing-bounce 1.2s infinite ease-in-out;
        }
        .typing-indicator div:nth-child(1) {
            animation-delay: -0.32s;
        }
        .typing-indicator div:nth-child(2) {
            animation-delay: -0.16s;
        }
        @keyframes typing-bounce {
            0%, 80%, 100% {
                transform: scale(0);
            } 40% {
                transform: scale(1.0);
            }
        }
        /* --- End of Typing Indicator CSS --- */
        
        /* New Input Area */
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
            border-radius: 50%; /* Makes it round */
            width: 44px;
            height: 44px;
            margin-left: 10px; 
            cursor: pointer; 
            font-size: 20px; /* Icon size */
            display: flex;
            justify-content: center;
            align-items: center;
            transition: background-color 0.2s;
        }
        #sendButton:hover { 
            background-color: var(--chip-hover); 
        }
        
        /* New Suggestion Chips */
        .suggestion-area {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            padding: 20px 0;
            justify-content: center; /* Centers the chips */
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
        
        <!-- --- NEW: Added App Header outside the chat box --- -->
        <div class="app-header">
            <img src="{{ url_for('static', filename='images/logo.png') }}" alt="Car Genie Logo">
            <span>Car Genie</span>
        </div>
        
        <div class="chat-box" id="chatBox">
            <!-- --- CHANGED: Greeting text updated --- --><div class="greeting" id="greeting">Hello, User!</div>
        </div>
        
        <div class="prompt-area">
            <div class="input-container">
                <input type="text" id="userInput" placeholder="Ask Car Genie..." autocomplete="off">
                <button id="sendButton" title="Send">➤</button> <!-- Using an arrow character --></div>
            
            <div class="suggestion-area" id="suggestionArea">
                <button class="suggestion-btn">Price of Camry</button>
                <button class="suggestion-btn">Tell me about Mustang</button>
                <button class="suggestion-btn">Mileage of Civic</button>
                <button class="suggestion-btn">Engine of X5</button>
            </div>
        </div>

    </div>

    <script>
        const chatBox = document.getElementById('chatBox');
        const userInput = document.getElementById('userInput');
        const sendButton = document.getElementById('sendButton');
        const greeting = document.getElementById('greeting');
        const suggestionArea = document.getElementById('suggestionArea');

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

            // Hide greeting and suggestions on first message
            if (greeting) {
                greeting.style.display = 'none';
                suggestionArea.style.display = 'none';
            }

            addMessage(userText, 'user-message');
            userInput.value = '';

            try {
                // --- CHANGED: Use HTML for the typing indicator ---
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
                
                // Remove typing indicator
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
            return messageElement; // Return for modification (e.g., typing indicator)
        }
        
        sendButton.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault(); // Prevents new line in text area
                sendMessage();
            }
        });
    </script>
</body>
</html>
"""

# --- Python logic for routes (unchanged) ---
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/ask', methods=['POST'])
def ask():
    if not CAR_DATA:
        return jsonify({'answer': 'I am sorry, my knowledge base of cars could not be loaded.'})
    user_message = request.json['message']
    intent, entity = parse_user_input(user_message, CAR_DATA)
    car_details = None
    if entity:
        car_details = get_car_details(entity, CAR_DATA)
    response_text = generate_response(intent, car_details)
    
    # --- 2. ADDED THIS DELAY ---
    # Simulate AI "thinking" for 1.5 seconds
    time.sleep(1.5) 
    
    return jsonify({'answer': response_text})

if __name__ == '__main__':
    app.run(debug=True)

