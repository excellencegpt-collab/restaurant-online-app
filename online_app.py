import csv
import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


RESTAURANT_NAME = "Foddie Hot & Specie Restaurant"
APP_NAME = f"{RESTAURANT_NAME} Menu Software"
RECEIPT_DIR = "receipts"
DB_FILE = os.environ.get("RESTAURANT_DB_PATH", "restaurant_data.db")
DEFAULT_DISCOUNT_PERCENT = 5
DEFAULT_TAX_PERCENT = 10


@dataclass(frozen=True)
class MenuItem:
    code: str
    category: str
    name: str
    price: int


MENU_ITEMS = [
    MenuItem("F01", "Starters", "French Fries", 250),
    MenuItem("F02", "Starters", "Masala Fries", 300),
    MenuItem("F03", "Starters", "Chicken Nuggets", 450),
    MenuItem("F04", "Starters", "Garlic Mayo Fries", 350),
    MenuItem("F05", "Starters", "Loaded Fries", 550),
    MenuItem("B01", "Burgers", "Zinger Burger", 450),
    MenuItem("B02", "Burgers", "Chicken Burger", 380),
    MenuItem("B03", "Burgers", "Beef Burger", 550),
    MenuItem("B04", "Burgers", "Cheese Burger", 480),
    MenuItem("B05", "Burgers", "Double Patty Burger", 700),
    MenuItem("S01", "Fast Food", "Chicken Shawarma", 280),
    MenuItem("S02", "Fast Food", "Zinger Shawarma", 350),
    MenuItem("S03", "Fast Food", "Club Sandwich", 500),
    MenuItem("S04", "Fast Food", "Chicken Roll Paratha", 300),
    MenuItem("S05", "Fast Food", "Pizza Fries", 650),
    MenuItem("Q01", "BBQ", "Chicken Tikka", 450),
    MenuItem("Q02", "BBQ", "Chicken Malai Boti", 750),
    MenuItem("Q03", "BBQ", "Chicken Seekh Kabab", 600),
    MenuItem("Q04", "BBQ", "Beef Seekh Kabab", 700),
    MenuItem("Q05", "BBQ", "BBQ Platter", 1500),
    MenuItem("P01", "Pizza", "Small Pizza", 650),
    MenuItem("P02", "Pizza", "Medium Pizza", 1150),
    MenuItem("P03", "Pizza", "Large Pizza", 1750),
    MenuItem("P04", "Pizza", "Special Pizza", 2100),
    MenuItem("D01", "Drinks", "Soft Drink", 120),
    MenuItem("D02", "Drinks", "Mineral Water", 100),
    MenuItem("D03", "Drinks", "Fresh Lime", 180),
    MenuItem("D04", "Drinks", "Tea", 100),
    MenuItem("D05", "Drinks", "Coffee", 220),
]


def connect_db():
    return sqlite3.connect(DB_FILE)


def init_database():
    with connect_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_no TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                customer TEXT NOT NULL,
                table_no TEXT NOT NULL,
                subtotal INTEGER NOT NULL,
                discount_percent INTEGER NOT NULL,
                discount_amount INTEGER NOT NULL,
                tax_percent INTEGER NOT NULL,
                tax_amount INTEGER NOT NULL,
                grand_total INTEGER NOT NULL,
                pdf_path TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS order_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                item_code TEXT NOT NULL,
                item_name TEXT NOT NULL,
                category TEXT NOT NULL,
                qty INTEGER NOT NULL,
                price INTEGER NOT NULL,
                line_total INTEGER NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
            )
