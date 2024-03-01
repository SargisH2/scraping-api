from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup, Tag

BASE_URL = 'https://www.autodoc.co.uk/spares-search?keyword='

def class_to_key(class_part):
    dct = {
        'icon-text--availability': 'availability',
        'icon-text-list': 'other_info',
        'inkl': 'price_including'
    }
    return dct.get(class_part) if class_part in dct.keys() else class_part.lower().replace(' ', '_')

def get_details(detail_block):
    return_info = {}
    sections = detail_block.find_all('div', recursive=False)
    details, numbers = sections[0], sections[-1]
    
    number_details = numbers.select('div.product-block__seo-info-text')[0].text.split(':')[1]
    number_details = {'trade_numbers': list(map(lambda x: x.strip(), number_details.split('\n')))}
    return_info.update(number_details)
    
    product_details = details.select('ul.product-description__list')[0]
    detail_items = {}
    for li_tag in product_details.children:
        if(isinstance(li_tag, Tag)):
            name, value = li_tag.find_all('span', recursive=False)
            name, value = name.text.strip().rstrip(':'), value.text.strip()
            name, value = name.lower().replace('  ', '').replace(' ', '_').replace('_/_', '/'), value.replace('  ', '').replace('\n', ' ')
            detail_items.update({name: value})
    return_info.update(detail_items)
            
    return return_info

def get_pricing(pricing_block):
    return_info = {}
    divs_to_extract = pricing_block.find_all(recursive=False)
    for div in divs_to_extract[:-2]:
        p_tags = div.find_all('p', recursive=False)
        if p_tags:
            text_content = [p.get_text(strip=True) for p in p_tags]
        else:
            text_content = div.get_text(strip=True).replace('  ', '').replace('\n', ' ')
        if 'class' in div.attrs and text_content:
            key = div['class'][-1].split('__')[1]
            key = class_to_key(key)
            return_info[key] = text_content
    
    return return_info

def get_autodoc_json(content):
    soup = BeautifulSoup(content, 'html.parser')
    
    # product section
    product_info = soup.select('section.section.wrap')[0] 
    return_obj = {
        'autodoc_product_code': product_info.findChild('div')['data-article-id']
    }
    
    # heading line
    head_tag = product_info.find('h1')
    return_obj.update({
        'head_name': head_tag.contents[0].strip(),
        'head_description': head_tag.findChildren('span')[1].get_text()
    })
    
    num_info = product_info.select('span.product-block__article')
    for span_tag in num_info:
        inner_data = span_tag.get_text().strip()
        num_name, num_content = inner_data.split(': ')
        return_obj.update({
            num_name.lower().replace(' ', '_'): num_content
        })
        
        
    # detail block
    detail_block = product_info.select('div.col-12.col-lg-4.order-last.order-lg-0')[0]
    product_details = get_details(detail_block)
    return_obj.update(product_details)
    
    # pricing block
    pricing_block = product_info.select('div.col-12.col-md-6.col-lg-4')[1]
    pricing_details = get_pricing(pricing_block)
    return_obj.update(pricing_details)
    
    return return_obj

def get_urls(content):
    content = BeautifulSoup(content, 'html.parser')
    hrefs = {}
    for a_tag in content.select('a.listing-item__name'):
        text_parts = []
        
        if a_tag.contents:
            for child in a_tag.contents:
                if child.name is None and child.strip():
                    text_parts.append(child.strip())
                elif child.name == 'span' and 'highlight' in child.get('class', []):
                    text_parts.append(child.get_text(strip=True))
        
        if text_parts:
            hrefs[' '.join(text_parts)] = a_tag['href']
    
    return hrefs

app = FastAPI()

class SearchQuery(BaseModel):
    query: str
    

@app.post("/get-content/")
async def get_content(input: SearchQuery):
    chrome_options = Options()
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    
    # Ensure you have the ChromeDriver executable in your PATH or specify its path with the executable_path argument
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(BASE_URL+input.query)
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "listing-title__name"))
        )
        content = driver.page_source
        results_dict = get_urls(content)
    except Exception as e:
        driver.quit()
        return {"content": 'Search failed: '+str(e)}
    result = list(results_dict.keys())[0]
    url = list(results_dict.values())[0]
    
    try:
        driver.get(url)
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "product-block__description-title"))
        )
        content = driver.page_source
        scraped_data = get_autodoc_json(content)
    except Exception as e:
        driver.quit()
        raise HTTPException(status_code=500, detail=f"Failed to load content from {url}: {str(e)}")
    finally:
        driver.quit()

    return {result: scraped_data}
