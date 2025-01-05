import logging
from datetime import datetime
import hashlib
from functools import lru_cache
from bs4 import BeautifulSoup
import yfinance as yf
from django.core.cache import cache
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import json
import time
import chromedriver_autoinstaller
import requests


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('uranium_app')


server_config = True


URANIUM_STOCKS = [
    'URA', 'CCJ', 'DNN', 'UUUU', 'UEC', 'NXE', 'UROY',
    
    'U-UN.TO', 'CCO.TO', 'DML.TO', 'FCU.TO', 'LAM.TO',
    
    'CVV.V', 'AEC.V', 'AL.V', 'FMC.V', 'ISO.V', 'SYH.V', 'GXU.V',
    
    'BKUCF', 'CVVUF',  'FCUUF', 'LMRXF', 'NATKY',
    
    'PDN.AX', 'BOE.AX', 'DYL.AX', 'BMN.AX', 'LOT.AX', 'ERA.AX', 'TOE.AX','NFL.AX',
    'BKY.AX', 'GTR.AX', 'HAV.AX', 'MEU.AX', 'MHC.AX', 'RIO.AX', 'ENR.AX',
    'POW.AX', 'RDM.AX', 'RLC.AX', 'AND.AX', 'CUL.AX', 'EBR.AX','GLA.AX',
    
    'BHP.L', 'RIO.L', 'YCA.L', 'BKY.L'
]

@lru_cache(maxsize=1)
def get_uranium_stocks():
    return URANIUM_STOCKS

# Global variable to store the fetched data
global_uranium_data = None

def fetch_data_daily():
    global global_uranium_data
    logger.info("Starting daily data fetch...")
    global_uranium_data = fetch_uranium_data()
    logger.info("Daily data fetch completed.")

# Schedule the daily data fetch
# schedule.every().day.at("00:00").do(fetch_data_daily)

# # Function to run the scheduler in a separate thread
# def run_scheduler():
#     while True:
#         schedule.run_pending()
#         time.sleep(1)

# # Start the scheduler thread
# scheduler_thread = threading.Thread(target=run_scheduler)
# scheduler_thread.start()

def fetch_uranium_stocks():
    cache_key = 'uranium_stocks_data'
    cached_data = cache.get(cache_key)

    if cached_data:
        return cached_data

    with requests.Session() as session:
        stock_data_results = [fetch_single_stock(symbol, session) for symbol in get_uranium_stocks()]
    
    stock_data = dict(stock_data_results)
    cache.set(cache_key, stock_data, timeout=3600)
    return stock_data


def fetch_single_stock(symbol, session):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        history = stock.history(period="1y")
        country_name = info.get("country", None)

        if history.empty:
            logger.warning(f"No data found for {symbol}, skipping...")
            return symbol, {}
        
        current_price = history['Close'].iloc[-1]
        last_price = history['Close'].iloc[-2]
        change_1m = ((current_price - history['Close'].iloc[-22]) / history['Close'].iloc[-22]) * 100
        change_1y = ((current_price - history['Close'].iloc[0]) / history['Close'].iloc[0]) * 100
        
        return symbol, {
            'name': info.get('longName', 'N/A'),
            'current_price': current_price,
            'last_price': last_price,
            'change_1m': change_1m,
            'change_1y': change_1y,
            'volume': info.get('volume', 'N/A'),
            'market_cap': info.get('marketCap', 'N/A'),
            'pe_ratio': info.get('trailingPE', 'N/A'),
            'data': history['Close'].tolist(),
            'dates': history.index.strftime('%Y-%m-%d').tolist(),
            'country_name': country_name
        }
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        return symbol, {}
    

