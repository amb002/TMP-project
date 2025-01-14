from digitalio import DigitalInOut, Direction
import board
import adafruit_fingerprint
import serial
import numpy as np
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from PIL import Image
import cv2

# GPIO and Fingerprint Sensor Setup
led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT
uart = serial.Serial("/dev/ttyS0", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

# Persistent Storage Files
MODEL_FILE = "fingerprint_model.pkl"
FEATURES_FILE = "fingerprint_features.pkl"
LABELS_FILE = "fingerprint_labels.pkl"

# Initialize ML model and data
rf_model = RandomForestClassifier(n_estimators=100)
scaler = StandardScaler()
pca = PCA(n_components=50)  # Reduce dimensions to 50
fingerprint_features = []
fingerprint_labels = []

# Utility Functions
def load_persistent_data():
    """Load model, features, and labels from files."""
    global rf_model, fingerprint_features, fingerprint_labels, scaler, pca
    try:
        with open(MODEL_FILE, "rb") as model_file:
            rf_model = pickle.load(model_file)
        with open(FEATURES_FILE, "rb") as features_file:
            fingerprint_features = pickle.load(features_file)
        with open(LABELS_FILE, "rb") as labels_file:
            fingerprint_labels = pickle.load(labels_file)
        print("Persistent data loaded successfully.")
    except FileNotFoundError:
        print("No persistent data found. Starting fresh.")
    except Exception as e:
        print(f"Error loading persistent data: {e}")

def save_persistent_data():
    """Save model, features, and labels to files."""
    try:
        with open(MODEL_FILE, "wb") as model_file:
            pickle.dump(rf_model, model_file)
        with open(FEATURES_FILE, "wb") as features_file:
            pickle.dump(fingerprint_features, features_file)
        with open(LABELS_FILE, "wb") as labels_file:
            pickle.dump(fingerprint_labels, labels_file)
        print("Persistent data saved successfully.")
    except Exception as e:
        print(f"Error saving persistent data: {e}")

def preprocess_image(image_data):
    """
    Preprocess the fingerprint image:
    - Resize
    - Normalize
    - Apply Sobel edge detection
    """
    image_width = 256
    image_height = 144
    img_array = np.array(image_data, dtype=np.uint8).reshape((image_height, image_width))
    
    # Resize to smaller dimensions
    resized = cv2.resize(img_array, (128, 128))
    
    # Normalize (contrast enhancement)
    normalized = cv2.equalizeHist(resized)
    
    # Apply Sobel edge detection
    sobel_x = cv2.Sobel(normalized, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(normalized, cv2.CV_64F, 0, 1, ksize=3)
    sobel_combined = cv2.magnitude(sobel_x, sobel_y)  # Combine gradients
    
    # Scale and flatten
    sobel_scaled = cv2.convertScaleAbs(sobel_combined)
    return sobel_scaled.flatten()

def store_fingerprint():
    """Store a fingerprint template and train the ML model."""
    print("Place your finger on the sensor to enroll...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    print("Extracting fingerprint image...")
    image_data = finger.get_fpdata(sensorbuffer="image")
    features = preprocess_image(image_data)

    # Check for duplicates
    if any(np.array_equal(features, stored_features) for stored_features in fingerprint_features):
        print("Fingerprint already exists. Skipping enrollment.")
        return False

    label = len(fingerprint_labels) + 1
    fingerprint_features.append(features)
    fingerprint_labels.append(label)

    # Train the Random Forest model only if there are at least two classes
    if len(set(fingerprint_labels)) > 1:
        scaled_features = scaler.fit_transform(fingerprint_features)
        reduced_features = pca.fit_transform(scaled_features)
        rf_model.fit(reduced_features, fingerprint_labels)

    save_persistent_data()
    print(f"Fingerprint stored with ID: {label}. Total fingerprints stored: {len(fingerprint_labels)}")
    return True

def match_fingerprint():
    """Match a fingerprint against stored templates."""
    print("Place your finger on the sensor to match...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    print("Extracting fingerprint image...")
    image_data = finger.get_fpdata(sensorbuffer="image")
    current_features = preprocess_image(image_data)

    if not fingerprint_features:
        print("No fingerprints stored. Please enroll fingerprints first.")
        return False

    # Check if we have enough data for Random Forest prediction
    if len(set(fingerprint_labels)) > 1:
        try:
            scaled_features = scaler.transform([current_features])
            reduced_features = pca.transform(scaled_features)
            prediction = rf_model.predict(reduced_features)
            probabilities = rf_model.predict_proba(reduced_features)[0]
            confidence = max(probabilities)
            if confidence > 0.7:  # Threshold for confidence
                print(f"Fingerprint matched with ID: {prediction[0]} (Confidence: {confidence:.2f})")
                return True
            else:
                print(f"No confident match found. Best guess ID: {prediction[0]} (Confidence: {confidence:.2f})")
        except Exception as e:
            print(f"Error during ML matching: {e}")

    print("No match found.")
    return False

# Main Menu
load_persistent_data()
while True:
    print("\nFingerprint Options:")
    print("1. Enroll Fingerprint")
    print("2. Match Fingerprint")
    print("3. Exit")
    option = input("Select an option: ")

    if option == "1":
        store_fingerprint()
    elif option == "2":
        match_fingerprint()
    elif option == "3":
        print("Exiting...")
        break
    else:
        print("Invalid option. Please select again.")
