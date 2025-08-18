# a script to classify the probablility of a project being ai
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from colorama import Fore, Style
import os
import sys
import re # regex
import numpy as np
import classify # classify script

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

def get_devlogs(project_id):
    devlog_ai_score = 0

    devlog_ai_score += classify.classify_description(int(project_id)) # start off with calculating the description

    project = project_collection.find_one({"id": int(project_id)})
    devlog_ids = project["devlog_ids"]

    for devlog_id in devlog_ids:
        devlog = devlog_collection.find_one({"id": int(devlog_id)})
        print(f"{Fore.GREEN}{devlog_id}{Style.RESET_ALL}")
        print(devlog["text"])
        # run classify with the devlog text devlog["text"]
        prob = classify.classify_devlog(devlog["text"])
        print(prob)

        # then add score to a variable
        devlog_ai_score += prob

    mean_ai_score = devlog_ai_score / len(devlog_ids)
    print(f"{Fore.BLUE}AI SCORE: {Fore.BLUE}{mean_ai_score*100:.2f}%{Style.RESET_ALL }")

project_id = input("What is the project id? ")
get_devlogs(project_id=project_id)