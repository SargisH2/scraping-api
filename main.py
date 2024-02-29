from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

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
    
    
    return return_obj



app = FastAPI()

class URLInput(BaseModel):
    url: str
    

@app.post("/get-content/")
async def get_content(input: URLInput):
    chrome_options = Options()
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    
    # Ensure you have the ChromeDriver executable in your PATH or specify its path with the executable_path argument
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(input.url)
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "product-block__icon-text-list"))
        )
        content = driver.page_source
        scraped_data = get_autodoc_json(content)
    except Exception as e:
        driver.quit()
        raise HTTPException(status_code=500, detail=f"Failed to load content from {input.url}: {str(e)}")
    finally:
        driver.quit()

    return {"content": scraped_data}
