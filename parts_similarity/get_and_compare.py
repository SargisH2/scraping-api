import requests
import json

GEMINI_PROMPT = """
Your task involves a two-step analysis process. Begin by thoroughly examining the visual content of a set of images. Note down key visual features, themes, elements, and any patterns or inconsistencies you observe. Once you've completed this visual analysis, proceed to examine the textual data for two distinct items. Here are the details for each item:

After reviewing both the images and the textual data, your objective is to evaluate and quantify the level of similarity between the items, using content of the images and textual data points. Rate the similarity on a scale from 0 (completely dissimilar) to 1 (identical). Additionally, provide a detailed analysis explaining the key features, themes, or elements that led to your rating. This includes discussing aspects where they align (similarities) and where they diverge (differences).
"""
GENERATION_CONFIG={
            "max_output_tokens": 2048,
            "temperature": 0.4,
            "top_p": 1,
            "top_k": 32
        } # default

api_url = 'http://127.0.0.1:8000/get-content-autodoc/'
main_part_data = {
    "query": '743-88K'
}

import base64
from urllib.request import Request, urlopen
def get_encoded(url):
    try:
        req = Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
        contents = urlopen(req).read()
        data = base64.b64encode(contents)
        return base64.b64decode(data)
    except Exception as e:
        print('\nImage Couldn\'t be retrieved\n' + url + '\n Error: ', e)


DATA_FILE = 'scraped_items.json'
RESULTS_LIST = []
def scrape_data():
    response = requests.post(api_url, json=main_part_data)
    scraped_item = response.json()
    RESULTS_LIST.append(scraped_item)
    similar_items = scraped_item.get('similar_products')
    if similar_items:
        item_urls = [item.get('url') for item in similar_items if item.get('url')]
        for item_url in item_urls:
            similar_part_data = {
                "query": item_url,
                "is_page": True
            }
            print('Scraping', item_url, end = ' ')
            response_similar_item = requests.post(api_url, json=similar_part_data)
            similar_item_data = response_similar_item.json()
            RESULTS_LIST.append(similar_item_data)
            print('Done')
            break ####
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(RESULTS_LIST, f)
    
def read_data():
    file_content = json.load(open(DATA_FILE, 'r', encoding='utf-8'))
    return file_content

# scrape_data()
all_items = read_data()
print('done', len(all_items))

## modified original script
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part
import vertexai.preview.generative_models as generative_models

def split_raw_data(item_dict): #return Part objects for images and text data
    images = item_dict.get('images')
    image_parts = []
    if images:
        encoded_images = [get_encoded(url) for url in images if url[-3:]!='svg']
        print('Saved images:', len(encoded_images))
        image_parts = [Part.from_data(img_encoded, mime_type="image/jpeg") for img_encoded in encoded_images]
    
    text_data = json.dumps(dict(list(item_dict.items())[:-3]))
    print('\n'*5, text_data, '\n'*5)
    return image_parts, text_data
    

main_item, item_to_compare = all_items[0], all_items[1]
images1, details1 = split_raw_data(main_item)
images2, details2 = split_raw_data(item_to_compare)


def compare(images1, details1, images2, details2):
    vertexai.init(project="capable-matrix-408007", location="europe-west1")
    model = GenerativeModel("gemini-1.0-pro-vision-001")
    print('images: ', len(images1), ' | ', len(images2))
    responses = model.generate_content(
        # [GEMINI_PROMPT.format(details1, details2)],
        [GEMINI_PROMPT, 'Text data for Item 1:\n'+details1, '\nimages for first item:', *images1, 'Text data for Item 2:\n'+details2, '\nimages for second item: ', *images2],
        generation_config=GENERATION_CONFIG,
        safety_settings={
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
    )
  
    print(responses.text)


compare(images1, details1, images2, details2)