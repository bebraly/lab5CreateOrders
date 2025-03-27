# -*- coding: utf-8 -*-
import json
import re
import requests
import sys
import os
from typing import Dict, List, Union, Optional

API_KEY = ""
BASE_URL = "https://api.ataix.kz"

def make_api_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Union[Dict, str]: #для отправки запросов
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "accept": "application/json",
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=20)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=20)
        else:
            return f"Ошибка: неподдерживаемый метод {method}"

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        return f"Ошибка запроса: {str(e)}"

def extract_unique_currencies(data: str, target_word: str) -> set: # получение валют
    """Извлекает уникальные валюты из текста"""
    words = re.findall(r'\b\w+\b', data)
    return {re.sub(r'[^a-zA-Zа-яА-Я]', '', words[i + 1])
            for i in range(len(words) - 1) if words[i] == target_word}

def display_balances() -> None: #получка баланса
    """Отображает балансы всех доступных валют"""
    print("Доступный баланс на бирже в токенах USDT")
    symbols_data = make_api_request("GET", "/api/symbols")
    if isinstance(symbols_data, str):
        print(symbols_data)
        return

    currencies = extract_unique_currencies(json.dumps(symbols_data), "base")

    for currency in currencies:
        balance_info = make_api_request("GET", f"/api/user/balances/{currency}")
        if isinstance(balance_info, dict):
            try:
                available = balance_info.get('result').get('available')
                print(f"{currency}\t\t{available}")
            except AttributeError as e:
                print(f"Не нашел валюту {currency}")

def find_symbols_with_price_threshold(threshold: float = 0.6) -> Dict[str, str]: #пары
    symbols_data = make_api_request("GET", "/api/symbols")
    prices_data = make_api_request("GET", "/api/prices")

    if isinstance(symbols_data, str) or isinstance(prices_data, str):
        print("Ошибка получения данных:", symbols_data or prices_data)
        return {}

    symbols = re.findall(r'"symbol"\s*:\s*"(\w+/\w+)"', json.dumps(symbols_data))
    prices = re.findall(r'"lastTrade"\s*:\s*"([\d.]+)"', json.dumps(prices_data))

    result = {}
    print("\n\nТорговая пара с USDT где минимальная цена меньше или равно 0.6 USDT:")

    for symbol, price in zip(symbols, prices):
        if "USDT" in symbol and float(price) <= threshold:
            print(f"{symbol}\t{price}")
            result[symbol] = price

    return result

def create_orders(symbol: str, base_price: float) -> List[Dict]: #order
    price_levels = {
        '2%': round(base_price * 0.98, 4),
        '5%': round(base_price * 0.95, 4),
        '8%': round(base_price * 0.92, 4)
    }

    orders = []
    for level, price in price_levels.items():
        order_data = {
            "symbol": symbol,
            "side": "buy",
            "type": "limit",
            "quantity": 1,
            "price": str(price)
        }

        response = make_api_request("POST", "/api/orders", order_data)
        if isinstance(response, dict):
            orders.append({
                "orderID": response.get("result", {}).get("orderID", "N/A"),
                "price": price,
                "quantity": 1,
                "symbol": symbol,
                "status": response.get("result", {}).get("status", "NEW"),
                "discount": level
            })

    return orders

def save_orders_to_file(orders: List[Dict], filename: str = "orders_data.json") -> None: #save order
    existing_orders = []
    if os.path.exists(filename):
        try:
            with open(filename, "r") as file:
                existing_orders = json.load(file)
        except (json.JSONDecodeError, IOError):
            existing_orders = []

    existing_orders.extend(orders)

    try:
        with open(filename, "w") as file:
            json.dump(existing_orders, file, indent=4)
        print(f"[+] Данные успешно сохранены в {filename}")
    except IOError as e:
        print(f"Ошибка сохранения файла: {str(e)}")

def main():
    display_balances()
    available_pairs = find_symbols_with_price_threshold()

    if not available_pairs:
        print("Нет доступных торговых пар, удовлетворяющих условиям")
        return

    while True:
        user_input = input("Выберите торговую пару (название) или 'N' --> ").upper()

        if user_input == "N":
            sys.exit()

        selected_pair = f"{user_input}/USDT"
        if selected_pair in available_pairs:
            base_price = float(available_pairs[selected_pair])
            print(f"\nВыбрана пара: {selected_pair}\tТекущая цена: {base_price}")

            price_2pc = round(base_price * 0.98, 4)
            price_5pc = round(base_price * 0.95, 4)
            price_8pc = round(base_price * 0.92, 4)

            print(f"""
Будет создано три ордера на покупку:
- На 2% ниже: {price_2pc}
- На 5% ниже: {price_5pc}
- На 8% ниже: {price_8pc}
""")

            confirmation = input("Для подтверждения введите 'Y', для отмены 'N' --> ")
            if confirmation.lower() == 'y':
                orders = create_orders(selected_pair, base_price)
                if orders:
                    save_orders_to_file(orders)
                    print("[+] Ордера успешно созданы. Для проверки посетите сайт ATAIX, вкладка 'Мои ордера'")
                break
            elif confirmation.lower() == 'n':
                sys.exit()
        else:
            print("Неверный выбор. Доступные пары:", ", ".join(pair.split('/')[0] for pair in available_pairs))

if __name__ == "__main__":
    main()