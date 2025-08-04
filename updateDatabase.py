from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import AutoReconnect
import os
import sys
import asyncio
import aiohttp
from pymongo import UpdateOne
from aiohttp import ClientConnectorCertificateError
from requests.exceptions import SSLError
from dotenv import load_dotenv

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

# use a database named "projects"
db = client.shells

# create/use a new collection
project_collection = db["projects"]
devlog_collection = db["devlogs"]

# Send a ping to confirm a successful connection

try:
    client.admin.command('ping')
except AutoReconnect:
    pass # ingnore autoreconnect error at startup
except Exception as e:
    print(e)


# headers
cookies= {
    "_journey_session": os.getenv("SOM_COOKIE")
}
headers = {
    "Accept": "application/json"
}
max_retries = 4

async def fetch_page(session, page, semaphore, url):
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
                        print(f"Recieved page {page}")
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
        
        # this shouldn't really happen, buuutt just in case
        raise Exception(f"Exhausted all {max_retries} attempts for {url}?page={page}")


async def fetch_all_pages(total_pages, session, url, is_devlogs):
    semaphore = asyncio.Semaphore(30)
    all_items = [] # an empty array to store the results


    tasks = [fetch_page(session=session,page=page, semaphore=semaphore, url=url)
            for page in range(1, total_pages + 1)]

    results = await asyncio.gather(*tasks, return_exceptions=True)
                                
    for i, page_data in enumerate(results, 1):
        if isinstance(page_data, Exception): # async doesn't automatically raise an exception
            print(f"Exception occured on page {i}: {page_data}")
            continue
        if page_data:
            if is_devlogs:
                all_items.extend(page_data.get("devlogs", []))
            else:
                all_items.extend(page_data.get("projects", []))
        else:
            print(f"Page {i} was empty")

    return all_items

async def get_total_pages(session, url):
    semaphore = asyncio.Semaphore(1)
    data = await fetch_page(session, 1, semaphore=semaphore, url=url)
    return data["pagination"]["pages"]

async def main():
    try:
        connector = aiohttp.TCPConnector(limit=30)
        timeout = aiohttp.ClientTimeout(total=8)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # devlogs
            url = "https://summer.hackclub.com/api/v1/devlogs"
            pages = await get_total_pages(session=session, url=url)
            print(f"Total pages: {pages}")

            devlogs = await fetch_all_pages(total_pages=pages, session=session, url=url, is_devlogs=True)
            print("Fetched all devlogs!")

            # some info
            print(f"Processing {len(devlogs)} devlogs!")
            devlog_operations = []
            for devlog in devlogs:
                devlog_data = {
                    "text": devlog.get("text"),
                    "id": devlog.get("id"),
                    "attachment": devlog.get("attachment"),
                    "project_id": devlog.get("project_id"),
                }
                id_filter = {"id": devlog_data["id"]}
                update = {"$set": devlog_data} # set adds it if it doesn't exist and if it does, then it overwrites it
                devlog_operations.append(UpdateOne(id_filter, update, upsert=True)) 
            if devlog_operations:
                print(f"Executing {len(devlog_operations)} devlog upserts")
                batch_size = 1000
                for i in range(0, len(devlog_operations), batch_size):
                    batch = devlog_operations[i:i+batch_size]
                    try:
                        result = devlog_collection.bulk_write(batch, ordered=False)
                        print(f"Devlog batch {i//batch_size+1}: Modified {result.modified_count}, Upserted {result.upserted_count}")
                    except AutoReconnect as e:
                        print(f"Devlog batch {i//batch_size+1} failed: {e}")
                print("Devlog processing complete.")
            else:
                print("No devlog operations needed!")

            # projects
            url = "https://summer.hackclub.com/api/v1/projects"
            pages = await get_total_pages(session=session, url=url)
            print(f"Total pages: {pages}")

            projects = await fetch_all_pages(total_pages=pages, session=session, url=url, is_devlogs=False)
            print("Fetched all projects!")


            project_operations = [] # the operations for bulk write
            for project in projects:
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
                id_filter = {"id": project_data["id"]} # the id will be used to check if the project exists already
                update = {"$set": project_data}
                project_operations.append(UpdateOne(id_filter, update, upsert=True)) # upsert will basically add the object no matter if it exists or not

            if project_operations:
                print(f"Executing {len(project_operations)} project upserts.")
                batch_size = 1000
                for i in range(0, len(project_operations), batch_size):
                    batch = project_operations[i:i+batch_size]
                    try:
                        result = project_collection.bulk_write(batch, ordered=False)
                        print(f"Project batch {i//batch_size+1}: Modified {result.modified_count}, Upserted {result.upserted_count}")
                    except Exception as e:
                        print(f"Project batch {i//batch_size+1} failed: {e}")
                print("Project processing complete.")
            else:
                print("No project operations needed!")
    except Exception as e:
        print(f"Exception in main! {e}")

if __name__ == "__main__":
    asyncio.run(main())