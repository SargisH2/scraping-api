from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://www.onlinecarparts.co.uk/spares-search.html?keyword="
chrome_options = Options()
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")


def find_in_onlinecarparts(query):
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(BASE_URL+query)
    element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "title-car"))
    )
    content = driver.page_source
    results_dict = get_urls(content)
    driver.quit()
    return results_dict

def get_urls(content):
    content = BeautifulSoup(content, 'html.parser')
    hrefs = {}
    for a_tag in content.select('a.product-card__title-link'):
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

def scrape_bottom_blocks(info_blocks):
    blocks_content = dict()
    if len(info_blocks) > 1:
        block_container = info_blocks[0].find('div', recursive=False)
        blocks = block_container.find_all('div', recursive=False)
        for i, block in enumerate(blocks):
            print('Scraping bottom block', i)
            block_name = block.get('class')[0]
            blocktitle = block.select(f'div.{block_name}__title')[0].get_text().strip().lower().replace(' ', '_')
            block_content = []
            content_lists = block.find_all('ul')
            for content_list in content_lists:
                if 'equivalents' not in blocktitle:
                    list_data = [li_tag.get_text().strip() for li_tag in content_list.select('li')]
                else:
                    list_data = {}
                    for li_tag in content_list.select('li'):
                        if len(li_tag.contents) == 3 and li_tag.contents[0] == '\n':
                            k, w = li_tag.contents[1:]
                            list_data.update({
                                k.get_text().strip(): w.get_text().strip()
                            })
                        
                if list_data: block_content.append(list_data)
                
            if not block_content:
                continue
            if len(block_content) == 1:
                block_content = block_content[0]
            blocks_content.update({
                blocktitle: block_content
            })
    return blocks_content

def get_description_details(detail_block):
    return_info = {}
    details_table, advantages_list = detail_block.select('table.product__table')[0], detail_block.select('ul.product__advantages-list')[0]
    
    advantages_list = advantages_list.select('div.product__advantages-title')
    advantages = {'advantages': list(map(lambda x: x.get_text(strip=True), advantages_list))}
    return_info.update(advantages)
    
    detail_rows = details_table.select('tr')
    detail_items = {
        row.select('td')[0].get_text(strip=True).lower().replace(' ', '_'): row.select('td')[1].get_text(strip=True)
        for row in detail_rows
    }
    return_info.update(detail_items)
    
    return return_info

def get_price_info(pricing_block):
    return_info = {}
    
    return_info['price'] = pricing_block.select('div.product__new-price')[0].get_text(strip=True).replace('\u00a3', '£')
    if pricing_block.select('div.product__old-price'):
        return_info['old_price'] = pricing_block.select('div.product__old-price')[0].get_text(strip=True).replace('\u00a3', '£')
    
    divs_to_extract = pricing_block.find_all('div', recursive=False)[2:-2] # (price ; stock)
    
    for div in divs_to_extract:
        text_content = div.get_text(strip=True).replace('  ', '').replace('\n', ' ')
        if 'class' in div.attrs and text_content:
            key = div['class'][-1].split('__')[1]
            return_info[key] = text_content
    return_info['status'] = pricing_block.select('div.product__status')[0].get_text(strip=True)
        
    return return_info

def get_onlinecarparts_json(content):
    soup = BeautifulSoup(content, 'html.parser')
    product_page = soup.find(attrs={'id':'main'})
    
    # product code
    product_info = product_page.select('div.product')[0] 
    return_obj = {
        'onlinecarparts_product_code': product_info['data-article-id']
    }
    
    # heading line
    head_tag = product_page.find('h1')
    article_tag_text = product_info.select('div.product__artkl')[0].get_text().strip()
    return_obj.update({
        'head_name': head_tag.contents[0].strip(),
        'head_description': head_tag.findChildren('span')[0].get_text(),
        "product_article": article_tag_text.replace('\u2116', 'N').replace('  ', '').replace('\n', ' ')
    })
    
    # info blocks
    info_blocks = product_page.select('div.product-info-blocks')
    block_details = scrape_bottom_blocks(info_blocks)
    return_obj.update(block_details)
        
    # detail block
    detail_block = product_info.select('div.product__description')[0]
    product_details = get_description_details(detail_block)
    return_obj.update(product_details)
    
    # pricing block
    pricing_block = product_info.select('div.product__info')[0]
    pricing_details = get_price_info(pricing_block)
    return_obj.update(pricing_details)

    return return_obj
    
def run_onlinecarparts_page_scraper(url):
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "product"))
    )
    content = driver.page_source
    scraped_data = get_onlinecarparts_json(content)
        
    scraped_data['url'] = url
    driver.quit()
    return scraped_data
