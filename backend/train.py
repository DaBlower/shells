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

projects = []

# get data for training
def collect_data():
    # get all projects
    cursor = project_collection.find({})

    for project in cursor:
        projects.append(getDevlogs.raw_values(project["id"]))
        print(f"{Fore.GREEN}Got values for project {project["id"]}!{Style.RESET_ALL}")

    df = pd.DataFrame(projects)

    x = df[["mean_num_words", "mean_num_sentences", "mean_mean_sentence_length", "mean_buzz_ratio", "mean_punct_ratio", "followers", "seconds_coded"]] # the features that the model will use to predict
    y = df["multiplier"]

    return x, y

X, y = collect_data()

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42) # thgttg!!!

# train model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# evaluate model
y_pred = model.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
print(f"Mean Squared Error: {mse}")

# save model
joblib.dump(model, "trained_model.pkl")
print("Saved model as trained_model.pkl")