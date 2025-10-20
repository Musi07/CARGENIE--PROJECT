import csv
import os

def load_knowledge_base(filename='cars.csv'):
    """
    Loads the car data from a CSV file into a list of dictionaries.
    """
    # Build the correct path to the CSV file.
    # This script is in 'src', and the csv is in the parent folder.
    # os.path.dirname(__file__) gets the directory of the current script ('src')
    # os.path.join(...) then goes up one level ('..') and finds the file.
    filepath = os.path.join(os.path.dirname(__file__), '..', filename)
    
    knowledge_base = []
    try:
        with open(filepath, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Clean up whitespace from keys and values
                clean_row = {key.strip(): val.strip() for key, val in row.items()}
                knowledge_base.append(clean_row)
        print("Knowledge base loaded successfully!")
        return knowledge_base
    except FileNotFoundError:
        print(f"Error: The file at '{filepath}' was not found. Please make sure '{filename}' is in the main project folder.")
        return None

def main():
    """
    Main function to run the Car Genie chatbot.
    """
    car_data = load_knowledge_base()
    
    if not car_data:
        return
        
    print("--------------------------------------------------")
    print(f"Loaded {len(car_data)} car entries.")
    if car_data:
        first_car = car_data[0]
        print(f"Example Entry: The {first_car['Company']} {first_car['Model']} from {first_car['Year']}.")
    print("--------------------------------------------------")
    
if __name__ == "__main__":
    main()
