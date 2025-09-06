# a script to train a ML model
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from colorama import Fore, Style
import os
import sys
import re # regex
import numpy as np
import pandas as pd
import getDevlogs # devlog script
import joblib

# ML modules
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

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

projects = [] # the features of each project
df = []

print(f"Unlabeled: {df["multiplier"].notna().sum()}")
print(f"Labeled: {df["multiplier"].isna().sum()}")

def process_data(df):
    # separate into labeled and non labeled data
    labeled_data = df[df["multiplier"].isna()]
    unlabeled_data = df[df["multiplier"].notna()]

    return labeled_data, unlabeled_data

def get_features():
    global df
    # get all projects
    cursor = project_collection.find({})

    for project in cursor:
        projects.append(getDevlogs.raw_values(project["id"]))
        print(f"{Fore.GREEN}Got values for project {project["id"]}!{Style.RESET_ALL}")

    df = pd.DataFrame(projects)

labeled_df, unlabeled_df = process_data(df)

X_labeled = df[["mean_num_words", "mean_num_sentences", "mean_mean_sentence_length", "mean_buzz_ratio", "mean_punct_ratio", "followers", "seconds_coded"]] # the features that the model will use to predict
y_labled = labeled_df["multiplier"]


X_train, X_test, y_train, y_test = train_test_split(X_labeled, y_labled, test_size=0.2, random_state=42, stratify=y_labled)