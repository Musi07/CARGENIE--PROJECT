from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from fuzzywuzzy import process
import csv
import os
import time 
import re 

app = Flask(__name__)

# --- Part 1: Data Loading (Unchanged) ---
def load_knowledge_base(filename='cars.csv'):
# ... (identical to the file in context) ...
    return knowledge_base

CAR_DATA = load_knowledge_base()

def get_car_details(model_name, car_data):
# ... (identical to the file in context) ...
    return None

# --- *** UPDATED: 'parse_user_input' for Company Info *** ---
def parse_user_input(user_text, car_data):
    """Parses user input to find intent and entity/criteria."""
    user_text = user_text.lower()
    
# ... (identical to the file in context) ...
    for intent, keywords in conv_intents.items():
        if any(keyword in user_text for keyword in keywords):
            return intent, None

    # --- Check for Recommendation Intent (Unchanged) ---
    if any(k in user_text for k in ['best', 'most', 'cheapest', 'recommend me']):
# ... (identical to the file in context) ...
        if 'sort_by' in criteria:
            return 'get_recommendation', criteria 
    # --- End of Recommendation Intent ---

    # --- Check for Filter Intent (Unchanged) ---
    filter_keywords = ['find', 'show me', 'looking for', 'under', 'over', 'cheaper than', 'less than', 'more than']
# ... (identical to the file in context) ...
        if criteria: # If we found any criteria, it's a filter intent
            return 'filter_cars', criteria

    # --- End of Filter Intent ---

    # If not filter, find the car entity
    matched_entity = None
# ... (identical to the file in context) ...
        if score > 50: 
            matched_entity = best_match 
            
    # Now find the task intent
    task_intents = {
# ... (identical to the file in context) ...
        'get_all_info': ['tell me about', 'details', 'info', 'information on']
    }
    matched_intent = None
# ... (identical to the file in context) ...
            break
            
    # --- *** UPDATED LOGIC BLOCK! *** ---
    # If we found an intent (like 'get_all_info') but NO car *model*...
    if matched_intent and not matched_entity:
        # ...let's check if they just gave us a *company* name.
        companies = set(car['Company'].lower() for car in car_data if 'Company' in car)
        for company in companies:
            if company in user_text:
                # They did! This is a 'get_company_info' intent.
                return 'get_company_info', company # e.g., 'get_company_info', 'tesla'
    # --- *** END OF UPDATED LOGIC BLOCK *** ---
            
    # If we found a car but no specific task, default to 'get_all_info'
    if not matched_intent and matched_entity:
        matched_intent = 'get_all_info'
        
    return matched_intent, matched_entity

# --- 'filter_cars' Search Engine Function (Unchanged) ---
def filter_cars(criteria, car_data):
# ... (identical to the file in context) ...
    return matches


# --- *** UPDATED: 'generate_response' to handle Company Info *** ---
def generate_response(intent, details): # 'details' is either car_details (dict), criteria (dict), company_name (str), or None
    # Handle conversational intents first
    if intent == 'greeting':
# ... (identical to the file in context) ...
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
        elif company_name in [car['Company'].lower() for car in CAR_DATA]:
             return (f"I don't have a detailed summary for <b>{company_name.title()}</b>, but I do have these models in my database:<br>"
                    f"<b>{model_list_str}</b>")
    # --- *** End of Company Info Intent *** ---

    # --- Handle Recommendation Intent (Unchanged) ---
    if intent == 'get_recommendation':
# ... (identical to the file in context) ...
        return "I can find the cheapest or most fuel-efficient car. What would you like?"

    # --- Handle Filter Intent (Unchanged) ---
    if intent == 'filter_cars':
# ... (identical to the file in context) ...
        return response
    # --- End of Filter Intent ---

    # Handle fallback cases
    car_details = details # Now we know 'details' is car_details
# ... (identical to the file in context) ...
    if not intent:
         return f"What would you like to know about the {car_details.get('Company')} {car_details.get('Model')}? You can ask about its price, mileage, or for all details."

    # --- Handle "Smart" Car-Specific Responses (Unchanged) ---
    company, model = car_details.get('Company'), car_details.get('Model')
    
# ... (identical to the file in context) ...
    
    return "I'm sorry, I didn't understand that. You can ask me about price, mileage, or general details of a car."

