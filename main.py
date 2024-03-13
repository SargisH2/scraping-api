from fastapi import FastAPI
from pydantic import BaseModel
from autodoc_scraping import find_in_autodoc, run_autodoc_page_scraper
from onlinecarparts_scraping import find_in_onlinecarparts, run_onlinecarparts_page_scraper
import json 

app = FastAPI()

class SearchQuery(BaseModel):
    query: str
    images: bool = True
    is_page: bool = False

@app.post("/get-content-autodoc/")
async def get_content_autodoc(input: SearchQuery):
    get_images = input.images
    if input.is_page:
        scraped_data = run_autodoc_page_scraper(input.query, get_images = get_images)
    else:
        results_dict = find_in_autodoc(input.query, supplier = '10706')
        if not results_dict:
            return {"content": "No results found"}
        finded_item = list(results_dict.keys())[0]
        url = list(results_dict.values())[0]
        scraped_data = run_autodoc_page_scraper(url, get_images = get_images)
    
    return scraped_data

@app.post("/get-content-onlinecarparts/")
async def get_content_onlinecarparts(input: SearchQuery):
    get_images = input.images
    results_dict = find_in_onlinecarparts(input.query)
    if not results_dict:
        return {"content": "No results found"}
    finded_item = list(results_dict.keys())[0]
    url = list(results_dict.values())[0]
    scraped_data = run_onlinecarparts_page_scraper(url, get_images = get_images)
    
    return scraped_data

@app.get("/")
async def root():
    return {
        "autodoc": "send post request to /get-content-autodoc/ with query in json format. Example: {'query': 'thermostat'}",
        "onlinecarparts.co.uk": "send post request to /get-content-onlinecarparts/ with query in json format. Example: {'query': 'thermostat'}",
        }
