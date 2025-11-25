import csv
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIGURATION ---
# This is the file you downloaded from Google
SERVICE_ACCOUNT_FILE = 'serviceAccountKey.json' 
# This is the name of the "collection" (like a folder) we will create in Firebase
COLLECTION_NAME = 'cars' 
# This is your local CSV file
CSV_FILE_PATH = 'cars.csv' 
# --- END OF CONFIGURATION ---

def upload_csv_to_firestore():
    """
    Reads a CSV file and uploads its data to a Firestore collection.
    Each row in the CSV becomes a new "document" (car) in the collection.
    """
    
    # 1. Initialize Firebase Admin SDK
    try:
        # Check if the app is already initialized to avoid errors
        if not firebase_admin._apps:
            cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
            firebase_admin.initialize_app(cred)
            print("Firebase app initialized successfully.")
        else:
            print("Firebase app already initialized.")
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        print("Please make sure your 'serviceAccountKey.json' file is in the correct folder.")
        return

    db = firestore.client()
    collection_ref = db.collection(COLLECTION_NAME)
    
    print(f"Starting upload of '{CSV_FILE_PATH}' to Firestore collection '{COLLECTION_NAME}'...")
    
    # 2. Read the CSV file
    try:
        with open(CSV_FILE_PATH, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            count = 0
            # 3. Loop through each row (car) in the CSV
            for row in reader:
                # Get the car model as the "ID" for the document
                # This makes sure we don't upload duplicate cars
                model_id = row.get('Model')
                if not model_id:
                    print("Skipping row with no model.")
                    continue
                
                # Convert numeric strings to actual numbers (float)
                # This is better for sorting by price/mileage later
                data_to_upload = {}
                for key, value in row.items():
                    if key in ['Mileage_kmpl', 'Engine_CC', 'Price_Base_USD', 'Price_TopTrim_USD', 'Year']:
                        try:
                            # Try to convert to float
                            data_to_upload[key] = float(value)
                        except (ValueError, TypeError):
                            data_to_upload[key] = value # Keep as string if it's not a number
                    else:
                        data_to_upload[key] = value
                
                # 4. Upload the car data to Firebase
                # We use .set() to create or overwrite the document
                collection_ref.document(model_id).set(data_to_upload)
                print(f"  -> Uploaded/Updated: {model_id}")
                count += 1
                
            print(f"\nUpload complete! Successfully uploaded/updated {count} cars.")

    except FileNotFoundError:
        print(f"Error: The file '{CSV_FILE_PATH}' was not found.")
    except Exception as e:
        print(f"An error occurred during upload: {e}")

# --- Run the uploader script ---
if __name__ == "__main__":
    upload_csv_to_firestore()


