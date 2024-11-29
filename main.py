from fastapi import FastAPI, HTTPException
import asyncio
import logging
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, select, text
from pydantic import BaseModel

# Инициализация приложения FastAPI
app = FastAPI()

# Настройки логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация базы данных
DATABASE_URL = "postgresql+asyncpg://maxidom-products:0000@localhost:5432/maxidom-products"

Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

CATEGORY = "nasosnoe-oborudovanie"
INTERVAL = 10

class ProductUpdate(BaseModel):
    name: str = None
    price: str = None

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(String)

async def fetch_product_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    product_data = []
    async with aiohttp.ClientSession() as session:
        while url:
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка при парсинге: {response.status}")
                        break
                    html_content = await response.text()
                    # Используем BeautifulSoup для парсинга
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html_content, "html.parser")
                    products = soup.find_all("article", class_="l-product__horizontal")
                    for product in products:
                        name = product.find("span", itemprop="name").text.strip()
                        price = product.find("div", class_="l-product__price-base").text.strip()
                        product_data.append({"name": name, "price": price})
                    next_page = soup.find("a", id="navigation_2_next_page")
                    url = "https://www.maxidom.ru" + next_page["href"] if next_page else None
            except Exception as e:
                logger.error(f"Ошибка: {str(e)}")
                break
    return product_data

async def save_products_to_db(products):
    async with async_session() as session:
        async with session.begin():
            for product_data in products:
                result = await session.execute(
                    select(Product).filter(Product.name == product_data["name"])
                )
                product = result.scalar_one_or_none()
                if product:
                    product.price = product_data["price"]  # Обновляем цену
                else:
                    new_product = Product(name=product_data["name"], price=product_data["price"])
                    session.add(new_product)

async def periodic_parsing():
    start_url = f"https://www.maxidom.ru/catalog/{CATEGORY}/"
    while True:
        logger.info("Парсинг начался...")
        products = await fetch_product_data(start_url)
        await save_products_to_db(products)
        await asyncio.sleep(INTERVAL)

@app.get("/")
async def root():
    return {"message": "API для парсинга запущен"}

@app.get("/products")
async def get_products():
    async with async_session() as session:
        result = await session.execute(select(Product))
        return result.scalars().all()
    
# Маршрут для получения товара по id
@app.get("/products/{product_id}")
async def get_product(product_id: int):
    async with async_session() as session:
        result = await session.execute(select(Product).filter(Product.id == product_id))
        product = result.scalar_one_or_none()
        if product is None:
            raise HTTPException(status_code=404, detail="Товар не найден")
        return product
# Маршрут для редактирования товара по id
@app.put("/products/{product_id}")
async def update_product(product_id: int, product_update: ProductUpdate):
    async with async_session() as session:
        result = await session.execute(select(Product).filter(Product.id == product_id))
        product = result.scalar_one_or_none()
        if product is None:
            raise HTTPException(status_code=404, detail="Товар не найден")

        # Обновляем только те поля, которые переданы в запросе
        if product_update.name is not None:
            product.name = product_update.name
        if product_update.price is not None:
            product.price = product_update.price

        await session.commit()
        return {"message": "Продукт обновлен", "product": {"id": product.id, "name": product.name, "price": product.price}}
# Маршрут для удаления товара по id
@app.delete("/products/{product_id}")
async def delete_product(product_id: int):
    async with async_session() as session:
        result = await session.execute(select(Product).filter(Product.id == product_id))
        product = result.scalar_one_or_none()
        if product is None:
            raise HTTPException(status_code=404, detail="Товар не найден")
        await session.delete(product)
        await session.commit()
        return {"detail": "Product deleted"}	

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(periodic_parsing())
