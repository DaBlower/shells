from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
import sys
import asyncio
import aiohttp
from pymongo import UpdateOne
from aiohttp import ClientConnectorCertificateError
from requests.exceptions import SSLError
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


# get devlogs
url = "https://summer.hackclub.com/api/v1/devlogs"
page = 1
cookies= {
    "_journey_session": os.getenv("SOM_COOKIE")
}
headers = {
    "Accept": "application/json"
}
max_retries = 4

BATCH_SIZE = 1000
operations = []
    
print("Moving on to devlogs!")
async def fetch_page(session, page, semaphore):
    async with semaphore:
        for attempt in range(0, max_retries):
            try:
                page_url = f"{url}?page={page}"
                print(f"Request: {page_url} (Attempt {attempt+1})")
                async with session.get(page_url, cookies=cookies, ssl=True, headers=headers) as response:
                    
                    if response.status != 200:
                        print(f"Failed request: {page_url} returned status {response.status}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)
                            continue
                        else:
                            raise Exception(f"HTTP {response.status} after {max_retries} attempts")
                   
                    try:
                        data = await response.json()
                        return data
                    except Exception as e:
                        print(f"Failed to decode JSON from {page_url}: {e}")
                        
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)
                            continue
                        else:
                            raise Exception(f"JSON decode failed after {max_retries} attempts: {e}")
                    
            except ClientConnectorCertificateError as e:
                print(f"SSL cert error on {page_url}: {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    raise Exception(f"SSL error after {max_retries} attempts: {e}")
            except Exception as e:
                print(f"Failed to get page {page_url}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    raise Exception(f"Request failed after {max_retries} attempts: {e}")
        
        # This should never be reached, but just in case
        raise Exception(f"Exhausted all {max_retries} attempts for {url}?page={page}")


async def fetch_all_pages(total_pages, session):
    semaphore = asyncio.Semaphore(30)
    all_devlogs = [] # an empty array to store devlogs


    tasks = [fetch_page(session=session,page=page, semaphore=semaphore)
            for page in range(1, total_pages + 1)]

    results = await asyncio.gather(*tasks, return_exceptions=True)
                                
    for i, page_data in enumerate(results, 1):
        if isinstance(page_data, Exception):
            print(f"Exception occured on page {i}: {page_data}")
            continue
        if page_data:
            all_devlogs.extend(page_data.get("devlogs", []))
        else:
            print(f"Page {i} was empty")

    return all_devlogs

async def get_total_pages(session):
    semaphore = asyncio.Semaphore(1)
    data = await fetch_page(session, 1, semaphore=semaphore)
    return data["pagination"]["pages"]

async def main():
    try:
        connector = aiohttp.TCPConnector(limit=30)
        timeout = aiohttp.ClientTimeout(total=8)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # devlogs
            url = "https://summer.hackclub.com/api/v1/devlogs"
            pages = await get_total_pages(session=session)
            print(f"Total pages: {pages}")

            devlogs = await fetch_all_pages(total_pages=pages, session=session)

            # some info
            print(f"Processing {len(devlogs)} devlogs!")
            print("First devlog:", devlogs[0])
            print("Beginning upserts…")

            for devlog in devlogs:
                print(f"Upserting devlog {devlog}…")
                existing = devlog_collection.find_one({"id": devlog["id"]})
                if not existing or existing.get("text") != devlog.get("text"):
                    devlog_data = {
                        "text": devlog.get("text"),
                        "id": devlog.get("id"),
                        "attachment": devlog.get("attachment"),
                        "project_id": devlog.get("project_id"),
                    }
                    title = {"id": devlog_data["id"]}
                    update = {"$set": devlog_data}
                    options = {"upsert": True}
                    devlog_collection.update_one(title, update, upsert=options['upsert'])
                    print(f"Added id: {devlog_data.get("id")}")
            
            # projects
            url = "https://summer.hackclub.com/api/v1/projects"
            pages = await get_total_pages(session=session)
            print(f"Total pages: {pages}")

            projects = await fetch_all_pages(total_pages=pages, session=session)
            for project in projects:
                existing = project_collection.find_one({"id": project["id"]})
                if not existing or existing.get("updated_at") != project.get("updated_at"): # check if an update is needed
                    project_data = {
                        "title": project.get("title"),
                        "id": project.get("id"),
                        "category": project.get("category"),
                        "url": f"https://summer.hackclub.com/projects/{project.get("id")}",
                        "description": project.get("description"),
                        "devlog_count": project.get("devlogs_count"),
                        "devlog_ids": project.get("devlogs"),
                        "seconds_coded": project.get("total_seconds_coded"),
                        "followers": len(project.get("followers", [])), # if followers doesn't exist, then just return an empty list
                        "banner": project.get("banner"),
                        "updated_at": project.get("updated_at")
                    }
                    title = {"id": project_data["id"]}
                    update = {"$set": project_data}
                    options = {"upsert": True}
                    project_collection.update_one(title, update, upsert=options['upsert'])
                    print(f"Added id: {project_data.get("id")}")
    except Exception as e:
        print(f"Exception in main! {e}")

if __name__ == "__main__":
    asyncio.run(main())