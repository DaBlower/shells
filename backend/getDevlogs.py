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

def raw_values(project_id):
    project = project_collection.find_one({"id": int(project_id)})
    devlog_ids = project["devlog_ids"]
    features = {}

 

    #project description
    desc = classify.extract_features(project["description"])
    mean_num_words = 0
    mean_num_sentences = 0
    mean_mean_sentence_length = 0
    mean_buzz_ratio = 0
    mean_punct_ratio = 0

    mean_num_words += desc["num_words"]
    mean_num_sentences += desc["num_sentences"]
    mean_mean_sentence_length += desc["mean_sentences_length"]
    mean_buzz_ratio += desc["buzz_ratio"]
    mean_punct_ratio += desc["punct_ratio"]

    for devlog_id in devlog_ids:
        devlog = devlog_collection.find_one({"id": int(devlog_id)})
        # run classify with the devlog text devlog["text"]
        features = classify.extract_features(devlog["text"])

        mean_num_words += features["num_words"]
        mean_num_sentences += features["num_sentences"]
        mean_mean_sentence_length += features["mean_sentences_length"]
        mean_buzz_ratio += features["buzz_ratio"]
        mean_punct_ratio += features["punct_ratio"]

    devlog_count = len(devlog_ids)

    mean_num_words = mean_num_words / (devlog_count + 1)
    mean_num_sentences = mean_num_sentences / (devlog_count + 1)
    mean_mean_sentence_length = mean_mean_sentence_length / (devlog_count + 1)
    mean_buzz_ratio = mean_buzz_ratio / (devlog_count + 1)
    mean_punct_ratio = mean_punct_ratio / (devlog_count + 1)
    

    return {
        "mean_num_words": mean_num_words,
        "mean_num_sentences": mean_num_sentences,
        "mean_mean_sentence_length": mean_mean_sentence_length,
        "mean_buzz_ratio": mean_buzz_ratio,
        "mean_punct_ratio": mean_punct_ratio,
        "followers": project["followers"],
        "seconds_coded": project["seconds_coded"]
    }