def fetch_uranium_price(driver):
    cache_key = 'uranium_price_data'
    cached_data = cache.get(cache_key)

    if cached_data:
        return cached_data

    url = 'https://numerco.com/NSet/aCNSet.html'
    
    # chromedriver_autoinstaller.install()

    # options = Options()
    # options.add_argument('--headless')
    # options.add_argument('--no-sandbox')
    # options.add_argument('--disable-dev-shm-usage')

    # if server_config:
    #     options.binary_location = "/usr/bin/chromium"

    #     service = Service(executable_path="/usr/bin/chromedriver")

    #     driver = webdriver.Chrome(service=service, options=options)
    
    # else:
    #     driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)
        
        # Wait for the spot price to be present and not empty
        try:
            spot_price_element = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "spottU3o8"))
            )
            WebDriverWait(driver, 30).until(
                lambda d: spot_price_element.text != ""
            )
            spot_price = spot_price_element.text
        except TimeoutException:
            logger.error("Timeout waiting for spot price to load")
            spot_price = "N/A"

        logger.info(f"Spot price: {spot_price}")

        # Wait for the table to be present
        try:
            table_element = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "CVDtradesTable"))
            )
            table_html = table_element.get_attribute('outerHTML')
            soup = BeautifulSoup(table_html, 'html.parser')
            headers = [th.text.strip() for th in soup.find_all('th')]
            tbody = soup.find('tbody')
            if tbody:
                data = [[cell.text.strip() for cell in row.find_all('td')] for row in tbody.find_all('tr')]
            else:
                data = []
        except TimeoutException:
            logger.error("Timeout waiting for table to load")
            headers = []
            data = []

        logger.info(f"Headers: {headers}")
        logger.info(f"Data rows: {len(data)}")

        result = {
            'spot_price': spot_price,
            'headers': headers,
            'data': data
        }
        cache.set(cache_key, result, timeout=3600)
        return result
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return {'error': f"An error occurred: {str(e)}"}
    # finally:
        # driver.quit()

def fetch_calendar_data(driver):
    cache_key = 'calendar_data'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return cached_data
    
    current_year = datetime.now().year
    url = f'https://www.uxc.com/p/fuelcycle/Calendar.aspx?year={current_year}'
    
    # chromedriver_autoinstaller.install()

    # options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    # options.add_argument('--no-sandbox')
    # options.add_argument('--disable-dev-shm-usage')
    
    
    # if server_config:
    #     options.binary_location = "/usr/bin/chromium"  

    #     service = Service(executable_path="/usr/bin/chromedriver")

    #     driver = webdriver.Chrome(service=service, options=options)
    
    # else:
    #     driver = webdriver.Chrome(options=options)
    
    driver.get(url)
    

    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "td.rcMain.rcCalendars"))
    )
    
    try:
        # Extract the calendar HTML
        calendar_html = driver.find_element(By.CSS_SELECTOR, 'td.rcMain.rcCalendars').get_attribute('innerHTML')

        event_rows = driver.find_elements(By.CSS_SELECTOR, 'table.table-striped tbody tr:not(:first-child)')
        event_data = []

        for row in event_rows:
            try:
                date_element = row.find_element(By.CSS_SELECTOR, 'td.text-center')
                date = date_element.text.strip() if date_element else 'N/A'
                
                title_element = row.find_element(By.CSS_SELECTOR, 'div.lead a')
                title = title_element.text.strip() if title_element else 'N/A'
                link = title_element.get_attribute('href').strip() if title_element else 'N/A'
                
                details = row.find_elements(By.CSS_SELECTOR, 'dl.dl-horizontal dt')
                details_texts = row.find_elements(By.CSS_SELECTOR, 'dl.dl-horizontal dd')
                details_dict = {}

                for dt, dd in zip(details, details_texts):
                    key = dt.text.strip().lower()
                    text = dd.text.strip()
                    href = dd.find_element(By.TAG_NAME, 'a') if dd.find_elements(By.TAG_NAME, 'a') else None
                    href_link = href.get_attribute('href').strip() if href else 'N/A'
                    details_dict[key] = {
                        'text': text,
                        'link': href_link
                    }

                location = details_dict.get('location', {'text': 'N/A', 'link': 'N/A'})
                sponsor = details_dict.get('sponsor', {'text': 'N/A', 'link': 'N/A'})
                contact = details_dict.get('contact', {'text': 'N/A', 'link': 'N/A'})
                description = details_dict.get('description', {'text': 'N/A', 'link': 'N/A'})

                event_item = {
                    'date': date,
                    'title': title,
                    'link': link,
                    'location': location['text'],
                    'location_link': location['link'],
                    'sponsor': sponsor['text'],
                    'sponsor_link': sponsor['link'],
                    'contact': contact['text'],
                    'contact_link': contact['link'],
                    'description': description['text'],
                }
                event_data.append(event_item)

            except Exception as e:
                logger.error(f"Error processing event row: {str(e)}")
        
        # Return both event data and the calendar HTML
        return {
            'calendar_html': calendar_html,
            'event_data': event_data
        }

    except Exception as e:
        logger.error(f"Error in fetching/opening calendar data: {str(e)}")
        driver.quit()
        return None
    

