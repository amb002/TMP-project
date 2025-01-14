from typing import Union
from fastapi import FastAPI, HTTPException
import firebase_admin
from firebase_admin import credentials, db
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from digitalio import DigitalInOut, Direction
import board
import adafruit_fingerprint
import serial
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
import pickle
from PIL import Image
import base64

# Initialize FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Firebase initialization
cred = credentials.Certificate("secret.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://fingerprint-project-10f1a-default-rtdb.firebaseio.com/"
})

# Fingerprint sensor initialization
led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT
uart = serial.Serial("/dev/ttyS0", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

# Persistent storage
MODEL_FILE = "fingerprint_model.pkl"
FEATURES_FILE = "fingerprint_features.pkl"
LABELS_FILE = "fingerprint_labels.pkl"

knn_model = KNeighborsClassifier(n_neighbors=1)
fingerprint_features = []
fingerprint_labels = []

aliases = {}

def load_persistent_data():
    """Load model, features, and labels from files."""
    global knn_model, fingerprint_features, fingerprint_labels, aliases
    try:
        with open(MODEL_FILE, "rb") as model_file:
            knn_model = pickle.load(model_file)
        with open(FEATURES_FILE, "rb") as features_file:
            fingerprint_features = pickle.load(features_file)
        with open(LABELS_FILE, "rb") as labels_file:
            fingerprint_labels = pickle.load(labels_file)
        with open("aliases.pkl", "rb") as aliases_file:
            aliases = pickle.load(aliases_file)
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
        with open("aliases.pkl", "wb") as aliases_file:
            pickle.dump(aliases, aliases_file)
        print("Persistent data saved successfully.")
    except Exception as e:
        print(f"Error saving persistent data: {e}")

def extract_features(template_data):
    """Extract features from the fingerprint template."""
    return np.array(template_data).flatten()

class EnrollRequest(BaseModel):
    id: int
    alias: str

import base64

def extract_features_as_string(template_data):
    """Extract and encode features from the fingerprint template as a string."""
    features = np.array(template_data).flatten()
    # Convert features to a Base64 encoded string
    features_string = base64.b64encode(features.tobytes()).decode('utf-8')
    return features_string

@app.post("/enroll")
def enroll_fingerprint(request: EnrollRequest):
    """Enroll a new fingerprint."""
    print("Place your finger on the sensor to enroll...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        raise HTTPException(status_code=400, detail="Failed to template fingerprint.")

    if request.id in fingerprint_labels:
        raise HTTPException(status_code=400, detail="ID already exists. Please choose a unique ID.")

    template_data = finger.get_fpdata(sensorbuffer="image")
    features_string = extract_features_as_string(template_data)
    fingerprint_features.append(features_string)
    fingerprint_labels.append(request.id)
    aliases[request.id] = request.alias

    # Train the k-NN model with numerical features
    numeric_features = [np.frombuffer(base64.b64decode(f), dtype=np.uint8) for f in fingerprint_features]
    knn_model.fit(numeric_features, fingerprint_labels)
    save_persistent_data()

    # Store fingerprint data in Firebase
    ref = db.reference(f"fingerprints/{request.id}")
    ref.set({
        "id": request.id,
        "alias": request.alias,
        "features": features_string
    })

    return {"message": "Fingerprint enrolled", "id": request.id, "alias": request.alias}



@app.post("/match")
def match_fingerprint():
    """Match a fingerprint."""
    print("Place your finger on the sensor to match...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        raise HTTPException(status_code=400, detail="Failed to template fingerprint.")

    current_template = finger.get_fpdata(sensorbuffer="image")
    current_features = extract_features(current_template)

    if not fingerprint_features:
        raise HTTPException(status_code=404, detail="No fingerprints stored. Please enroll fingerprints first.")

    try:
        prediction = knn_model.predict([current_features])
        distance, _ = knn_model.kneighbors([current_features], n_neighbors=1, return_distance=True)
        if distance[0][0] < 0.5:
            matched_id = int(prediction[0])
            return {"message": "Fingerprint matched", "id": matched_id, "alias": aliases.get(matched_id, "Unknown"), "confidence": 1 - distance[0][0]}
    except Exception as e:
        print(f"ML matching error: {e}")

    if finger.finger_fast_search() == adafruit_fingerprint.OK:
        return {"message": "Fingerprint matched", "id": finger.finger_id, "alias": aliases.get(finger.finger_id, "Unknown"), "confidence": finger.confidence}

    raise HTTPException(status_code=404, detail="No match found.")

@app.post("/save-image")
def save_fingerprint_image():
    """Save a fingerprint image."""
    print("Place your finger on the sensor to capture the image...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    image_data = finger.get_fpdata(sensorbuffer="image")
    image_width, image_height = 256, 144
    img_array = np.array(image_data, dtype=np.uint8).reshape((image_height, image_width))
    img = Image.fromarray(img_array, mode="L")
    img.save("fingerprint_image.png")
    return {"message": "Fingerprint image saved as 'fingerprint_image.png'"}

@app.post("/delete/{fingerprint_id}")
def delete_fingerprint(fingerprint_id: int):
    """Delete a fingerprint."""
    global fingerprint_features, fingerprint_labels, aliases
    if fingerprint_id in fingerprint_labels:
        index = fingerprint_labels.index(fingerprint_id)
        del fingerprint_features[index]
        del fingerprint_labels[index]
        aliases.pop(fingerprint_id, None)
        if fingerprint_features:
            knn_model.fit(fingerprint_features, fingerprint_labels)
        else:
            knn_model = KNeighborsClassifier(n_neighbors=1)
    else:
        raise HTTPException(status_code=404, detail="Fingerprint ID not found.")

    if finger.delete_model(fingerprint_id) == adafruit_fingerprint.OK:
        save_persistent_data()
        return {"message": f"Fingerprint {fingerprint_id} deleted."}
    else:
        raise HTTPException(status_code=400, detail="Failed to delete fingerprint from sensor.")

# Load persistent data on startup
load_persistent_data()

@app.get("/")
def read_root():
    return {"Hello": "World"}
