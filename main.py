from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from typing import List
import asyncio
import logging
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, select
from pydantic import BaseModel

# Инициализация приложения FastAPI
app = FastAPI()

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            if connection.client_state == WebSocketState.CONNECTED:
                await connection.send_text(message)

    async def send_message(self, message: str):
        await self.broadcast(message)

ws_manager = WebSocketManager()


# Настройки логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Конфигурация базы данных
DATABASE_URL = "postgresql+asyncpg://maxidom-products:0000@localhost:5432/maxidom-products"
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


AVAILABLE_CATEGORIES = [
	"nasosnoe-oborudovanie", "kraski-i-emali", "dreli", "sadovaya-tehnika",
	"zapchasti-dlya-sadovoy-tehniki", "unitazy",
	"mebel-dlya-vannyh-komnat", "oborudovanie-dlya-dusha",
	"smesiteli", "filtry-dlya-vody", "otopitelnoe-oborudovanie", "inzhenernaya-santehnika", "ventilyatsionnoe-oborudovanie", 
    "aksessuary-dlya-vannoy-komnaty", "izmeritelnyy-instrument", "organizatsiya-rabochego-mesta", "otvertki", "klyuchi-golovki", 
    "udarno-rychazhnyy-instrument", "svarochnoe-oborudovanie", "grunty-propitki-olify", "malyarno-shtukaturnyy-instrument", 
    "sredstva-zaschitnye-dlya-dereva", "vyklyuchateli",
	"rozetki-ramki-dlya-rozetok", "vse-dlya-elektromontazha",
	"udliniteli-setevye-filtry-ibp", "stulya",
	"melkaya-tehnika-dlya-kuhni", "posuda-i-pribory-dlya-vypechki"
]
CATEGORY = AVAILABLE_CATEGORIES[0]
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


# WebSocket-эндпоинт
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@app.get("/")
async def root():
    return {"message": "API для парсинга запущен"}

@app.get("/products")
async def get_products():
    async with async_session() as session:
        result = await session.execute(select(Product))
        await ws_manager.send_message(f"Товары найдены.")
        return result.scalars().all()
    
# Маршрут для получения товара по id
@app.get("/products/{product_id}")
async def get_product(product_id: int):
    async with async_session() as session:
        result = await session.execute(select(Product).filter(Product.id == product_id))
        product = result.scalar_one_or_none()
        if product is None:
            await ws_manager.send_message(f"Товар с ID={product_id} не найден.")
            raise HTTPException(status_code=404, detail="Товар не найден")
        await ws_manager.send_message(f"Товар с ID={product_id} найден.")
        return product
    

# Маршрут для редактирования товара по id
@app.put("/products/{product_id}")
async def update_product(product_id: int, product_update: ProductUpdate):
    async with async_session() as session:
        result = await session.execute(select(Product).filter(Product.id == product_id))
        product = result.scalar_one_or_none()
        if product is None:
            raise HTTPException(status_code=404, detail="Товар не найден")

        if product_update.name is not None:
            product.name = product_update.name
        if product_update.price is not None:
            product.price = product_update.price

        await session.commit()
        await ws_manager.send_message(f"Продукт с ID={product_id} обновлен.")
        return {"message": "Продукт обновлен", "product": {"id": product.id, "name": product.name, "price": product.price}}
    

#Маршрут для удаления товара по id
@app.delete("/products/{product_id}")
async def delete_product(product_id: int):
    async with async_session() as session:
        result = await session.execute(select(Product).filter(Product.id == product_id))
        product = result.scalar_one_or_none()
        if product is None:
            raise HTTPException(status_code=404, detail="Товар не найден")
        await session.delete(product)
        await session.commit()
        await ws_manager.send_message(f"Продукт с ID={product_id} удален.")
        return {"detail": "Product deleted"}	
    
# Маршрут для добавления нового товара
@app.post("/products")
async def add_product(product: ProductUpdate):
    async with async_session() as session:
        async with session.begin():
            # Проверяем, существует ли товар с таким же именем
            result = await session.execute(select(Product).filter(Product.name == product.name))
            existing_product = result.scalar_one_or_none()
            if existing_product:
                raise HTTPException(status_code=400, detail="Товар с таким именем уже существует")

            # Создаем новый товар
            new_product = Product(name=product.name, price=product.price)
            session.add(new_product)
            await session.commit()

            # Отправляем сообщение через WebSocket
            await ws_manager.send_message(f"Добавлен новый товар: {new_product.name}")

            return {"message": "Товар добавлен", "product": {"id": new_product.id, "name": new_product.name, "price": new_product.price}}


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(periodic_parsing())