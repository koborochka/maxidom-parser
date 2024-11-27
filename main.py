import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

# Подключение к БД PostgreSQL
DATABASE_URL = "postgresql://maxidom-products:0000@localhost:5432/maxidom-products"
Base = declarative_base()

# Модель таблицы для товаров
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(String)

# Настройка движка и сессии
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создание таблицы, если её ещё нет
Base.metadata.create_all(bind=engine)

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

        product_data.append({'name': name, 'price': price})

    return product_data

# Функция для перехода на следующую страницу
def get_next_page_url(soup, base_url):
    next_page = soup.find('a', id='navigation_2_next_page')
    return base_url + next_page.get('href') if next_page else None

# Функция для записи данных в базу данных
def save_products_to_db(products):
    session = SessionLocal()
    try:
        # Удаление старых данных
        session.query(Product).delete()
        session.commit()

        # Добавление новых данных
        for product_data in products:
            product = Product(name=product_data["name"], price=product_data["price"])
            session.add(product)

        session.commit()
        print(f"Сохранено {len(products)} товаров в базу данных")
    except Exception as e:
        print(f"Ошибка при сохранении данных в БД: {e}")
        session.rollback()
    finally:   
          session.close()

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

# Сохранение данных в БД
save_products_to_db(product_data)
