import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
import cv2
import base64
from io import BytesIO
from PIL import Image

import firebase_admin
from firebase_admin import credentials, db

database_url = "https://fingerprint-project-10f1a-default-rtdb.firebaseio.com/"
cred = credentials.Certificate("secret.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": database_url
})

# Helper function to decode base64 string and convert to image
def decode_base64_to_image(base64_string):
    img_data = base64.b64decode(base64_string)
    img = Image.open(BytesIO(img_data))
    return np.array(img)

def preprocess_image(image, target_size=(224, 224)):
    image = cv2.resize(image, target_size)  # Resize to the target size
    
    # Check if the image has more than 1 channel (color image)
    if len(image.shape) == 3 and image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # Convert to grayscale (if needed)
    
    image = image.astype("float32") / 255.0  # Normalize the image
    return np.expand_dims(image, axis=-1)  # Add channel dimension if it's grayscale


# Function to create the base network for the Siamese model
def create_base_network(input_shape=(224, 224, 1)):
    input = layers.Input(shape=input_shape)
    x = layers.Conv2D(32, (3, 3), activation="relu")(input)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Conv2D(64, (3, 3), activation="relu")(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Conv2D(128, (3, 3), activation="relu")(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Flatten()(x)
    x = layers.Dense(256, activation="relu")(x)
    x = layers.Lambda(lambda x: tf.nn.l2_normalize(x, axis=1))(x)  # Normalize the output
    return models.Model(input, x)

# Function to create the Siamese network
def create_siamese_network(input_shape=(224, 224, 1)):
    base_network = create_base_network(input_shape)
    
    input_a = layers.Input(shape=input_shape)
    input_b = layers.Input(shape=input_shape)
    
    # Generate the feature vectors for both inputs
    feature_a = base_network(input_a)
    feature_b = base_network(input_b)
    
    # Compute the Euclidean distance between the feature vectors
    distance = layers.Lambda(lambda tensors: tf.norm(tensors[0] - tensors[1], axis=1, keepdims=True))([feature_a, feature_b])
    
    return models.Model(inputs=[input_a, input_b], outputs=distance)

# Function to prepare pairs of images and labels (0 for non-matching, 1 for matching)
def create_image_pairs(fingerprints, image_size=(224, 224)):
    pairs = []
    labels = []
    
    # Create pairs of images and their labels
    for i in range(len(fingerprints)):
        if fingerprints[i] is not None:
            # Positive pair (matching images)
            for j in range(i + 1, len(fingerprints)):
                if fingerprints[j] is not None:
                    image_a = preprocess_image(decode_base64_to_image(fingerprints[i]["image"]), image_size)
                    image_b = preprocess_image(decode_base64_to_image(fingerprints[j]["image"]), image_size)
                    pairs.append([image_a, image_b])
                    labels.append(1)  # Matching

            # Negative pair (non-matching images)
            for j in range(len(fingerprints)):
                if fingerprints[j] is not None and i != j:
                    image_a = preprocess_image(decode_base64_to_image(fingerprints[i]["image"]), image_size)
                    image_b = preprocess_image(decode_base64_to_image(fingerprints[j]["image"]), image_size)
                    pairs.append([image_a, image_b])
                    labels.append(0)  # Not matching
    
    return np.array(pairs), np.array(labels)

# Define a function to train the model
def train_siamese_network(fingerprints, image_size=(224, 224)):
    pairs, labels = create_image_pairs(fingerprints, image_size)
    pairs = [pairs[:, 0], pairs[:, 1]]  # Separate the image pairs into two inputs
    
    # Create the Siamese network
    model = create_siamese_network(input_shape=(image_size[0], image_size[1], 1))
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    
    # Train the model
    model.fit(pairs, labels, batch_size=16, epochs=10)
    return model

def match_fingerprint(model, known_fingerprints, new_fingerprint, image_size=(224, 224)):
    # Preprocess the new fingerprint image
    new_fingerprint_image = preprocess_image(decode_base64_to_image(new_fingerprint), image_size)
    
    best_match = None
    best_distance = float('inf')
    
    for fingerprint in known_fingerprints:
        if fingerprint is not None:  # Check if the fingerprint is not None
            # Compare with each stored fingerprint
            known_fingerprint_image = preprocess_image(decode_base64_to_image(fingerprint["image"]), image_size)
            
            # Predict similarity using the trained model
            distance = model.predict([np.expand_dims(new_fingerprint_image, axis=0), np.expand_dims(known_fingerprint_image, axis=0)])
            
            if distance < best_distance:
                best_distance = distance
                best_match = fingerprint
    
    return best_match, best_distance

def decode_img(png_file_path):
    with open(png_file_path, "rb") as img_file:
        # Read the PNG image as binary
        img_binary = img_file.read()
        
        # Convert the binary data to base64
        base64_img_str = base64.b64encode(img_binary).decode("utf-8")
    
    return base64_img_str


def test():
    png_file_path = "1.png"
    new_fingerprint = decode_img(png_file_path)
    # Sample fingerprint data (with base64 image strings)
    ref = db.reference("fingerprints")
    fingerprints = ref.get()

    # Train the model on the known fingerprints
    model = train_siamese_network(fingerprints)

    # A new fingerprint to match (in base64)
    
    # Match the new fingerprint with the known ones
    best_match, best_distance = match_fingerprint(model, fingerprints, new_fingerprint)

    print(f"Best Match: {best_match["id"]}, Distance: {best_distance}")
    
test()