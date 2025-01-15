from typing import Union
from fastapi import FastAPI, HTTPException
import firebase_admin
from firebase_admin import credentials, db
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import base64
import io
import serial
from datetime import datetime
from digitalio import DigitalInOut, Direction
import board
import adafruit_fingerprint
from PIL import Image
import numpy as np
from io import BytesIO

USE_MODEL = False

if USE_MODEL:
    import tensorflow as tf
    from tensorflow.keras import layers, models
    import cv2

database_url = "https://fingerprint-project-10f1a-default-rtdb.firebaseio.com/"
cred = credentials.Certificate("secret.json")
firebase_admin.initialize_app(cred, {"databaseURL": database_url})
uart = serial.Serial("/dev/ttyS0", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

app = FastAPI()
gui_endpoint = "http://localhost:3000"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[gui_endpoint],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = None

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

class EnrollRequest(BaseModel):
    id: int
    alias: str

def preprocess_image(image, target_size=(224, 224)):
    image = cv2.resize(image, target_size)
    if len(image.shape) == 3 and image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image = image.astype("float32") / 255.0
    return np.expand_dims(image, axis=-1)

def create_cnn(input_shape=(224, 224, 1)):
    input_a = layers.Input(shape=input_shape)
    input_b = layers.Input(shape=input_shape)
    
    def cnn_base(input):
        x = layers.Conv2D(32, (3, 3), activation="relu")(input)
        x = layers.MaxPooling2D((2, 2))(x)
        x = layers.Conv2D(64, (3, 3), activation="relu")(x)
        x = layers.MaxPooling2D((2, 2))(x)
        x = layers.Conv2D(128, (3, 3), activation="relu")(x)
        x = layers.MaxPooling2D((2, 2))(x)
        x = layers.Flatten()(x)
        x = layers.Dense(256, activation="relu")(x)
        return x
    
    processed_a = cnn_base(input_a)
    processed_b = cnn_base(input_b)
    
    combined = layers.Concatenate()([processed_a, processed_b])
    combined = layers.Dense(256, activation="relu")(combined)
    combined = layers.Dense(1, activation="sigmoid")(combined)
    
    return models.Model(inputs=[input_a, input_b], outputs=combined)

def create_image_pairs(fingerprints, image_size=(224, 224)):
    pairs = []
    labels = []
    for i in range(len(fingerprints)):
        if fingerprints[i] is not None:
            for j in range(i + 1, len(fingerprints)):
                if fingerprints[j] is not None and fingerprints[i]["id"] == fingerprints[j]["id"]:
                    image_a = preprocess_image(decode_base64_to_image(fingerprints[i]["image"]), image_size)
                    image_b = preprocess_image(decode_base64_to_image(fingerprints[j]["image"]), image_size)
                    pairs.append([image_a, image_b])
                    labels.append(1)

            for j in range(len(fingerprints)):
                if fingerprints[j] is not None and fingerprints[i]["id"] != fingerprints[j]["id"]:
                    image_a = preprocess_image(decode_base64_to_image(fingerprints[i]["image"]), image_size)
                    image_b = preprocess_image(decode_base64_to_image(fingerprints[j]["image"]), image_size)
                    pairs.append([image_a, image_b])
                    labels.append(0)
    
    return np.array(pairs), np.array(labels)

def train_cnn_model(fingerprints, image_size=(224, 224)):
    pairs, labels = create_image_pairs(fingerprints, image_size)
    pairs = [pairs[:, 0], pairs[:, 1]]
    
    model = create_cnn(input_shape=(image_size[0], image_size[1], 1))
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    
    model.fit(pairs, labels, batch_size=16, epochs=10)
    return model

def match_fingerprint(model, known_fingerprints, new_fingerprint, image_size=(224, 224)):
    new_fingerprint_image = preprocess_image(decode_base64_to_image(new_fingerprint), image_size)
    
    best_match = None
    best_probability = 0
    
    for fingerprint in known_fingerprints:
        if fingerprint is not None:
            known_fingerprint_image = preprocess_image(decode_base64_to_image(fingerprint["image"]), image_size)
            probability = model.predict([np.expand_dims(new_fingerprint_image, axis=0), np.expand_dims(known_fingerprint_image, axis=0)])[0][0]
            
            if probability > best_probability:
                best_probability = probability
                best_match = fingerprint
    
    return best_match, best_probability

def decode_base64_to_image(base64_string):
    img_data = base64.b64decode(base64_string)
    img = Image.open(BytesIO(img_data))
    return np.array(img)

def decode_img(png_file_path):
    with open(png_file_path, "rb") as img_file:
        img_binary = img_file.read()
        base64_img_str = base64.b64encode(img_binary).decode("utf-8")
    return base64_img_str

def encode_fingerprint_image(fingerprint_data):
    image = Image.open(BytesIO(fingerprint_data))
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    encoded_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return encoded_image

@app.on_event("startup")
async def on_startup():
    if USE_MODEL:
        print("Training model on startup...")
        ref = db.reference("fingerprints")
        fingerprints = ref.get()
        global model
        model = train_cnn_model(fingerprints)

@app.post("/enroll")
def enroll_fingerprint(request: EnrollRequest):
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    image_data = finger.get_fpdata(sensorbuffer="image")
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        raise HTTPException(status_code=400, detail="Failed to template fingerprint.")
    if finger.store_model(request.id) != adafruit_fingerprint.OK:
        raise HTTPException(status_code=400, detail="Failed to store fingerprint in sensor.")
    
    img_str = encode_fingerprint_image(image_data)
    ref = db.reference(f"fingerprints/{request.id}")
    ref.set({
        "id": request.id,
        "alias": request.alias,
        "image": img_str
    })
    return {"message": "Fingerprint enrolled", "id": request.id, "alias": request.alias}

@app.post("/match")
def match_fingerprint_endpoint():
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    image_data = finger.get_fpdata(sensorbuffer="image")
    scanned_img_str = encode_fingerprint_image(image_data)
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        raise HTTPException(status_code=400, detail="Failed to template fingerprint.")
    
    if USE_MODEL:
        ref = db.reference("fingerprints")
        fingerprints = ref.get()
        best_match, best_probability = match_fingerprint(model, fingerprints, scanned_img_str)
    else:
        if finger.finger_fast_search() != adafruit_fingerprint.OK:
            raise HTTPException(status_code=404, detail="No match found.")
        matched_id = finger.finger_id
        ref = db.reference(f"fingerprints/{matched_id}")
        alias = ref.get().get("alias", "Unknown")
        matched_img_str = ref.get().get("image")
        best_match = {"id": matched_id, "alias": alias, "image": matched_img_str}
        best_probability = finger.confidence
    
    matched_id = best_match["id"]
    ref = db.reference(f"fingerprints/{matched_id}")
    
    alias = best_match.get("alias", "Unknown")
    matched_img_str = best_match.get("image")
    
    timestamp = datetime.now()
    human_readable_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")

    matches_ref = ref.child("matches")
    matches_ref.push({"timestamp": human_readable_timestamp})

    return {
        "message": "Fingerprint matched",
        "id": matched_id,
        "alias": alias,
        "confidence": best_probability,
        "scanned_img_str": scanned_img_str,
        "matched_img_str": matched_img_str,
        "timestamp": human_readable_timestamp
    }

@app.post("/delete/{fingerprint_id}")
def delete_fingerprint(fingerprint_id: int):
    if finger.delete_model(fingerprint_id) != adafruit_fingerprint.OK:
        raise HTTPException(status_code=400, detail="Failed to delete fingerprint from sensor.")

    ref = db.reference(f"fingerprints/{fingerprint_id}")
    ref.delete()
    return {"message": f"Fingerprint {fingerprint_id} deleted."}