def fetch_iaea_news(driver):
    logger.info("Starting fetch_iaea_news function")
    
    # options = Options()
    # options.add_argument('--headless')
    # options.add_argument('--no-sandbox')
    # options.add_argument('--disable-dev-shm-usage')

    try:
        logger.info("Setting up Selenium WebDriver")

        # if server_config:
        #     options.binary_location = "/usr/bin/chromium"  

        #     service = Service(executable_path="/usr/bin/chromedriver")

        #     driver = webdriver.Chrome(service=service, options=options)
        
        # else:
        #     driver = webdriver.Chrome(options=options)
        
        
        url = 'https://www.iaea.org/news?year%5Bvalue%5D%5Byear%5D=&type=All&topics=All&keywords=nuclear'
        logger.info(f"Navigating to URL: {url}")
        driver.get(url)
        
        logger.info("Waiting for news container to load")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "views-bootstrap-grid-1"))
        )
        
        logger.info("Parsing page content with BeautifulSoup")
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        news_container = soup.find('div', id='views-bootstrap-grid-1')
        if not news_container:
            logger.error("Could not find IAEA news container")
            return []

        news_items = news_container.find_all('div', class_='grid')
        logger.info(f"Found {len(news_items)} news items")
        
        news_data = []
        for item in news_items:
            try:
                link_element = item.find('h4').find('a')
                if link_element:
                    link = f"https://www.iaea.org{link_element['href']}"
                    title = link_element.text.strip()
                else:
                    logger.warning("Skipping item without link")
                    continue

                image_element = item.find('img')
                image_url = f"https://www.iaea.org{image_element['src']}" if image_element else None

                date_element = item.find('span', class_='dateline-published')
                published_date = date_element.text.strip() if date_element else 'N/A'
                try:
                    published_date = datetime.strptime(published_date, "%d %B %Y").strftime('%Y-%m-%d')
                except ValueError:
                    logger.warning(f"Failed to parse date IAEA: {published_date}")
                    published_date = 'N/A'

                content_type_element = item.find('div', class_='content-type-label-wrapper')
                content_type = content_type_element.text.strip() if content_type_element else 'N/A'

                news_item = {
                    'id': hashlib.md5(link.encode()).hexdigest(),
                    'title': title,
                    'link': link,
                    'publisher': 'IAEA',
                    'published_date': published_date,
                    'image_url': image_url,
                    'content': content_type,
                }
                news_data.append(news_item)
                logger.info(f"Processed news item: {title}")
            except Exception as e:
                logger.error(f"Error processing news item: {str(e)}", exc_info=True)

        logger.info(f"Finished processing {len(news_data)} news items")
        return news_data
    except Exception as e:
        logger.error(f"Error in fetch_iaea_news: {str(e)}", exc_info=True)
        return []
    # finally:
    #     if 'driver' in locals():
    #         logger.info("Closing Selenium WebDriver")
    #         driver.quit()