# --- Part 3: Web Server (Flask) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
# ... (style section is unchanged) ...
    <style>
        :root {
# ... (identical to the file in context) ...
            --bot-message-bg: #2a2a2d; /* Bot messages are also dark grey */
        }
        body { 
# ... (identical to the file in context) ...
            min-height: 95vh; 
        }
        .main-container {
# ... (identical to the file in context) ...
            justify-content: flex-end; 
        }
        
        /* Persistent App Header (Unchanged) */
# ... (identical to the file in context) ...
        .app-header img {
            height: 28px; 
            width: auto;
        }
        
        /* Reset Button Styles (Unchanged) */
# ... (identical to the file in context) ...
        #resetButton:hover {
            color: var(--text-color);
        }


        .chat-box { 
# ... (identical to the file in context) ...
            scrollbar-color: var(--chip-bg) transparent;
        }
        .greeting {
# ... (identical to the file in context) ...
            margin: auto; 
        }
        .greeting img {
           display: none; 
        }
        .message { 
# ... (identical to the file in context) ...
            word-wrap: break-word;
        }
        .user-message { 
# ... (identical to the file in context) ...
            border-radius: 20px 20px 5px 20px; 
        }
        .bot-message { 
# ... (identical to the file in context) ...
            border-radius: 20px 20px 20px 5px; 
        }
        
        /* Typing Indicator CSS (Unchanged) */
# ... (identical to the file in context) ...
        @keyframes typing-bounce {
            0%, 80%, 100% {
                transform: scale(0);
            } 40% {
                transform: scale(1.0);
            }
        }
        
        /* Input Area (Unchanged) */
# ... (identical to the file in context) ...
        #sendButton:hover { 
            background-color: var(--chip-hover); 
        }
        
        /* Suggestion Chips (Unchanged) */
# ... (identical to the file in context) ...
        .suggestion-btn:hover {
            background-color: var(--chip-hover);
        }
    </style>
</head>
<body>
    <div class="main-container">
        
        <div class="app-header">
# ... (identical to the file in context) ...
            <button id="resetButton" title="Reset Chat" style="display: none;">&#8634;</button> 
        </div>
        
        <div class="chat-box" id="chatBox">
            <div class="greeting" id="greeting">Hello, User!</div>
        </div>
        
        <div class="prompt-area">
# ... (identical to the file in context) ...
            
            <!-- Suggestion Buttons (Unchanged) -->
            <div class="suggestion-area" id="suggestionArea">
                <button class="suggestion-btn">Find cars under $30000</button>
# ... (identical to the file in context) ...
                <button class="suggestion-btn">Most efficient car?</button>
            </div>
        </div>

    </div>

    <script>
        # ... (JavaScript is unchanged) ...
        const chatBox = document.getElementById('chatBox');
# ... (identical to the file in context) ...
        const resetButton = document.getElementById('resetButton'); 

        const suggestionButtons = document.querySelectorAll('.suggestion-btn');
# ... (identical to the file in context) ...
                sendMessage();
            });
        });
        
        async function sendMessage() {
# ... (identical to the file in context) ...
            if (greeting.style.display !== 'none') {
                greeting.style.display = 'none';
                suggestionArea.style.display = 'none';
                resetButton.style.display = 'block'; 
            }

            addMessage(user_text, 'user-message');
# ... (identical to the file in context) ...

            try {
                // Add the 3-dot typing indicator
# ... (identical to the file in context) ...
                const typingIndicator = addMessage(typingIndicatorHTML, 'bot-message');
                
                const response = await fetch('/ask', {
# ... (identical to the file in
                    body: JSON.stringify({ message: userText })
                });
                const data = await response.json();
                
                chatBox.removeChild(typingIndicator);
# ... (identical to the file in context) ...

            } catch (error) {
# ... (identical to the file in context) ...
            }
        }

        function addMessage(text, className) {
# ... (identical to the file in context) ...
            return messageElement; 
        }
        
        // Reset Chat Function (Unchanged)
        function resetChat() {
# ... (identical to the file in context) ...
            resetButton.style.display = 'none'; 
        }
        
        sendButton.addEventListener('click', sendMessage);
# ... (identical to the file in context) ...
        
        userInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
# ... (identical to the file in context) ...
                sendMessage();
            }
        });
    </script>
</body>
</html>
"""

# --- Python logic for routes (Unchanged) ---
@app.route('/')
def home():
# ... (identical to the file in context) ...
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
    app.run(debug=True)