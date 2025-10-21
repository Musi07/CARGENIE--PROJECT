from flask import Flask, request, jsonify, render_template_string
import csv
import os

app = Flask(__name__)

def load_knowledge_base(filename='cars.csv'):
    filepath = os.path.join(os.path.dirname(__file__), filename)
    knowledge_base = []
    try:
        with open(filepath, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                clean_row = {key.strip(): val.strip() for key, val in row.items()}
                knowledge_base.append(clean_row)
        print("Knowledge base loaded successfully with", len(knowledge_base), "cars.")
        return knowledge_base
    except FileNotFoundError:
        print(f"Error: The file at '{filepath}' was not found.")
        return None

CAR_DATA = load_knowledge_base()

def parse_user_input(user_text, car_data):
    user_text = user_text.lower()
    intents = {
        'get_price': ['price', 'cost', 'how much'],
        'get_mileage': ['mileage', 'fuel', 'kmpl'],
        'get_engine': ['engine', 'cc', 'horsepower'],
        'get_availability': ['available', 'country', 'countries', 'sell in'],
        'get_all_info': ['tell me about', 'details', 'info', 'information on']
    }
    matched_intent = None
    for intent, keywords in intents.items():
        if any(keyword in user_text for keyword in keywords):
            matched_intent = intent
            break
            
    matched_entity = None
    if car_data:
        for car in car_data:
            if car['Model'].lower() in user_text:
                matched_entity = car['Model']
                break
    return matched_intent, matched_entity

def get_car_details(model_name, car_data):
    if car_data:
        for car in car_data:
            if car['Model'].lower() == model_name.lower():
                return car
    return None

def generate_response(intent, car_details):
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

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Car Genie</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .chat-container { width: 100%; max-width: 600px; background-color: #fff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); display: flex; flex-direction: column; height: 80vh; }
        .chat-header { background-color: #4A90E2; color: white; padding: 20px; border-radius: 12px 12px 0 0; text-align: center; }
        .chat-header h1 { margin: 0; font-size: 24px; }
        .chat-box { flex-grow: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
        .message { padding: 10px 15px; border-radius: 18px; max-width: 75%; line-height: 1.4; }
        .user-message { background-color: #4A90E2; color: white; align-self: flex-end; border-radius: 18px 18px 5px 18px; }
        .bot-message { background-color: #e9e9eb; color: #333; align-self: flex-start; border-radius: 18px 18px 18px 5px; }
        .input-area { display: flex; padding: 20px; border-top: 1px solid #ddd; }
        #userInput { flex-grow: 1; border: 1px solid #ccc; border-radius: 20px; padding: 10px 15px; font-size: 16px; outline: none; }
        #sendButton { background-color: #4A90E2; color: white; border: none; border-radius: 20px; padding: 10px 20px; margin-left: 10px; cursor: pointer; font-size: 16px; }
        #sendButton:hover { background-color: #357ABD; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header"><h1>Car Genie 🚗</h1></div>
        <div class="chat-box" id="chatBox">
            <div class="message bot-message">Hello! Ask me anything about cars. For example: "What is the price of the Camry?"</div>
        </div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Type your message..." autocomplete="off">
            <button id="sendButton">Send</button>
        </div>
    </div>

    <script>
        const chatBox = document.getElementById('chatBox');
        const userInput = document.getElementById('userInput');
        const sendButton = document.getElementById('sendButton');

        async function sendMessage() {
            const userText = userInput.value.trim();
            if (userText === '') return;

            addMessage(userText, 'user-message');
            userInput.value = '';

            try {
                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: userText })
                });
                const data = await response.json();
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
        }
        
        sendButton.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
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

@app.route('/ask', methods=['POST'])
def ask():
    if not CAR_DATA:
        return jsonify({'answer': 'I am sorry, my knowledge base of cars could not be loaded.'})

    user_message = request.json['message']
    
    intent, entity = parse_user_input(user_message, CAR_DATA)
    
    if not intent or not entity:
        response_text = "I'm sorry, I didn't quite understand. Please mention a car model and what you want to know (e.g., price, mileage)."
    else:
        car_details = get_car_details(entity, CAR_DATA)
        response_text = generate_response(intent, car_details)
        
    return jsonify({'answer': response_text})

if __name__ == '__main__':
    app.run(debug=True)