def scrape_nuclear_data(driver):
    logger.info('Starting nuclear data scraping...')
    cache_key = 'nuclear_data'
    
    # options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    # options.add_argument('--no-sandbox')
    # options.add_argument('--disable-dev-shm-usage')
    
    # if server_config:
    #     options.binary_location = "/usr/bin/chromium"  
    #     service = Service(executable_path="/usr/bin/chromedriver")
    #     driver = webdriver.Chrome(service=service, options=options)
    # else:
    #     driver = webdriver.Chrome(options=options)
    
    driver.get("https://world-nuclear.org/nuclear-reactor-database/summary")
    
    logger.info('Waiting for page to load...')
    # time.sleep(10)  # Increase wait time to ensure all elements are loaded
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "do_counter1"))
    )
    
    data = {}

    try:
        logger.info('Scraping basic nuclear data...')
        counters = driver.find_elements(By.CLASS_NAME, 'do_counter1')
        data['operable_reactors'] = counters[0].text
        data['global_share'] = counters[1].text
        data['under_construction'] = counters[2].text
        logger.info(f'Basic nuclear data: {data}')

        logger.info('Scraping chart data...')
        data['top_10_countries'] = scrape_chart_data(driver, '#TotalOperableReactorBarChart')
        data['reactors_under_construction'] = scrape_chart_data(driver, '#ReactorsUnderConstructionBarChart')
        data['global_nuclear_generation'] = scrape_chart_data(driver, '#GlobalNuclearGenerationByYearChart')
        data['planned_reactors'] = scrape_chart_data(driver, '#PlannedReactorsBarChart')
        data['proposed_reactors'] = scrape_chart_data(driver, '#ProposedReactorsBarChart')
        data['nuclear_electricity_production'] = scrape_chart_data(driver, '#NuclearElectricityProductionBarChart')
        
        logger.info('Scraping table data...')
        data['recent_connections'] = scrape_table_data(driver, 'table.table1')
        data['top_load_factor'] = scrape_table_data(driver, 'table.table2')
        data['top_generation'] = scrape_table_data(driver, 'table.table3')
        data['top_lifetime_generation'] = scrape_table_data(driver, 'table.table4')
        data['recent_construction_starts'] = scrape_table_data(driver, 'table.table5')

        logger.info('Finished scraping nuclear data.')
        logger.debug(f'Scraped data: {json.dumps(data, indent=2)}')

        cache.set(cache_key, data, timeout=60 * 60)  # Cache for 1 hour
        logger.info('Nuclear data cached.')

    except Exception as e:
        logger.error(f'Error during nuclear data scraping: {e}', exc_info=True)
        data = {}

    # finally:
    #     driver.quit()

    return data


def fetch_news_from_mining_com(driver):
    try:
        url = 'https://www.mining.com/?s=uranium'
        driver.get(url)
        time.sleep(2)

        page_content = driver.page_source
        soup = BeautifulSoup(page_content, 'html.parser')

        articles = soup.select('article.post.row.my-4.has-thumbnail')
        news_data = []

        for article in articles:
            title_element = article.find('h2')
            if title_element:
                title = title_element.get_text(strip=True)
                link = title_element.find('a')['href']

            image_element = article.find('img')
            image_url = image_element['src'] if image_element else 'No image available'

            summary_element = article.find('p', class_='post-info')
            summary = summary_element.get_text(strip=True) if summary_element else 'No summary available'

            post_meta = article.find('div', class_='post-meta.mb-3')
            if post_meta:
                post_meta_text = post_meta.get_text(strip=True)
                date_str = post_meta_text.split("|")[1].strip() if "|" in post_meta_text else 'N/A'
                try:
                    published_date = datetime.strptime(date_str, "%B %d, %Y") if date_str != 'N/A' else 'N/A'
                except ValueError:
                    logger.warning(f"Failed to parse date mining_com: {date_str}")
                    published_date = 'N/A'
                author = post_meta.find('a').get_text(strip=True) if post_meta.find('a') else 'N/A'
            else:
                published_date = 'N/A'
                author = 'N/A'

            news_item = {
                'id': hashlib.md5(link.encode()).hexdigest(),
                'title': title,
                'link': link,
                'publisher': 'Mining.com',
                'published_date': published_date,
                'author': author,
                'image_url': image_url,
                'content': summary,
            }

            news_data.append(news_item)

        logger.info(f"Cached {len(news_data)} news items from mining.com")
        return news_data

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return []


def fetch_news_from_nucnet(driver):
    try:
        url = 'https://www.nucnet.org/search?query=NUCLEAR'
        driver.get(url)
        time.sleep(5)

        news_items = driver.find_elements(By.XPATH, "//div[contains(@class, 'search-news-box clickable-box mb-6 md:mb-8')]")
        news_data = []

        for idx, news in enumerate(news_items):
            title_element = news.find_element(By.XPATH, ".//h4[contains(@class, 'news-box-title pr-4')]")
            title = title_element.text if title_element else 'No title available'

            link_element = news.find_element(By.XPATH, ".//a[contains(@class, 'clickable-box-link')]")
            link = link_element.get_attribute("href") if link_element else 'No link available'

            date_element = news.find_element(By.XPATH, ".//time[contains(@class, 'news-box-date')]")
            date_str = date_element.text if date_element else 'N/A'

            # Convert date from "20 September 2024" to "2024-09-20"
            try:
                published_date = datetime.strptime(date_str, "%d %B %Y").strftime("%Y-%m-%d")
            except ValueError:
                published_date = 'N/A'

            image_element = news.find_element(By.XPATH, ".//div[contains(@class, 'news-box-img')]//img")
            image_url = image_element.get_attribute('src') if image_element else 'No image available'

            news_item = {
                'id': hashlib.md5(link.encode()).hexdigest(),
                'title': title,
                'link': link,
                'publisher': 'NUCNET',
                'published_date': published_date,  # Updated date format
                'author': 'N/A',
                'image_url': image_url,
                'content': 'N/A',  # Assuming no content is available on this page
            }

            news_data.append(news_item)

        logger.info(f"Cached {len(news_data)} news items from nucnet.org")
        return news_data

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return []


