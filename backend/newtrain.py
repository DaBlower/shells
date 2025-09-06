# a script to train a ML model
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import pandas as pd
import os
import sys
import getDevlogs # devlog script

# ML modules
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score

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

# get devlogs
projects_cursor = project_collection.find({})
projects = []

for project in projects_cursor:
    projects.appedn(getDevlogs.raw_values(project[id]))

# load into dataframe
df = pd.DataFrame(projects)

# split by multiplier
labeled = df[df['multiplier'].notnull()]
unlabeled = df[df[df['multiplier'].isnull()]]

# choose inputs
features = [
    "mean_num_words", "mean_num_sentences", "mean_mean_sentence_length",
    "mean_buzz_ratio", "mean_punct_ratio", "followers", "seconds_coded"
]

X_train = labeled[features]
y_train = labeled['multiplier']

X_unlabelled = unlabeled[features]

# scaling
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_unlabelled_scaled = scaler.fit_transform(X_unlabelled)

# training
model = Ridge(alpha=1.0)
model.fit(X_train_scaled, y_train)

# evaluation
scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='r2')
print(f"R2 scores: {scores}")