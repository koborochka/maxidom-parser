import requests
from bs4 import BeautifulSoup
import time
import pandas as pd

# Функция для отправки запроса и получения HTML-кода страницы
def fetch_page(url, headers):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Ошибка доступа к {url}: {e}")
        return None


# Функция для извлечения данных о товарах с одной страницы
def parse_product_data(soup):
    product_data = []
    products = soup.find_all('article', class_='l-product')
    for product in products:
        name_tag = product.find('span', itemprop='name')
        name = name_tag.text.strip() if name_tag else 'Название не указано'

        price_tag = product.find('div', class_='l-product__price-base')
        price = price_tag.text.strip().replace('\xa0', ' ') if price_tag else 'Цена не указана'

        product_data.append({'Название': name, 'Цена': price})

    return product_data


# Функция для перехода на следующую страницу
def get_next_page_url(soup, base_url):
    next_page = soup.find('a', id='navigation_2_next_page')
    return base_url + next_page.get('href') if next_page else None


# Основная функция для сбора данных по всем страницам с небольшой задержкой
def collect_product_data(start_url, delay=1):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    base_url = "https://www.maxidom.ru"
    url = start_url
    all_product_data = []

    while url:
        print(f"Сбор данных с {url}...")
        page_html = fetch_page(url, headers)
        if not page_html:
            break

        soup = BeautifulSoup(page_html, 'html.parser')
        product_data = parse_product_data(soup)
        all_product_data.extend(product_data)

        # Переход на следующую страницу
        url = get_next_page_url(soup, base_url)
        if url:
            time.sleep(delay)  # Пауза перед следующим запросом

    return all_product_data


# Заменить на нужную категорию
category = "nasosnoe-oborudovanie"
start_url = f"https://www.maxidom.ru/catalog/{category}/"

# Сбор данных
product_data = collect_product_data(start_url)

# Создание DataFrame для данных
df = pd.DataFrame(product_data)
df.index += 1

# Сохранение данных в CSV файл
df.to_csv('results.csv', index_label='№', encoding='utf-8')
print("Данные сохранены в results.csv")