def fetch_world_nuclear_news_com():
    cache_key = 'world_nuclear_news'
    cached_news = cache.get(cache_key)

    if cached_news:
        return cached_news

    url = 'https://world-nuclear-news.org/search?search=uranium'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        page_content = response.text
        soup = BeautifulSoup(page_content, 'html.parser')
        
        news_container = soup.find('div', id='internal_news_list_wrapper')
        if not news_container:
            logger.error("Could not find news container")
            return []

        news_items = news_container.find_all('a', class_='news_box_link')
        news_data = []

        for item in news_items:
            link = f"https://world-nuclear-news.org{item['href']}"
            title = item.find('div', class_='news_list_title').text.strip()
            content = item.find('div', class_='news_list_intro').text.strip()
            category = item.find('span', class_='news_list_category').text.strip()
            published_date = item.find('span', class_='news_list_predate').text.strip()
            try:
                # Parse the date using the specific format
                date_obj = datetime.strptime(published_date, "%A, %d %B %Y")
                # Convert to the desired format 'YYYY-MM-DD'
                published_date = date_obj.strftime('%Y-%m-%d')
            except ValueError:
                logger.warning(f"Failed to parse date world_nuclear_news: {published_date}")
                published_date = 'N/A'
            
            image_element = item.find('img')
            image_url = f"https://world-nuclear-news.org{image_element['src']}" if image_element else None

            news_item = {
                'id': hashlib.md5(link.encode()).hexdigest(),
                'title': title,
                'link': link,
                'publisher': 'World Nuclear News',
                'published_date': published_date,
                'category': category,
                'content': content,
                'image_url': image_url
            }
            news_data.append(news_item)

        cache.set(cache_key, news_data, timeout=3600)  # Cache for 1 hour
        return news_data
    else:
        logger.error(f"Failed to retrieve world-nuclear-news.org. Status code: {response.status_code}")
        return []


def get_world_nuclear_article_content(url):
    cache_key = f'article_content_{hashlib.md5(url.encode()).hexdigest()}'
    cached_content = cache.get(cache_key)

    if cached_content:
        return cached_content

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            content = response.text
            soup = BeautifulSoup(content, 'html.parser')
            
            article_body = soup.find('div', class_='col-md-8 ArticleBody')
            if article_body:
                paragraphs = article_body.find_all('p')
                content_text = '\n\n'.join([p.get_text() for p in paragraphs])
                
                published_date = article_body.find('p').get_text(strip=True)
                
                related_topics = article_body.find('div', class_='RelatedTopics')
                if related_topics:
                    category = ', '.join([topic.get_text(strip=True) for topic in related_topics.find_all('a')])
                else:
                    category = 'Uncategorized'
                
                image_element = article_body.find('img')
                image_url = f"https://world-nuclear-news.org{image_element['src']}" if image_element else None
                
                result = (content_text, published_date, category, image_url)
                cache.set(cache_key, result, timeout=86400)  # Cache for 24 hours
                return result
            else:
                return "No content available", None, None, None
        else:
            return f"Failed to retrieve the webpage. Status code: {response.status_code}", None, None, None
    except Exception as e:
        logger.error(f"Error fetching article content: {e}")
        return f"Failed due to an error: {e}", None, None, None


