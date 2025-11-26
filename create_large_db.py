import csv
import random

# Define some real-world data to mix and match
makes = [
    "Toyota", "Honda", "Ford", "Chevrolet", "Nissan", "BMW", "Mercedes-Benz", 
    "Volkswagen", "Audi", "Hyundai", "Kia", "Subaru", "Mazda", "Lexus", "Jeep", "Tesla"
]

models = {
    "Toyota": ["Camry", "Corolla", "RAV4", "Highlander", "Tacoma", "Prius"],
    "Honda": ["Civic", "Accord", "CR-V", "Pilot", "Odyssey"],
    "Ford": ["F-150", "Mustang", "Explorer", "Escape", "Bronco"],
    "Chevrolet": ["Silverado", "Equinox", "Malibu", "Tahoe", "Corvette"],
    "Nissan": ["Altima", "Rogue", "Sentra", "Frontier", "Pathfinder"],
    "BMW": ["3 Series", "5 Series", "X3", "X5", "M3"],
    "Mercedes-Benz": ["C-Class", "E-Class", "GLC", "GLE", "S-Class"],
    "Volkswagen": ["Jetta", "Passat", "Tiguan", "Atlas", "Golf"],
    "Audi": ["A4", "A6", "Q5", "Q7", "e-tron"],
    "Hyundai": ["Elantra", "Sonata", "Tucson", "Santa Fe", "Kona"],
    "Kia": ["Forte", "K5", "Sportage", "Sorento", "Telluride"],
    "Subaru": ["Impreza", "Legacy", "Forester", "Outback", "Crosstrek"],
    "Mazda": ["Mazda3", "Mazda6", "CX-5", "CX-9", "MX-5 Miata"],
    "Lexus": ["IS", "ES", "RX", "NX", "GX"],
    "Jeep": ["Wrangler", "Grand Cherokee", "Cherokee", "Compass", "Gladiator"],
    "Tesla": ["Model 3", "Model S", "Model X", "Model Y", "Cybertruck"]
}

types = ["Sedan", "SUV", "Truck", "Coupe", "Hatchback", "Convertible", "Wagon"]

def generate_cars_csv():
    with open('cars.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # Header
        writer.writerow(['Company', 'Model', 'Year', 'Mileage_kmpl', 'Engine_CC', 'Type', 'Price_Base_USD', 'Price_TopTrim_USD', 'Available_Countries', 'Image_URL', 'Notes'])
        
        count = 0
        for make, model_list in models.items():
            for model in model_list:
                # Generate realistic-looking data
                year = 2024
                
                # Logic for type based on model name hints
                car_type = "Sedan"
                if any(x in model for x in ["RAV4", "CR-V", "Explorer", "Equinox", "Rogue", "X3", "X5", "GLC", "GLE", "Q5", "Q7", "Tucson", "Santa Fe", "Sportage", "Sorento", "Forester", "Outback", "CX-5", "CX-9", "RX", "NX", "GX", "Cherokee", "Compass", "Model X", "Model Y"]):
                    car_type = "SUV"
                elif any(x in model for x in ["F-150", "Silverado", "Frontier", "Tacoma", "Gladiator", "Cybertruck"]):
                    car_type = "Truck"
                elif any(x in model for x in ["Mustang", "Corvette", "M3", "MX-5"]):
                    car_type = "Coupe"
                
                # Mileage and Engine logic
                if make == "Tesla" or model == "e-tron":
                    engine = "0" # EV
                    mileage = random.randint(300, 500) # Range
                    notes = "Electric Vehicle. Mileage represents range in km."
                else:
                    engine = random.choice([1500, 2000, 2500, 3000, 3500, 5000])
                    mileage = random.randint(8, 25)
                    notes = f"Standard {make} reliability."

                # Price logic
                base_price = random.randint(22, 60) * 1000 + random.randint(0, 9) * 100
                top_price = int(base_price * 1.5)

                # Image (Placeholder to ensure it works)
                image_url = f"https://placehold.co/600x400?text={make}+{model}"

                writer.writerow([
                    make, 
                    model, 
                    year, 
                    mileage, 
                    engine, 
                    car_type, 
                    base_price, 
                    top_price, 
                    "Global", 
                    image_url, 
                    notes
                ])
                count += 1
        
        print(f"Successfully generated {count} cars in cars.csv")

if __name__ == "__main__":
    generate_cars_csv()