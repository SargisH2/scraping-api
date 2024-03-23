from fastapi import FastAPI
from pydantic import BaseModel
from autodoc_scraping import find_in_autodoc, run_autodoc_page_scraper
from onlinecarparts_scraping import find_in_onlinecarparts, run_onlinecarparts_page_scraper
from time import localtime, strftime
import time

suppliers = {
    "motorad": '10706',
    "mahle": '10223'
}

app = FastAPI()

class SearchQuery(BaseModel):
    query: str
    is_page: bool = False
    depth: int = 2
    supplier: str = "motorad"
    
max_depth = 0

@app.post("/get-content-autodoc/")
async def get_content_autodoc(input: SearchQuery):
    depth = input.depth
    global max_depth
    if not input.is_page: max_depth = depth
    
    print("\n\n", "STARTING DEPTH", depth, "\n\n")
    items_list = []
    items_tree = dict()
    
    if input.is_page:
        scraped_data = run_autodoc_page_scraper(input.query)
    else:
        supplier_code = suppliers[input.supplier]
        results_dict = find_in_autodoc(input.query, supplier = supplier_code)
        if not results_dict:
            return {"content": "No results found"}
        url = list(results_dict.values())[0]
        scraped_data = run_autodoc_page_scraper(url)
        
    urls = [item['url'] for item in scraped_data['similar_products'] if item['url']]
    similar_keys = [url.split('/')[-1] for url in urls]
    key = scraped_data['autodoc_product_code']
    items_tree.update({
            key: {
                similar_key: None
                for similar_key in similar_keys}
        })
    items_list.append(scraped_data)
    
    if depth > 1:
        print("\n\n", "Start scraping similars for depth", depth, "...\n\n")
        for url in urls:
            req_obj = SearchQuery
            req_obj.query = url
            req_obj.is_page = True
            req_obj.depth = depth -1
            new_items = await get_content_autodoc(req_obj)
            items_list.extend(new_items['items'])
            items_tree.update(new_items['tree'])
            new_key = url.split('/')[-1]
            if items_tree.get(key) and new_key in items_tree.values():
                items_tree[key][new_key] = new_items['tree'][new_key]
                
        print("\n\n", "Done for depth", depth, "\n\n")
    
    
    return_obj =  {
            'info':{
                'depth': depth,
                'total': len(set([item['autodoc_product_code'] for item in items_list])),
                'time': get_time(),
                'supplier': None if input.is_page else input.supplier
            },
            'tree': items_tree if input.is_page else {key: build_tree(key, items_tree, max_depth+1)},
            'items': items_list
        }
    
    return return_obj

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

def get_time():
    seconds = time.time()
    formatted_time = strftime("%d.%m.%y/%H:%M:%S", localtime(seconds))
    return formatted_time
    