def fetch_stock_news(symbol):
    cache_key = f'stock_news_{symbol}'
    cached_news = cache.get(cache_key)

    if cached_news:
        return cached_news

    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news
        news_data = []
        seen_titles = set()  # To keep track of unique titles
        
        for item in news:
            if 'uranium' in item['title'].lower() or 'nuclear' in item['title'].lower():
                published_date = datetime.fromtimestamp(item['providerPublishTime']).strftime('%Y-%m-%d')
                # Check if we've already seen this title
                if item['title'] not in seen_titles:
                    news_item = {
                        'id': hashlib.md5(item['link'].encode()).hexdigest(),
                        'title': item['title'],
                        'link': item['link'],
                        'publisher': item['publisher'],
                        'published_date': published_date,
                        'ticker': symbol,
                        'image_url': item.get('thumbnail', {}).get('resolutions', [{}])[0].get('url', ''),
                        'content': item.get('summary', '')
                    }
                    news_data.append(news_item)
                    seen_titles.add(item['title'])

        cache.set(cache_key, news_data, timeout=3600)  # Cache for 1 hour
        return news_data
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {str(e)}")
        return []


def process_news_articles(articles):
    news_data = []
    first_day_of_month = datetime.now().replace(day=1)
    for article in articles:
        published_date = datetime.strptime(article['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
        if published_date >= first_day_of_month:
            news_item = {
                'id': hashlib.md5(article['url'].encode()).hexdigest(),
                'title': article['title'],
                'link': article['url'],
                'publisher': article['source']['name'],
                'published_date': published_date,
                'image_url': article['urlToImage'],
                'content': article['description']
            }
            news_data.append(news_item)
    return news_data


def get_article_content(url):
    cache_key = f'article_content_{hashlib.md5(url.encode()).hexdigest()}'
    cached_content = cache.get(cache_key)

    if cached_content:
        return cached_content

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            content = response.text
            soup = BeautifulSoup(content, 'html.parser')
            paragraphs = soup.find_all('p')
            article_content = '\n\n'.join([p.get_text() for p in paragraphs])
            cache.set(cache_key, article_content, timeout=86400)
            return article_content
        else:
            logger.error(f"Failed to retrieve article content. Status code: {response.status_code}")
            return "Failed to retrieve the article content."
    except Exception as e:
        logger.error(f"Error fetching article content: {str(e)}")
        return "An error occurred while fetching the article content."
    

def fetch_mining_technology_com_news():
    cache_key = 'mining_technology_com_news'
    cached_news = cache.get(cache_key)

    if cached_news:
        return cached_news

    url = 'https://www.mining-technology.com/s?wpsolr_q=uranium&wpsolr_fq%5B0%5D=sector_str%3AUranium&wpsolr_sort=sort_by_date_desc'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        page_content = response.text
        soup = BeautifulSoup(page_content, 'html.parser')

        articles = soup.select('article.cell.feature.grid-x.border-bottom')
        news_data = []

        for article in articles:
            category_element = article.find('div', class_='category')
            category = category_element.get_text(strip=True) if category_element else 'N/A'

            title_element = article.find('h3')
            if title_element:
                title = title_element.get_text(strip=True)
                link = title_element.find('a')['href']

            description_element = article.find('p')
            description = description_element.get_text(strip=True) if description_element else 'N/A'

            image_element = article.select_one('div.cell.large-4.article-image img')
            image_url = image_element['src'] if image_element else 'N/A'

            # Navigate to the article's URL to fetch additional details
            article_response = requests.get(link, headers=headers)
            if article_response.status_code == 200:
                article_content = article_response.text
                article_soup = BeautifulSoup(article_content, 'html.parser')

                date_element = article_soup.select_one('div.article-meta span.date-published')
                date_str = date_element.get_text(strip=True) if date_element else 'N/A'
                try:
                    published_date = datetime.strptime(date_str, "%B %d, %Y").strftime('%Y-%m-%d') if date_str != 'N/A' else 'N/A'
                except ValueError:
                    logger.warning(f"Failed to parse date mining_tech: {date_str}")
                    published_date = 'N/A'

                author_element = article_soup.select_one('div.article-meta span.author')
                author = author_element.get_text(strip=True) if author_element else 'N/A'

                content_element = article_soup.select_one('div.main-content')
                content = "\n\n".join([p.get_text(strip=True) for p in content_element.find_all('p')]) if content_element else 'N/A'

                news_item = {
                    'id': hashlib.md5(link.encode()).hexdigest(),
                    'publisher': category,
                    'title': title,
                    'published_date': published_date,
                    'author': author,
                    'image_url': image_url,
                    'content': content,
                    'link': link
                }
                news_data.append(news_item)

        cache.set(cache_key, news_data, timeout=3600)  # Cache for 1 hour
        return news_data
    else:
        logger.error(f"Failed to retrieve mining-technology.com news. Status code: {response.status_code}")
        return []


logger = logging.getLogger(__name__)

def fetch_inform_kz_news(driver):
    try:
        url = 'https://en.inform.kz/search_results/?q=nuclear'
        driver.get(url)
        time.sleep(5)

        news_items = driver.find_elements(By.CSS_SELECTOR, "div.searchCard")
        news_data = []

        for idx, news in enumerate(news_items):
            title_element = news.find_element(By.CSS_SELECTOR, "div.searchCard_title")
            title = title_element.text if title_element else 'No title available'

            link_element = news.find_element(By.CSS_SELECTOR, "a")
            link = link_element.get_attribute("href") if link_element else 'No link available'

            date_element = news.find_element(By.CSS_SELECTOR, "div.searchCard_time")
            date_str = date_element.text if date_element else 'N/A'

            # Convert date from "16:20, 28 August 2024" to "2024-08-28"
            try:
                date_parsed = datetime.strptime(date_str.split(",")[1].strip(), "%d %B %Y")
                published_date = date_parsed.strftime("%Y-%m-%d")
            except ValueError:
                published_date = 'N/A'

            image_element = news.find_element(By.CSS_SELECTOR, "picture img")
            image_url = image_element.get_attribute("src") if image_element else 'No image available'

            news_item = {
                'id': hashlib.md5(link.encode()).hexdigest(),
                'title': title,
                'link': link,
                'publisher': 'INFORM.KZ',
                'published_date': published_date,  # Converted date format
                'author': 'N/A',
                'image_url': image_url,
                'content': 'N/A',  # Assuming no content is available on this page
            }

            news_data.append(news_item)

        logger.info(f"Cached {len(news_data)} news items from inform.kz")
        return news_data

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return []


def fetch_news_from_northern_miner_com():
    url = 'https://www.northernminer.com/?s=uranium'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            page_content = response.text
            soup = BeautifulSoup(page_content, 'html.parser')
            
            # Select all article elements with the class 'content-list clearfix'
            articles = soup.select('article.content-list.clearfix')
            news_data = []
            
            for article in articles:
                # Extract the title and link
                title_element = article.find('h3', class_='content-list-title')
                title = title_element.get_text(strip=True) if title_element else 'N/A'
                link = title_element.find('a')['href'] if title_element and title_element.find('a') else 'N/A'
                
                # Extract the image URL
                image_element = article.find('img')
                image_url = image_element['src'] if image_element else 'N/A'
                
                # Extract the summary/content
                summary_element = article.find('div', class_='content-list-excerpt')
                summary = summary_element.get_text(strip=True) if summary_element else 'N/A'
                
                # Extract the published date and category
                entry_meta = article.find('p', class_='entry-meta')
                if entry_meta:
                    date_str = entry_meta.find('span', class_='entry-meta-date').get_text(strip=True)
                    try:
                        published_date = datetime.strptime(date_str, "%B %d, %Y").strftime('%d-%m-%Y')
                    except ValueError:
                        logging.warning(f"Failed to parse date: {date_str}")
                        published_date = 'N/A'
                    category = entry_meta.find('span', class_='entry-meta-cats').get_text(strip=True)
                else:
                    published_date = 'N/A'
                    category = 'N/A'
                
                # Prepare the news item
                news_item = {
                    'id': hashlib.md5(link.encode()).hexdigest(),
                    'title': title,
                    'link': link,
                    'publisher': 'Northern Miner',
                    'published_date': published_date,
                    'category': category,
                    'image_url': image_url,
                    'content': summary,
                }
                news_data.append(news_item)
            return news_data
        else:
            logging.error(f"Failed to retrieve northernminer.com news. Status code: {response.stat}")
            return []
    except Exception as e:
        logging.error(f"Error fetching news from northernminer.com: {str(e)}")
        return []


def scrape_chart_data(driver, chart_selector):
    try:
        chart_data = driver.execute_script(f"""
            const chart = Highcharts.charts.find(c => c.renderTo.id === '{chart_selector.lstrip('#')}');
            if (!chart) return null;
            return chart.series.map(series => ({{
                name: series.name,
                data: series.data.map(point => ({{
                    name: point.name || point.category,
                    y: point.y
                }}))
            }}));
        """)
        return chart_data
    except Exception as e:
        logger.error(f"Error scraping chart {chart_selector}: {e}")
        return []

def scrape_table_data(driver, table_selector):
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, table_selector))
        )
        table = driver.find_element(By.CSS_SELECTOR, table_selector)
        headers = [th.text for th in table.find_elements(By.CSS_SELECTOR, 'thead th')]
        rows = table.find_elements(By.CSS_SELECTOR, 'tbody tr')
        data = []
        for row in rows:
            row_data = {}
            cells = row.find_elements(By.TAG_NAME, 'td')
            for i, cell in enumerate(cells):
                row_data[headers[i]] = cell.text
            data.append(row_data)
        return data
    except Exception as e:
        logger.error(f"Error scraping table {table_selector}: {e}")
        return []


