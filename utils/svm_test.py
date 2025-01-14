from digitalio import DigitalInOut, Direction
import board
import adafruit_fingerprint
import serial
import numpy as np
import pickle
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from PIL import Image

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
svm_model = SVC(probability=True, kernel="linear")
scaler = StandardScaler()
fingerprint_features = []
fingerprint_labels = []

# Utility Functions
def load_persistent_data():
    """Load model, features, and labels from files."""
    global svm_model, fingerprint_features, fingerprint_labels, scaler
    try:
        with open(MODEL_FILE, "rb") as model_file:
            svm_model = pickle.load(model_file)
        with open(FEATURES_FILE, "rb") as features_file:
            fingerprint_features = pickle.load(features_file)
        with open(LABELS_FILE, "rb") as labels_file:
            fingerprint_labels = pickle.load(labels_file)
        if fingerprint_features:
            fingerprint_features = scaler.fit_transform(fingerprint_features)
        print("Persistent data loaded successfully.")
    except FileNotFoundError:
        print("No persistent data found. Starting fresh.")
    except Exception as e:
        print(f"Error loading persistent data: {e}")

def save_persistent_data():
    """Save model, features, and labels to files."""
    try:
        with open(MODEL_FILE, "wb") as model_file:
            pickle.dump(svm_model, model_file)
        with open(FEATURES_FILE, "wb") as features_file:
            pickle.dump(fingerprint_features, features_file)
        with open(LABELS_FILE, "wb") as labels_file:
            pickle.dump(fingerprint_labels, labels_file)
        print("Persistent data saved successfully.")
    except Exception as e:
        print(f"Error saving persistent data: {e}")

def extract_features(image_data):
    """
    Extract features from the fingerprint image.
    The image is flattened into a 1D feature vector.
    """
    image_width = 256
    image_height = 144
    img_array = np.array(image_data, dtype=np.uint8).reshape((image_height, image_width))
    # Flatten the image to a 1D array
    return img_array.flatten()

def save_fingerprint_image_as_png(image_data):
    """Save the fingerprint image as a PNG file."""
    image_width = 256
    image_height = 144
    img_array = np.array(image_data, dtype=np.uint8).reshape((image_height, image_width))
    img = Image.fromarray(img_array, mode="L")
    img.save("fingerprint_image.png")
    print("Fingerprint image saved as 'fingerprint_image.png'")

# Core Functions
def store_fingerprint():
    """Store a fingerprint template and train the ML model."""
    print("Place your finger on the sensor to enroll...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    print("Extracting fingerprint image...")
    image_data = finger.get_fpdata(sensorbuffer="image")
    features = extract_features(image_data)

    # Check for duplicates
    if any(np.array_equal(features, stored_features) for stored_features in fingerprint_features):
        print("Fingerprint already exists. Skipping enrollment.")
        return False

    label = len(fingerprint_labels) + 1
    fingerprint_features.append(features)
    fingerprint_labels.append(label)

    # Train the SVM model only if there are at least two classes
    if len(set(fingerprint_labels)) > 1:
        scaled_features = scaler.fit_transform(fingerprint_features)
        svm_model.fit(scaled_features, fingerprint_labels)

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
    current_features = extract_features(image_data)

    if not fingerprint_features:
        print("No fingerprints stored. Please enroll fingerprints first.")
        return False

    # Check if we have enough data for SVM prediction
    if len(set(fingerprint_labels)) > 1:
        try:
            current_features_scaled = scaler.transform([current_features])
            prediction = svm_model.predict(current_features_scaled)
            probabilities = svm_model.predict_proba(current_features_scaled)[0]
            confidence = max(probabilities)
            if confidence > 0.7:  # Threshold for confidence
                print(f"Fingerprint matched with ID: {prediction[0]} (Confidence: {confidence:.2f})")
                return True
            else:
                print(f"No confident match found. Best guess ID: {prediction[0]} (Confidence: {confidence:.2f})")
        except Exception as e:
            print(f"Error during ML matching: {e}")

    # Fallback to simple matching for a single fingerprint
    print("Using fallback matching for a single fingerprint...")
    for i, stored_features in enumerate(fingerprint_features):
        if np.array_equal(current_features, stored_features):
            print(f"Fingerprint matched with ID: {fingerprint_labels[i]} (Fallback Matching)")
            return True

    print("No match found.")
    return False

def delete_fingerprint():
    """Delete a fingerprint from the local dataset."""
    print("Enter the ID of the fingerprint to delete:")
    try:
        delete_id = int(input("Fingerprint ID: "))
    except ValueError:
        print("Invalid ID. Please enter a valid number.")
        return False

    global fingerprint_features, fingerprint_labels
    if delete_id in fingerprint_labels:
        index = fingerprint_labels.index(delete_id)
        del fingerprint_features[index]
        del fingerprint_labels[index]
        print(f"Fingerprint with ID {delete_id} removed from the local dataset.")

        # Retrain the SVM model only if we have at least two classes
        if len(set(fingerprint_labels)) > 1:
            scaled_features = scaler.fit_transform(fingerprint_features)
            svm_model.fit(scaled_features, fingerprint_labels)
        else:
            svm_model = SVC(probability=True, kernel="linear")  # Reset model

    else:
        print(f"Fingerprint with ID {delete_id} not found in the local dataset.")

    save_persistent_data()
    return True

def save_fingerprint_image():
    """Capture and save the fingerprint image."""
    print("Place your finger on the sensor to capture the image...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    image_data = finger.get_fpdata(sensorbuffer="image")
    save_fingerprint_image_as_png(image_data=image_data)

# Main Menu
load_persistent_data()
while True:
    print("\nFingerprint Options:")
    print("1. Enroll Fingerprint")
    print("2. Match Fingerprint")
    print("3. Delete Fingerprint")
    print("4. Save Fingerprint Image")
    print("5. Exit")
    option = input("Select an option: ")

    if option == "1":
        store_fingerprint()
    elif option == "2":
        match_fingerprint()
    elif option == "3":
        delete_fingerprint()
    elif option == "4":
        save_fingerprint_image()
    elif option == "5":
        print("Exiting...")
        break
    else:
        print("Invalid option. Please select again.")
