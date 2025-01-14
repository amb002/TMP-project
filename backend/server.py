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

class EnrollRequest(BaseModel):
    id: int
    alias: str

@app.post("/enroll")
def enroll_fingerprint(request: EnrollRequest):
    """Enroll a new fingerprint."""
    print("Place your finger on the sensor to enroll...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        raise HTTPException(status_code=400, detail="Failed to template fingerprint.")
    if finger.store_model(request.id) != adafruit_fingerprint.OK:
        raise HTTPException(status_code=400, detail="Failed to store fingerprint in sensor.")

    # Save fingerprint metadata in Firebase
    ref = db.reference(f"fingerprints/{request.id}")
    ref.set({
        "id": request.id,
        "alias": request.alias
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
    if finger.finger_fast_search() != adafruit_fingerprint.OK:
        raise HTTPException(status_code=404, detail="No match found.")

    matched_id = finger.finger_id
    ref = db.reference(f"fingerprints/{matched_id}")
    alias = ref.get().get("alias", "Unknown")

    return {
        "message": "Fingerprint matched",
        "id": matched_id,
        "alias": alias,
        "confidence": finger.confidence
    }

@app.post("/delete/{fingerprint_id}")
def delete_fingerprint(fingerprint_id: int):
    """Delete a fingerprint."""
    if finger.delete_model(fingerprint_id) != adafruit_fingerprint.OK:
        raise HTTPException(status_code=400, detail="Failed to delete fingerprint from sensor.")

    # Delete fingerprint metadata from Firebase
    ref = db.reference(f"fingerprints/{fingerprint_id}")
    ref.delete()
    return {"message": f"Fingerprint {fingerprint_id} deleted."}

@app.post("/save-image")
def save_fingerprint_image():
    """Save a fingerprint image."""
    print("Place your finger on the sensor to capture the image...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    image_data = finger.get_fpdata(sensorbuffer="image")
    with open("fingerprint_image.raw", "wb") as f:
        f.write(bytearray(image_data))
    return {"message": "Fingerprint image saved as 'fingerprint_image.raw'"}

@app.get("/")
def read_root():
    return {"Hello": "World"}