def init_driver():
    chromedriver_autoinstaller.install()

    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled") 

    if server_config:
        options.binary_location = "/usr/bin/chromium"
        service = Service(executable_path="/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)

    return driver


def fetch_uranium_data():
    global global_uranium_data

    if global_uranium_data is None:

        driver = init_driver()

        try:
            uranium_price = fetch_uranium_price(driver)
            print("progress >>>>>>>>>>>>>>>>> 10%")
            calendar_data = fetch_calendar_data(driver)
            print("progress >>>>>>>>>>>>>>>>> 30%")
            iaea_news = fetch_iaea_news(driver)
            print("progress >>>>>>>>>>>>>>>>> 40%")
            nuclear_data = scrape_nuclear_data(driver)
            print("progress >>>>>>>>>>>>>>>>> 50%")
            mining_com_news = fetch_news_from_mining_com(driver)
            print("progress >>>>>>>>>>>>>>>>> 60%")
            nucnet_news = fetch_news_from_nucnet(driver)
            print("progress >>>>>>>>>>>>>>>>> 60%")
            inform_kz_news = fetch_inform_kz_news(driver)
            print("progress >>>>>>>>>>>>>>>>> 70%")
        finally:
            driver.quit()

        uranium_stocks = fetch_uranium_stocks()
        print("progress >>>>>>>>>>>>>>>>> 80%")
        world_nuclear_news_com = fetch_world_nuclear_news_com()
        print("progress >>>>>>>>>>>>>>>>> 90%")
        mining_technology_com_news = fetch_mining_technology_com_news()
        print("progress >>>>>>>>>>>>>>>>> 95%")
        northern_miner_com_news = fetch_news_from_northern_miner_com()
        print("progress >>>>>>>>>>>>>>>>> 100%")
        
        # Fetch stock news synchronously
        all_stock_news = []
        for symbol in URANIUM_STOCKS:
            stock_news = fetch_stock_news(symbol)
            all_stock_news.extend(stock_news)

        # Sort and remove duplicates
        seen_titles = set()
        unique_stock_news = []
        for news in sorted(all_stock_news, key=lambda x: x['published_date'], reverse=True):
            if news['title'] not in seen_titles:
                seen_titles.add(news['title'])
                unique_stock_news.append(news)

        # If we don't have enough unique stock news, fetch more
        while len(unique_stock_news) < 9:
            for symbol in URANIUM_STOCKS:
                additional_news = fetch_stock_news(symbol)
                for news in additional_news:
                    if news['title'] not in seen_titles:
                        seen_titles.add(news['title'])
                        unique_stock_news.append(news)
                        if len(unique_stock_news) >= 9:
                            break
                if len(unique_stock_news) >= 9:
                    break

        global_uranium_data = {
            **uranium_price,
            'stocks': uranium_stocks,
            'mining_com_news': mining_com_news,
            'world_nuclear_news_com': world_nuclear_news_com,
            'calendar': calendar_data,
            'mining_technology_com_news': mining_technology_com_news,
            'inform_kz_news': inform_kz_news,
            'northern_miner_com_news': northern_miner_com_news,
            'nuclear_data': nuclear_data,
            'iaea_news': iaea_news,
            'stock_news': unique_stock_news[:9],
            'nucnet_news': nucnet_news
        }

    return global_uranium_data


# Update the fetch_uranium_data_sync function
def fetch_uranium_data_sync():
    return fetch_uranium_data()


# Initial data fetch
fetch_data_daily()
