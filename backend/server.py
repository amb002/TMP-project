from typing import Union

from fastapi import FastAPI
import firebase_admin
from firebase_admin import credentials, db
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cred = credentials.Certificate("secret.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://fingerprint-project-10f1a-default-rtdb.firebaseio.com/"
})

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.get("/add/")
def add_item():
    ref = db.reference(f"items/{1234}")
    ref.set("Test")
    return {"message": f"Item {1234} added successfully", "data": "testmerge"}

class RegisterData(BaseModel):
    name: str
    isReady: bool

@app.post("/register")
async def register(data: RegisterData):
    print(f"Received data: {data}")
    data.isReady = True
    return {"message": "Registration successful", "data": data}