import os

from dotenv import load_dotenv

from pymongo import MongoClient

load_dotenv()

uri = os.getenv("MONGO_URI")

print("Mulai koneksi...")

client = MongoClient(uri)

print("Client dibuat")

client.admin.command("ping")

print("MongoDB Connected!")
