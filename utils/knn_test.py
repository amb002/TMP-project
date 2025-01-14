from digitalio import DigitalInOut, Direction
import board
import adafruit_fingerprint
import serial
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
import pickle
from PIL import Image


led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

uart = serial.Serial("/dev/ttyS0", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

MODEL_FILE = "fingerprint_model.pkl"
FEATURES_FILE = "fingerprint_features.pkl"
LABELS_FILE = "fingerprint_labels.pkl"

knn_model = KNeighborsClassifier(n_neighbors=1)
fingerprint_features = []
fingerprint_labels = []

def load_persistent_data():
    """Load model, features, and labels from files."""
    global knn_model, fingerprint_features, fingerprint_labels
    try:
        with open(MODEL_FILE, "rb") as model_file:
            knn_model = pickle.load(model_file)
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
            pickle.dump(knn_model, model_file)
        with open(FEATURES_FILE, "wb") as features_file:
            pickle.dump(fingerprint_features, features_file)
        with open(LABELS_FILE, "wb") as labels_file:
            pickle.dump(fingerprint_labels, labels_file)
        print("Persistent data saved successfully.")
    except Exception as e:
        print(f"Error saving persistent data: {e}")

def save_fingerprint_image_as_png(image_data):
    """Capture a fingerprint image and save it as a PNG file."""
    print("Started saving image process")
    image_width = 256
    image_height = 144
    img_array = np.array(image_data, dtype=np.uint8).reshape((image_height, image_width))
    img = Image.fromarray(img_array, mode="L")
    img.save("fingerprint_image.png")
    print("Fingerprint image saved as 'fingerprint_image.png'")

def extract_features(template_data):
    """
    Extract features from the fingerprint template.
    This function simplifies the template into a feature vector.
    """
    return np.array(template_data).flatten()

def store_fingerprint():
    """Store a fingerprint template in the array and train the ML model."""
    print("Place your finger on the sensor to enroll...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    print("Templating...")
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        print("Failed to template fingerprint.")
        return False
    print("Storing fingerprint...")
    template_data = finger.get_fpdata(sensorbuffer="character")
    features = extract_features(template_data)

    # Check for duplicates
    if any(np.array_equal(features, stored_features) for stored_features in fingerprint_features):
        print("Fingerprint already exists. Skipping enrollment.")
        return False

    label = len(fingerprint_features) + 1
    fingerprint_features.append(features)
    fingerprint_labels.append(label)
    knn_model.fit(fingerprint_features, fingerprint_labels)
    save_persistent_data()
    print(f"Fingerprint stored with ID: {label}. Total fingerprints stored: {len(fingerprint_features)}")
    return True


def match_fingerprint():
    """Match a fingerprint against stored templates using ML or fallback."""
    print("Place your finger on the sensor to match...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    print("Templating...")
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        print("Failed to template fingerprint.")
        return False
    print("Extracting fingerprint data for matching...")
    current_template = finger.get_fpdata(sensorbuffer="character")
    current_features = extract_features(current_template)
    
    if not fingerprint_features:
        print("No fingerprints stored. Please enroll fingerprints first.")
        return False

    try:
        prediction = knn_model.predict([current_features])
        distance, index = knn_model.kneighbors([current_features], n_neighbors=1, return_distance=True)
        if distance[0][0] < 0.5:
            print(f"Fingerprint matched with ID: {prediction[0]} (Confidence: {1 - distance[0][0]:.2f})")
            return True
    except Exception as e:
        print(f"Error during ML matching: {e}")
    
    # Fallback to Adafruit library matching
    print("ML matching failed or no confident match found. Attempting Adafruit library matching...")
    if finger.finger_fast_search() == adafruit_fingerprint.OK:
        print(f"Fingerprint matched with ID: {finger.finger_id}, Confidence: {finger.confidence}")
        return True
    else:
        print("No match found using Adafruit library.")
        return False


def save_fingerprint_image():
    """Capture and save the fingerprint image."""
    print("Place your finger on the sensor to capture the image...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    image_data = finger.get_fpdata(sensorbuffer="image")
    save_fingerprint_image_as_png(image_data=image_data)
    
def delete_fingerprint():
    """Delete a fingerprint from the local dataset and sensor storage."""
    print("Enter the ID of the fingerprint to delete:")
    try:
        delete_id = int(input("Fingerprint ID: "))
    except ValueError:
        print("Invalid ID. Please enter a valid number.")
        return False

    # Remove from local dataset
    global knn_model, fingerprint_features, fingerprint_labels
    if delete_id in fingerprint_labels:
        index = fingerprint_labels.index(delete_id)
        del fingerprint_features[index]
        del fingerprint_labels[index]
        print(f"Fingerprint with ID {delete_id} removed from the local dataset.")
    # Retrain the k-NN model
        if fingerprint_features:
            knn_model.fit(fingerprint_features, fingerprint_labels)
        else:
            knn_model = KNeighborsClassifier(n_neighbors=1)
    else:
        print(f"Fingerprint with ID {delete_id} not found in the local dataset.")

    # Remove from sensor storage
    print("Attempting to remove fingerprint from sensor storage...")
    if finger.delete_model(delete_id) == adafruit_fingerprint.OK:
        print(f"Fingerprint with ID {delete_id} successfully removed from the sensor.")
    else:
        print(f"Failed to remove fingerprint with ID {delete_id} from the sensor. It may not exist.")

    save_persistent_data()
    return True


load_persistent_data()
while True:
    print("\nFingerprint Options:")
    print("1. Enroll Fingerprint")
    print("2. Match Fingerprint")
    print("3. Save Fingerprint Image")
    print("4. Exit")
    option = input("Select an option: ")

    if option == "1":
        store_fingerprint()
    elif option == "2":
        match_fingerprint()
    elif option == "3":
        save_fingerprint_image()
    elif option == "4":
        print("Exiting...")
        break
    else:
        print("Invalid option. Please select again.")
