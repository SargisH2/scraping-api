from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from autodoc_scraping import find_in_autodoc, run_autodoc_page_scraper
# from onlinecarparts_scraping import find_in_onlinecarparts, run_onlinecarparts_page_scraper
from time import gmtime, strftime
import requests

suppliers = {
    "motorad": '10706',
    "mahle": '10223'
}

app = FastAPI()

class SearchQuery(BaseModel):
    query: str
    webhook_url: str = None
    is_page: bool = False
    depth: int = 2
    supplier: str = "motorad"
    query_id: str = None
    

@app.post("/get-content-autodoc/")
async def process_request(background_tasks: BackgroundTasks, input: SearchQuery):
    # Add the long process to the background tasks
    if input.webhook_url:
        background_tasks.add_task(get_content_autodoc, input)
        return {"message": "Processing started, you'll be notified upon completion."}
    else:
        return get_content_autodoc(input)

# Process the request
def get_content_autodoc(input: SearchQuery):
    depth = input.depth
    print("\n\n", "STARTING DEPTH", depth, "\n\n")
    items_list = []
    items_tree = dict()
    
    # Get page result. Check if the input query is not url, get page url
    if input.is_page:
        scraped_data = run_autodoc_page_scraper(input.query)
    else:
        supplier_code = suppliers[input.supplier]
        results_dict = find_in_autodoc(input.query, supplier = supplier_code)
        if not results_dict:
            return {"content": "No results found"}
        url = list(results_dict.values())[0]
        scraped_data = run_autodoc_page_scraper(url)
        
    # Get info about similar items
    similars = scraped_data.get('similar_products')
    if similars:
        urls = [item['url'] for item in similars if item['url']]
    else:
        return {"content": "No results found"}
    
    similar_keys = [url.split('/')[-1] for url in urls]
    
    # key - product code for this item, update items_tree and items_list for current item
    key = scraped_data['autodoc_product_code']
    items_tree.update({
            key: {
                similar_key: None
                for similar_key in similar_keys}
        })
    items_list.append(scraped_data)
    
    # Check the depth for limit the recursion, scrape all possible similar items
    if depth > 1:
        print("\n\n", "Start scraping similars for depth", depth, "...\n\n")
        for url in urls:
            req_obj = SearchQuery
            req_obj.query = url
            req_obj.is_page = True
            req_obj.depth = depth -1
            new_items = get_content_autodoc(req_obj)
            if new_items.get('content') == "No results found": continue
            items_list.extend(new_items['items'])
            items_tree.update(new_items['tree'])
            new_key = url.split('/')[-1]
            if items_tree.get(key) and new_key in items_tree.values():
                items_tree[key][new_key] = new_items['tree'][new_key]
                
        print("\n\n", "Done for depth", depth, "\n\n")
    
    # Prepare results, send to the webhook or return for recursion case
    return_obj =  {
            'info':{
                'depth': depth,
                'total': len(set([item['autodoc_product_code'] for item in items_list])),
                'time': get_time(),
                'supplier': None if input.is_page else input.supplier
            },
            'tree': items_tree if input.is_page else {key: build_tree(key, items_tree, depth+1)},
            'items': items_list
        }
    if input.is_page:
        return return_obj
    else:
        return_obj.update({
            'query_id': input.query_id
        })
        requests.post(input.webhook_url, json=return_obj)

# @app.post("/get-content-onlinecarparts/")
# async def get_content_onlinecarparts(input: SearchQuery):
#     results_dict = find_in_onlinecarparts(input.query)
#     if not results_dict:
#         return {"content": "No results found"}
#     finded_item = list(results_dict.keys())[0]
#     url = list(results_dict.values())[0]
#     scraped_data = run_onlinecarparts_page_scraper(url)
    
#     return scraped_data

@app.get("/")
async def root():
    return {
        "autodoc": "send post request to /get-content-autodoc/ with query in json format. Example: {'query': 'thermostat'}",
        "onlinecarparts.co.uk": "send post request to /get-content-onlinecarparts/ with query in json format. Example: {'query': 'thermostat'}",
        }

# Build a tree from raw tree list
def build_tree(node, tree_dict, max_depth, depth = 0, visited=None):
    if visited is None:
        visited = set()
    if depth == max_depth or node in visited:
        return {}
    
    if node not in tree_dict:
        return None
    
    visited.add(node)
    
    subtree = {child: build_tree(child, tree_dict, max_depth, depth+1, visited.copy()) for child in tree_dict[node]}
    return subtree

# Current time in gmt
def get_time():
    formatted_time = strftime("%d.%m.%y/%H:%M:%S", gmtime())
    return formatted_time
    
    
# ToDO: handle onlinecarparts scraping