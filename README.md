


# Web Scraper for Product Data

Этот проект представляет собой скрипт для сбора данных о товарах с сайта [Maxidom](https://www.maxidom.ru). Скрипт выполняет парсинг данных о товарах и их ценах из указанной категории и сохраняет их в формате CSV.

## Описание

Скрипт реализует парсинг страниц каталога товаров. На каждой странице скрипт извлекает информацию о названии и цене каждого товара, затем переходит на следующую страницу, если она доступна, и продолжает сбор данных. После завершения сбора данные сохраняются в файл `results.csv`.

### Основные функции

- **fetch_page(url, headers)**: отправляет GET-запрос по указанному URL, обрабатывает ошибки доступа и возвращает HTML-код страницы.
- **parse_product_data(soup)**: извлекает данные о товарах с одной страницы, включая название и цену, и возвращает их в виде списка словарей.
- **get_next_page_url(soup, base_url)**: определяет URL следующей страницы, если она доступна.
- **collect_product_data(start_url, delay=1)**: основной цикл сбора данных по всем страницам в категории. Скрипт переходит на следующую страницу и делает паузу (по умолчанию 1 секунда) для снижения нагрузки на сервер.

## Установка

1. Клонируйте репозиторий.
   ```bash
   git clone <URL вашего репозитория>
   cd <название папки репозитория>
   ```
2. Установите зависимости.
   ```bash
   pip install requests beautifulsoup4 pandas
   ```

## Использование

1. Задайте категорию товаров для парсинга, заменив переменную `category` на нужное значение. Например:
   ```python
   category = "nasosnoe-oborudovanie"
   ```

2. Запустите скрипт:
   ```bash
   python scraper.py
   ```

3. Данные о товарах будут сохранены в файл `results.csv`.

## Пример структуры CSV-файла

Файл `results.csv` содержит две колонки:
- **№** — номер строки,
- **Название** — название товара,
- **Цена** — цена товара.

### Пример данных

| №  | Название          | Цена            |
|----|-------------------|-----------------|
| 1  | Водяной насос 1   | 5 000 руб.      |
| 2  | Насос погружной 2 | 7 500 руб.      |

## Зависимости

- Python 3.x
- `requests` — для отправки HTTP-запросов
- `beautifulsoup4` — для парсинга HTML-кода
- `pandas` — для работы с таблицами и сохранения данных в CSV

