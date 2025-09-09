# a script to train a ML model
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import pandas as pd
import os
import sys
import getDevlogs # devlog script

# ML modules
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score

# plotting
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

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

project_count = project_collection.count_documents({})

for project in projects_cursor:
    projects.append(getDevlogs.raw_values(project_id=project["id"]))
    project_count -= 1
    print(f"{project_count} projects to go!")

# load into dataframe
df = pd.DataFrame(projects)

# choose inputs
features = [
    "mean_num_words", "mean_num_sentences", "mean_mean_sentence_length",
    "mean_buzz_ratio", "mean_punct_ratio", "followers", "seconds_coded"
]

X_all = df[features]

# scaling
scaler = StandardScaler()
X_all_scaled = scaler.fit_transform(X_all)

# training
kmeans = KMeans(n_clusters=3, random_state=42)
kmeans.fit(X_all_scaled)

df["cluster"] = kmeans.labels_

# visualisation
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_all_scaled)

plt.scatter(X_pca[:, 0], X_pca[:, 1], c=kmeans.labels_)
plt.xlabel("PC1")
plt.ylabel("PC2")
plt.title("Projects")
plt.show()