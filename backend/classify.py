# a script to classify the probablility of a project being ai
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from colorama import Fore, Style
import os
import sys
import re # regex
import numpy as np

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

buzzwords = []

def classify(project_id):
    project = project_collection.find_one({"id": project_id})

    if project:
        print(f"{Fore.GREEN}Found project! {project["title"]}{Style.RESET_ALL}")

def load_buzzwords():
    with open("config/BUZZWORDS.txt", "r") as f:
        content = f.read()
        buzzwords = [w.strip() for w in content.split(",") if w.strip()]

def extract_features(text):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip()) # split text into array
    sentences = [s for s in sentences if s] # filter out blank parts

    words = re.findall(r'\b\w+\b') # all words
    num_words = len(words) # number of words
    num_sentences = len(sentences) # number of sentences

    mean_sentence_length = np.mean([len(s.split()) for s in sentences]) if sentences else 0.0 # split each sentence into words and get the number of words in the sentence

    # buzzwords
    buzz_count = sum(1 for w in words if w.lower() in buzzwords) # the amount of buzzwords in the text
    buzz_ratio = buzz_count / num_words if num_words > 0 else 0.0
 
    # punctuation
    punct_count = len(re.findall(r'[.,!?;:]')) # the amount of punctuation in the text
    punct_ratio = punct_count / num_words if num_words > 0 else 0.0

    return { # return a dictionary
        "num_words": num_words,
        "num_sentences": num_sentences,
        "mean_sentences_length": mean_sentence_length,
        "buzz_ratio": buzz_ratio,
        "punct_ratio": punct_count
    }