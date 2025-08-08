from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os
import sys

load_dotenv()

uri = os.getenv("MONGO_URI")
# Create a new client and connect to the server
try:
    client = MongoClient(
        uri, 
        server_api=ServerApi('1'),
        maxPoolSize=50,  # maximum connections
        minPoolSize=5,
        maxIdleTimeMS=30000,  # how long unused connections should last
        connectTimeoutMS=30000,  # connection timeout
        socketTimeoutMS=30000,   # socket timeout
        serverSelectionTimeoutMS=30000  # server selection timeout
    )
except Exception as e:
    print(f"An Invalid URI host error was received. Is your Atlas host name correct in your connection string? {e}")
    sys.exit(2)

# use a database named "shells"
db = client.shells

# create/use a new collection
project_collection = db["projects"]
devlog_collection = db["devlogs"]

query = input("What is your project? ").strip()
page_raw = input("Start from which page? (default 1) ") or "1" # sets 1 as default
try:
    page = int(page_raw)
except Exception as e:
    print(f"That isn't a valid page!")
    exit(1)

page_size = 10

skip_count = (page - 1) * page_size

# run text search using index
cursor = project_collection.find(
    {"$text": {"$search": query}}, # search using query
    {"score": {"$meta": "textScore"}, "title": 1, "description": 1} # textScore is the relevance, title and description is what it will return
).sort([("score", {"$meta": "textScore"})]).skip(skip_count).limit(page_size)

# print results
print("Results:")
print(f"Page {page}")

for result in cursor:
    print(f"{result['title']}: {result['description']}")
    print("")
