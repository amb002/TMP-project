from digitalio import DigitalInOut, Direction
import board
import adafruit_fingerprint
import serial
import pickle
import numpy as np
from sklearn.svm import SVC
from skimage.feature import local_binary_pattern
from PIL import Image
import os

# LED and fingerprint sensor setup
led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT
uart = serial.Serial("/dev/ttyS0", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

# File paths for persistence
MODEL_FILE = "fingerprint_model.pkl"
FEATURES_FILE = "fingerprint_features.pkl"
LABELS_FILE = "fingerprint_labels.pkl"

# Variables for fingerprint storage
svm_model = SVC(kernel="linear", probability=True)
fingerprint_features = []
fingerprint_labels = []

# LBP parameters
LBP_RADIUS = 1
LBP_POINTS = 8 * LBP_RADIUS

# --- Helper Functions ---

def load_persistent_data():
    """Load the model, features, and labels from files."""
    global svm_model, fingerprint_features, fingerprint_labels
    try:
        with open(MODEL_FILE, "rb") as model_file:
            svm_model = pickle.load(model_file)
        with open(FEATURES_FILE, "rb") as features_file:
            fingerprint_features = pickle.load(features_file)
        with open(LABELS_FILE, "rb") as labels_file:
            fingerprint_labels = pickle.load(labels_file)
        print("Persistent data loaded successfully.")
    except FileNotFoundError:
        print("No persistent data found. Starting fresh.")
    except Exception as e:
        print(f"Error loading data: {e}")

def save_persistent_data():
    """Save the model, features, and labels to files."""
    try:
        with open(MODEL_FILE, "wb") as model_file:
            pickle.dump(svm_model, model_file)
        with open(FEATURES_FILE, "wb") as features_file:
            pickle.dump(fingerprint_features, features_file)
        with open(LABELS_FILE, "wb") as labels_file:
            pickle.dump(fingerprint_labels, labels_file)
        print("Persistent data saved successfully.")
    except Exception as e:
        print(f"Error saving data: {e}")

def extract_lbp_features(image):
    """Extract Local Binary Pattern features from the fingerprint image."""
    lbp = local_binary_pattern(image, LBP_POINTS, LBP_RADIUS, method="uniform")
    n_bins = int(lbp.max() + 1)
    hist, _ = np.histogram(lbp.ravel(), bins=n_bins, range=(0, n_bins), density=True)
    return hist

def save_fingerprint_image_as_png(image_data, filename="fingerprint_image.png"):
    """Save fingerprint image data as a PNG file."""
    image_width = 256
    image_height = 144
    img_array = np.array(image_data, dtype=np.uint8).reshape((image_height, image_width))
    img = Image.fromarray(img_array, mode="L")
    img.save(filename)
    print(f"Fingerprint image saved as '{filename}'.")

# --- Fingerprint Operations ---

def store_fingerprint():
    """Capture and store a fingerprint in the dataset."""
    print("Place your finger on the sensor to enroll...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    print("Templating...")
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        print("Failed to template fingerprint.")
        return False
    print("Storing fingerprint...")
    image_data = finger.get_fpdata(sensorbuffer="image")
    image_width = 256
    image_height = 144
    image_array = np.array(image_data, dtype=np.uint8).reshape((image_height, image_width))
    features = extract_lbp_features(image_array)
    label = len(fingerprint_labels) + 1
    fingerprint_features.append(features)
    fingerprint_labels.append(label)
    if len(fingerprint_labels) > 1:
        svm_model.fit(fingerprint_features, fingerprint_labels)
    save_persistent_data()
    print(f"Fingerprint stored with ID: {label}")
    return True

def match_fingerprint():
    """Match a fingerprint against the stored dataset."""
    print("Place your finger on the sensor to match...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    print("Templating...")
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        print("Failed to template fingerprint.")
        return False
    print("Extracting fingerprint data...")
    image_data = finger.get_fpdata(sensorbuffer="image")
    image_width = 256
    image_height = 144
    image_array = np.array(image_data, dtype=np.uint8).reshape((image_height, image_width))
    features = extract_lbp_features(image_array)

    if len(fingerprint_labels) < 2:
        print("Not enough fingerprints enrolled for matching.")
        return False

    prediction = svm_model.predict([features])
    confidence = svm_model.predict_proba([features])[0][prediction[0] - 1]
    if confidence > 0.8:  # Confidence threshold
        print(f"Fingerprint matched with ID: {prediction[0]} (Confidence: {confidence:.2f})")
        return True
    else:
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

    if delete_id in fingerprint_labels:
        index = fingerprint_labels.index(delete_id)
        del fingerprint_features[index]
        del fingerprint_labels[index]
        if len(fingerprint_labels) > 1:
            svm_model.fit(fingerprint_features, fingerprint_labels)
        print(f"Fingerprint with ID {delete_id} removed.")
    else:
        print(f"No fingerprint found with ID {delete_id}.")

    save_persistent_data()
    return True

# --- Main Program ---
load_persistent_data()

while True:
    print("\nFingerprint Options:")
    print("1. Enroll Fingerprint")
    print("2. Match Fingerprint")
    print("3. Delete Fingerprint")
    print("4. Exit")
    option = input("Select an option: ")

    if option == "1":
        store_fingerprint()
    elif option == "2":
        match_fingerprint()
    elif option == "3":
        delete_fingerprint()
    elif option == "4":
        print("Exiting...")
        break
    else:
        print("Invalid option. Please select again.")
