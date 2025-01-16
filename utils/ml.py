import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
import cv2
import base64
from io import BytesIO
from PIL import Image

import firebase_admin
from firebase_admin import credentials, db

database_url = "https://tmp-project-1dae9-default-rtdb.firebaseio.com/"
cred = credentials.Certificate("secret.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": database_url
})

def decode_base64_to_image(base64_string):
    img_data = base64.b64decode(base64_string)
    img = Image.open(BytesIO(img_data))
    return np.array(img)

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
    
    if best_match is None:
        print("No match found")
    else:
        print(f"Best Match: {best_match['id']}, Probability: {best_probability}")

    
    return best_match, best_probability

def decode_img(png_file_path):
    with open(png_file_path, "rb") as img_file:
        img_binary = img_file.read()
        base64_img_str = base64.b64encode(img_binary).decode("utf-8")
    return base64_img_str

def test():
    png_file_path = "3.png"
    new_fingerprint = decode_img(png_file_path)
    
    ref = db.reference("fingerprints")
    fingerprints = ref.get()

    model = train_cnn_model(fingerprints)

    best_match, best_probability = match_fingerprint(model, fingerprints, new_fingerprint)

    if best_match is None:
        print("No match found")
    else:
        print(f"Best Match: {best_match['id']}, Probability: {best_probability}")

test()
