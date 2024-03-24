from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests
import json

app = FastAPI()

SERVER_URL = "https://scraping-api-app-b55c363cbea4.herokuapp.com/"
WEBHOOK_URL = "http://127.0.0.1:8080/webhook/" # set port to 8080

class SearchQueryWebHook(BaseModel):
    query: str
    depth: int = 2
    supplier: str = "motorad"
    
# Send data to process
@app.post("/start-process/")
async def start_process(query: SearchQueryWebHook):
    data = {
        "query": query.query,
        "depth": query.depth,
        'supplier': query.supplier,
        "webhook_url": WEBHOOK_URL
    }
    # Make a request to the server to start the long process
    response = requests.post(SERVER_URL+'get-content-autodoc/', json=data)
    return response.json()

# Receive data
@app.post("/webhook/")
async def webhook_receiver(request: Request):
    # Receive the webhook notification
    data = await request.json()
    print(f"Webhook received data")
    with open('test.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    return {"message": "Webhook received, check logs and test.json for the data."}
