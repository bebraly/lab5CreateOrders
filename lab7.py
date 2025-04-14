# -*- coding: utf-8 -*-
import json
import requests
import time

API_KEY = ""
API_BASE = "https://api.ataix.kz/api/orders"
ORDERS_FILE = "orders_data.json"

def load_orders():
    with open(ORDERS_FILE, "r") as file:
        return json.load(file)

def save_orders(orders):
    with open(ORDERS_FILE, "w") as file:
        json.dump(orders, file, indent=4)

def get_order_status(order_id):
    url = f"{API_BASE}/{order_id}"
    headers = {
        "accept": "application/json",
        "X-API-Key": API_KEY
    }
    response = requests.get(url, headers=headers, timeout=20)
    if response.status_code == 200:
        return response.json().get("result", {}).get("status")
    else:
        print(f" Ошибка получения статуса ордера {order_id}: {response.status_code}")
        return None

def cancel_order(order_id):
    url = f"{API_BASE}/{order_id}"
    headers = {
        "accept": "application/json",
        "X-API-Key": API_KEY
    }
    response = requests.delete(url, headers=headers, timeout=20)
    return response.status_code == 200

def create_new_order(symbol, price):
    new_price = round(float(price) * 1.02, 4)
    data = {
        "symbol": symbol,
        "side": "sell",
        "type": "limit",
        "quantity": 1,
        "price": str(new_price)
    }
    headers = {
        "accept": "application/json",
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(API_BASE, headers=headers, json=data, timeout=20)
    if response.status_code == 200:
        return response.json().get("result")
    else:
        print(f"Ошибка при создании нового ордера: {response.status_code}")
        return None

def process_orders():
    orders = load_orders()
    new_orders = []

    for order in orders:
        if order["status"].lower() !="filled":
            continue

        order_id = order["orderID"]
        print(f"Проверка ордера {order_id}...")

        status = get_order_status(order_id)

        if status == "filled":
            print(f"Ордер {order_id} выполнен. Продаю за * 1,02")
            order["status"] = "filled"
            result = create_new_order(order["symbol"], order["price"])
            if result:
                print(f"Создан новый ордер: {result['orderID']} по {result['price']}")
                new_orders.append({
                    "orderID": result["orderID"],
                    "price": result["price"],
                    "quantity": result["quantity"],
                    "symbol": result["symbol"],
                    "status": result["status"],
                    "discount": "2%"
                })
        time.sleep(1)



    orders.extend(new_orders)
    save_orders(orders)
    print("Обработка завершена. Обновления сохранены в orders_data.json")

if __name__ == "__main__":
    process_orders()