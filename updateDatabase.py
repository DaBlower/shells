from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
import sys
import asyncio
import aiohttp
import ssl
from aiohttp import ClientConnectorCertificateError
from requests.exceptions import SSLError
import time
from dotenv import load_dotenv

load_dotenv()

uri = f"mongodb+srv://{os.getenv("MONGO_USERNAME")}:{os.getenv("MONGO_PASSWORD")}@{os.getenv("MONGO_CLUSTER")}.{os.getenv("MONGO_DB_NAME")}.mongodb.net/?retryWrites=true&w=majority&appName={os.getenv("MONGO_APP_NAME")}"

# Create a new client and connect to the server
try:
    client = MongoClient(uri, server_api=ServerApi('1'))
except Exception as e:
    print(f"An Invalid URI host error was received. Is your Atlas host name correct in your connection string? {e}")
    sys.exit(2)

# use a database named "projects"
db = client.shells

# create/use a new collection
project_collection = db["projects"]
devlog_collection = db["devlogs"]

# Send a ping to confirm a successful connection

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)


# # API setup for projects
# url = "https://summer.hackclub.com/api/v1/projects"
# page = 1
# cookies= {
#     "_journey_session": os.getenv("SOM_COOKIE")
# }
# MAX_RETRIES = 5 # 5 attempts
# DELAY = 2

# print("On to projects!")
# # get projects
# while True:
#     for attempt in range(MAX_RETRIES):
#         try:
#             print(f"request: url={url}?page={page}")
#             response = requests.get(url=f"{url}?page={page}", cookies=cookies)
#             response.raise_for_status()
#             break
#         except SSLError as e:
#             print(f"SSL error on attempt {attempt + 1} {e}")
#             time.sleep(DELAY)
#         except Exception as e:
#             print(f"Failed to get projects using api at {url}?page={page}! {e}")
#             print("Have you updated your cookie?")
#             exit(3)
#     else:
#         print(f"Failed after {MAX_RETRIES} attempts, giving up :(")
#         exit(6)
    
#     # try parsing into json
#     try:
#         json_response = response.json()
#     except Exception as e:
#         print(f"Failed to parse SOM API response as JSON {e}")
#         exit(5)

#     projects = json_response["projects"]
#     for project in projects:
#         project_data = {
#             "title": project.get("title"),
#             "id": project.get("id"),
#             "category": project.get("category"),
#             "url": f"https://summer.hackclub.com/projects/{project.get("id")}",
#             "description": project.get("description"),
#             "devlog_count": project.get("devlogs_count"),
#             "devlog_ids": project.get("devlogs"),
#             "seconds_coded": project.get("total_seconds_coded"),
#             "followers": len(project.get("followers", [])), # if followers doesn't exist, then just return an empty list
#             "banner": project.get("banner")
#         }
#         title = {"title": project_data["id"]}
#         update = {"$set": project_data}
#         options = {"upsert": True}
#         project_collection.update_one(title, update, upsert=options['upsert'])

#     # handle pagination
#     pagination = json_response["pagination"]
#     if page < pagination.get("pages"):
#         print(f"Update for page {page} was successful - {pagination.get("pages")-page} page(s) left!")
#         page += 1
#         time.sleep(1) # be nice
#     else:
#         break

# get devlogs
url = "https://summer.hackclub.com/api/v1/devlogs"
page = 1
cookies= {
    "_journey_session": os.getenv("SOM_COOKIE")
}
max_retries = 4

    
print("Moving on to devlogs!")
async def fetch_page(session, page):
    for attempt in range(0, max_retries):
        try:
            page_url = f"{url}?page={page}"
            print(f"Request: {page_url}")
            async with session.get(page_url, cookies=cookies, ssl=True) as response:
                time.sleep(1)
                return await response.json()
        except ClientConnectorCertificateError as e:
            print(f"SSL cert error: {e}")
        except Exception as e:
            print(f"Failed to get projects at {url}: {e}")
    print(f"Too many attempts for {page_url}")
    exit(6)


async def fetch_all_pages(total_pages, connector):
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_page(session, p) for p in range(1, total_pages + 1)]
        all_pages = await asyncio.gather(*tasks)
        return [dl for page in all_pages for dl in page.get("devlogs", [])]


async def get_total_pages(connector):
    async with aiohttp.ClientSession(connector=connector) as session:
        data = await fetch_page(session, 1)
        print("Cookie in use:", cookies["_journey_session"])
        return data["pagination"]["pages"]

async def main():
    connector = aiohttp.TCPConnector(limit=10)
    pages = await get_total_pages(connector=connector)

    devlogs = await fetch_all_pages(total_pages=pages, connector=connector)
    for devlog in devlogs:
        existing = devlog_collection.find_one({"id": devlog["id"]})
        if not existing or existing.get("text") != devlog.get("text"):
            devlog_data = {
                "text": devlog.get("text"),
                "id": devlog.get("id"),
                "attachment": devlog.get("attachment"),
                "project_id": devlog.get("project_id"),
            }
            title = {"title": devlog_data["id"]}
            update = {"$set": devlog_data}
            options = {"upsert": True}
            devlog_collection.update_one(title, update, upsert=options['upsert'])
            print(f"Added id: {devlog_data.get("id")}")

asyncio.run(main())