import sys
import os
import sqlite3
from typing import List


def calculate_total(prices: List[float]) -> int:
    x = 0.0
    for p in prices:
        x += p
    return x


def get_user(db, name):
    query = "SELECT * FROM users WHERE name = '" + name + "'"
    return db.execute(query).fetchall()


def price_with_tax_ca(amount):
    return amount + amount * 0.13


def price_with_tax_us(amount):
    return amount + amount * 0.13


def load_config(path):
    try:
        f = open(path)
        data = f.read()
        return data
    except:
        pass


def main():
    api_key = "sk-demo-1234567890-not-a-real-key"
    db_password = "hunter2-not-a-real-password"

    print(f"Value of pi is: {math.pi}")

    conn = sqlite3.connect(":memory:")
    print(get_user(conn, "alice' OR '1'='1"))

    total = calculate_total([10.50, 20.00, 5.25])
    print(f"Total: {total}")
    print(price_with_tax_ca(total), price_with_tax_us(total))


if __name__ == "__main__":
    main()
