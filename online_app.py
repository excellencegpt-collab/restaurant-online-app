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
RESTAURANT_PHONE = "+92 347 6821871"
WHATSAPP_NUMBER = "923476821871"
RESTAURANT_ADDRESS = "Clifton, Karachi"
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


HERO_IMAGE_URL = "https://images.unsplash.com/photo-1514933651103-005eec06c04b?auto=format&fit=crop&w=1600&q=80"

CATEGORY_IMAGES = {
    "Starters": "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?auto=format&fit=crop&w=900&q=80",
    "Burgers": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=900&q=80",
    "Fast Food": "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?auto=format&fit=crop&w=900&q=80",
    "BBQ": "https://images.unsplash.com/photo-1529193591184-b1d58069ecdd?auto=format&fit=crop&w=900&q=80",
    "Pizza": "https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=900&q=80",
    "Drinks": "https://images.unsplash.com/photo-1544145945-f90425340c7e?auto=format&fit=crop&w=900&q=80",
}


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
            """
        )


def find_item(code):
    for item in MENU_ITEMS:
        if item.code == code:
            return item
    raise KeyError(code)


def make_receipt_no():
    return datetime.now().strftime("R%Y%m%d%H%M%S")


def order_summary(order, discount_percent, tax_percent):
    subtotal = sum(find_item(code).price * qty for code, qty in order.items())
    discount_amount = round(subtotal * discount_percent / 100)
    taxable = max(0, subtotal - discount_amount)
    tax_amount = round(taxable * tax_percent / 100)
    grand_total = taxable + tax_amount
    return subtotal, discount_amount, tax_amount, grand_total


def create_slip_pdf(order, customer, table_no, discount_percent, tax_percent, receipt_no):
    subtotal, discount_amount, tax_amount, grand_total = order_summary(order, discount_percent, tax_percent)
    now = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    page_width = 80 * mm
    page_height = max(160 * mm, (118 + (len(order) * 9)) * mm)
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=(page_width, page_height),
        rightMargin=4 * mm,
        leftMargin=4 * mm,
        topMargin=5 * mm,
        bottomMargin=5 * mm,
        title="Restaurant Receipt",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=16,
        textColor=colors.black,
        alignment=1,
        spaceAfter=1,
    )
    center_style = ParagraphStyle("SlipCenter", parent=styles["Normal"], fontName="Helvetica", fontSize=7, leading=9, alignment=1)
    small_style = ParagraphStyle("SlipSmall", parent=styles["Normal"], fontName="Helvetica", fontSize=7, leading=9)
    item_style = ParagraphStyle("SlipItem", parent=styles["Normal"], fontName="Helvetica", fontSize=7, leading=8)
    bold_style = ParagraphStyle("SlipBold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10)
    total_style = ParagraphStyle("SlipTotal", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=12)
    separator = "-" * 42

    story = [
        Paragraph(RESTAURANT_NAME.upper(), title_style),
        Paragraph("Fresh - Tasty - Quality", center_style),
        Paragraph(f"{RESTAURANT_PHONE} | {RESTAURANT_ADDRESS}", center_style),
        Paragraph("Computerized Sales Receipt", center_style),
        Paragraph(separator, center_style),
    ]

    info_table = Table(
        [
            ["Receipt No", receipt_no],
            ["Date", now],
            ["Customer", customer or "Walk-in"],
            ["Table", table_no or "-"],
        ],
        colWidths=[22 * mm, 50 * mm],
    )
    info_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    story.extend([info_table, Paragraph(separator, center_style)])

    item_rows = [[Paragraph("Item", bold_style), "Qty", "Rate", "Amount"]]
    for code, qty in order.items():
        item = find_item(code)
        item_rows.append([Paragraph(item.name, item_style), str(qty), str(item.price), str(item.price * qty)])

    items_table = Table(item_rows, colWidths=[34 * mm, 8 * mm, 14 * mm, 16 * mm], repeatRows=1)
    items_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("ALIGN", (1, 0), (-1, 0), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.black),
                ("LINEBELOW", (0, -1), (-1, -1), 0.4, colors.black),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.extend([items_table, Spacer(1, 2 * mm)])

    totals_table = Table(
        [
            [Paragraph("Subtotal", small_style), f"Rs. {subtotal}"],
            [Paragraph(f"Discount {discount_percent}%", small_style), f"Rs. {discount_amount}"],
            [Paragraph(f"Tax {tax_percent}%", small_style), f"Rs. {tax_amount}"],
            [Paragraph("Net Payable", total_style), f"Rs. {grand_total}"],
        ],
        colWidths=[42 * mm, 30 * mm],
    )
    totals_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (1, -1), (1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -2), 7),
                ("FONTSIZE", (1, -1), (1, -1), 10),
                ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.black),
                ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.black),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.extend(
        [
            totals_table,
            Paragraph(separator, center_style),
            Paragraph("Thank you for visiting!", center_style),
            Paragraph("Software generated receipt", center_style),
        ]
    )
    doc.build(story)
    return buffer.getvalue()


def save_order(order, customer, table_no, discount_percent, tax_percent, receipt_no, pdf_path=""):
    subtotal, discount_amount, tax_amount, grand_total = order_summary(order, discount_percent, tax_percent)
    with connect_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO orders (
                receipt_no, created_at, customer, table_no, subtotal,
                discount_percent, discount_amount, tax_percent, tax_amount,
                grand_total, pdf_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt_no,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                customer or "Walk-in",
                table_no or "-",
                subtotal,
                discount_percent,
                discount_amount,
                tax_percent,
                tax_amount,
                grand_total,
                pdf_path,
            ),
        )
        order_id = cursor.lastrowid
        for code, qty in order.items():
            item = find_item(code)
            conn.execute(
                """
                INSERT INTO order_lines (order_id, item_code, item_name, category, qty, price, line_total)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (order_id, item.code, item.name, item.category, qty, item.price, item.price * qty),
            )
    return order_id


def get_orders(from_day, to_day, query):
    params = [f"{from_day} 00:00:00", f"{to_day} 23:59:59"]
    sql = """
        SELECT id, receipt_no, created_at, customer, table_no, grand_total
        FROM orders
        WHERE created_at BETWEEN ? AND ?
    """
    if query:
        sql += " AND (customer LIKE ? OR receipt_no LIKE ? OR table_no LIKE ?)"
        like = f"%{query}%"
        params.extend([like, like, like])
    sql += " ORDER BY created_at DESC"
    with connect_db() as conn:
        return conn.execute(sql, params).fetchall()


def get_order_detail(order_id):
    with connect_db() as conn:
        order = conn.execute(
            """
            SELECT receipt_no, created_at, customer, table_no, subtotal,
                   discount_percent, discount_amount, tax_percent, tax_amount, grand_total
            FROM orders WHERE id = ?
            """,
            (order_id,),
        ).fetchone()
        lines = conn.execute(
            "SELECT item_name, qty, price, line_total FROM order_lines WHERE order_id = ?",
            (order_id,),
        ).fetchall()
    return order, lines


def reset_order():
    st.session_state.order = {}
    st.session_state.customer = ""
    st.session_state.table_no = ""
    st.session_state.discount_percent = DEFAULT_DISCOUNT_PERCENT
    st.session_state.tax_percent = DEFAULT_TAX_PERCENT
    st.session_state.last_receipt = None
    st.session_state.last_pdf = None


def ensure_state():
    if "order" not in st.session_state:
        reset_order()


def money(value):
    return f"Rs. {value:,}"


st.set_page_config(page_title=APP_NAME, layout="wide")
init_database()
ensure_state()

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(239, 68, 68, 0.18), transparent 28rem),
            linear-gradient(180deg, #070707 0%, #111111 52%, #090909 100%);
        color: #f8fafc;
    }
    .block-container {padding-top: 3.8rem; padding-bottom: 2rem; max-width: 1480px;}
    h1, h2, h3, h4, h5, h6, p, label, span {color: #f8fafc;}
    [data-testid="stMetricValue"] {font-size: 1.3rem;}
    [data-testid="stTabs"] button {color: #f8fafc;}
    [data-testid="stTabs"] button[aria-selected="true"] {color: #ff2a2a;}
    [data-testid="stHorizontalBlock"] {align-items: stretch;}
    .stSelectbox div[data-baseweb="select"],
    .stTextInput input,
    .stNumberInput input {
        background: #1c1c1c !important;
        border-color: #333333 !important;
        color: #ffffff !important;
    }
    .stAlert {
        background: #171717 !important;
        border: 1px solid #2b2b2b !important;
        color: #f8fafc !important;
    }
    .stDataFrame {
        border: 1px solid #2b2b2b;
        border-radius: 8px;
        overflow: hidden;
    }
    .stButton > button,
    .stDownloadButton > button {
        background: #ef1717 !important;
        color: #ffffff !important;
        border: 0 !important;
        border-radius: 999px !important;
        font-weight: 800 !important;
        min-height: 42px;
        box-shadow: 0 8px 18px rgba(239, 23, 23, 0.22);
    }
    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background: #ff2a2a !important;
        color: #ffffff !important;
    }
    .topbar {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        align-items: center;
        margin-bottom: 18px;
        flex-wrap: wrap;
    }
    .top-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #ef1717;
        color: white;
        padding: 12px 16px;
        border-radius: 7px;
        font-weight: 800;
        line-height: 1.1;
        box-shadow: 0 8px 20px rgba(239, 23, 23, 0.22);
        margin: 0 8px 8px 0;
    }
    .top-pill small {
        display: block;
        color: #ffe1e1;
        font-size: 11px;
        font-weight: 600;
    }
    .brand-chip {
        background: #171717;
        color: #ffffff;
        border: 1px solid #2b2b2b;
        border-radius: 999px;
        padding: 10px 18px;
        font-weight: 900;
        letter-spacing: 0.2px;
        margin-bottom: 8px;
    }
    .hero-wrap {
        position: relative;
        min-height: 310px;
        border-radius: 12px;
        overflow: hidden;
        margin: 0.4rem 0 1.4rem 0;
        background-size: cover;
        background-position: center;
        border: 1px solid #2b2b2b;
        box-shadow: 0 18px 46px rgba(0,0,0,0.42);
    }
    .hero-overlay {
        position: absolute;
        inset: 0;
        background: linear-gradient(90deg, rgba(0,0,0,0.86), rgba(0,0,0,0.32));
        display: flex;
        align-items: center;
        padding: 28px;
    }
    .hero-title {
        color: white;
        font-size: 44px;
        font-weight: 800;
        line-height: 1.08;
        margin-bottom: 8px;
        max-width: 800px;
    }
    .hero-subtitle {
        color: #ffdf8c;
        font-size: 15px;
        max-width: 520px;
    }
    .hero-note {
        color: #ffffff;
        margin-top: 18px;
        font-weight: 700;
    }
    .food-card {
        position: relative;
        border: 1px solid #2c2c2c;
        border-radius: 12px;
        overflow: hidden;
        background: #181818;
        margin-bottom: 10px;
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.24);
    }
    .food-img {
        width: 100% !important;
        height: 220px;
        background-size: cover;
        background-position: center;
        display: block;
    }
    .food-body {
        padding: 14px 16px 12px 16px;
    }
    .food-name {
        font-weight: 700;
        font-size: 18px;
        color: #ffffff;
    }
    .food-meta {
        color: #b8b8b8;
        font-size: 12px;
        margin-top: 4px;
    }
    .food-price {
        display: inline-block;
        color: #ffffff;
        background: #0f3f9b;
        border-radius: 999px;
        padding: 5px 10px;
        font-weight: 800;
        font-size: 14px;
        margin-top: 12px;
    }
    .discount-badge {
        position: absolute;
        right: 0;
        top: 0;
        background: #ffd400;
        color: #050505;
        font-size: 12px;
        font-weight: 900;
        padding: 7px 12px;
        border-bottom-left-radius: 10px;
    }
    .order-panel {
        background: #171717;
        border: 1px solid #2b2b2b;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 12px 28px rgba(0,0,0,0.22);
    }
    .whatsapp-float {
        position: fixed;
        right: 22px;
        bottom: 22px;
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 10px;
        background: #25d366;
        color: #07130b !important;
        padding: 12px 16px;
        border-radius: 999px;
        font-weight: 900;
        text-decoration: none !important;
        box-shadow: 0 14px 30px rgba(37, 211, 102, 0.32);
        border: 2px solid rgba(255,255,255,0.2);
    }
    .whatsapp-float:hover {
        background: #30e578;
        color: #07130b !important;
        text-decoration: none !important;
    }
    .whatsapp-icon {
        display: inline-flex;
        width: 26px;
        height: 26px;
        align-items: center;
        justify-content: center;
        border-radius: 999px;
        background: #ffffff;
        color: #25d366;
        font-size: 18px;
        font-weight: 900;
    }
    @media (max-width: 700px) {
        .whatsapp-float {
            right: 14px;
            bottom: 14px;
            padding: 11px 13px;
            font-size: 13px;
        }
    }
    .section-title {
        color: #ffffff;
        font-size: 28px;
        font-weight: 900;
        margin-bottom: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="topbar">
      <div>
        <span class="top-pill">Phone<br><small>{RESTAURANT_PHONE}</small></span>
        <span class="top-pill">Address<br><small>{RESTAURANT_ADDRESS}</small></span>
      </div>
      <div class="brand-chip">{RESTAURANT_NAME}</div>
    </div>
    <div class="hero-wrap" style="background-image:url('{HERO_IMAGE_URL}')">
      <div class="hero-overlay">
        <div>
          <div class="hero-title">{RESTAURANT_NAME}</div>
          <div class="hero-subtitle">Online Menu, Billing, PDF Receipt and Sales History</div>
          <div class="hero-note">Fast food, BBQ, pizza, burgers and fresh drinks in Clifton.</div>
        </div>
      </div>
    </div>
    <a class="whatsapp-float" href="https://wa.me/{WHATSAPP_NUMBER}?text=Assalam%20o%20Alaikum%2C%20mujhe%20order%20ke%20baray%20mein%20maloomat%20chahiye" target="_blank">
      <span class="whatsapp-icon">W</span>
      WhatsApp
    </a>
    """,
    unsafe_allow_html=True,
)

order_tab, history_tab = st.tabs(["Order", "Sales History"])

with order_tab:
    left, right = st.columns([1.35, 1], gap="large")

    with left:
        st.markdown('<div class="section-title">Menu</div>', unsafe_allow_html=True)
        filter_cols = st.columns([1, 1])
        categories = ["All"] + sorted({item.category for item in MENU_ITEMS})
        category = filter_cols[0].selectbox("Category", categories)
        search = filter_cols[1].text_input("Search item")

        filtered_items = []
        for menu_item in MENU_ITEMS:
            if category != "All" and menu_item.category != category:
                continue
            if search and search.lower() not in menu_item.name.lower() and search.lower() not in menu_item.code.lower():
                continue
            filtered_items.append(menu_item)

        for index in range(0, len(filtered_items), 2):
            row_items = filtered_items[index : index + 2]
            card_cols = st.columns(2)
            for card_col, menu_item in zip(card_cols, row_items):
                with card_col:
                    image_url = CATEGORY_IMAGES.get(menu_item.category, HERO_IMAGE_URL)
                    st.markdown(
                        f"""
                        <div class="food-card">
                          <div class="discount-badge">{DEFAULT_DISCOUNT_PERCENT}% OFF</div>
                          <div class="food-img" style="background-image:url('{image_url}')"></div>
                          <div class="food-body">
                            <div class="food-name">{menu_item.name}</div>
                            <div class="food-meta">{menu_item.category}</div>
                            <div class="food-price">{money(menu_item.price)}</div>
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    action_cols = st.columns([1, 1])
                    qty = action_cols[0].number_input(
                        "Qty",
                        min_value=1,
                        max_value=99,
                        value=1,
                        key=f"qty_{menu_item.code}",
                        label_visibility="collapsed",
                    )
                    if action_cols[1].button("Add", key=f"add_{menu_item.code}", use_container_width=True):
                        st.session_state.order[menu_item.code] = st.session_state.order.get(menu_item.code, 0) + int(qty)
                        st.session_state.last_receipt = None
                        st.session_state.last_pdf = None
                        st.rerun()

    with right:
        st.markdown('<div class="order-panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Current Order</div>', unsafe_allow_html=True)
        info_cols = st.columns(2)
        st.session_state.customer = info_cols[0].text_input("Customer", value=st.session_state.customer)
        st.session_state.table_no = info_cols[1].text_input("Table", value=st.session_state.table_no)

        calc_cols = st.columns(2)
        st.session_state.discount_percent = calc_cols[0].number_input(
            "Discount %",
            min_value=0,
            max_value=100,
            value=int(st.session_state.discount_percent),
        )
        st.session_state.tax_percent = calc_cols[1].number_input(
            "Tax %",
            min_value=0,
            max_value=100,
            value=int(st.session_state.tax_percent),
        )

        if st.session_state.order:
            rows = []
            for code, qty in st.session_state.order.items():
                item = find_item(code)
                rows.append(
                    {
                        "Item": item.name,
                        "Qty": qty,
                        "Rate": money(item.price),
                        "Amount": money(item.price * qty),
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)

            edit_cols = st.columns(3)
            selected_code = edit_cols[0].selectbox(
                "Edit item",
                list(st.session_state.order.keys()),
                format_func=lambda code: find_item(code).name,
            )
            if edit_cols[1].button("+ Qty", use_container_width=True):
                st.session_state.order[selected_code] += 1
                st.rerun()
            if edit_cols[2].button("Remove", use_container_width=True):
                st.session_state.order.pop(selected_code, None)
                st.rerun()

            subtotal, discount_amount, tax_amount, grand_total = order_summary(
                st.session_state.order,
                int(st.session_state.discount_percent),
                int(st.session_state.tax_percent),
            )
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Subtotal", money(subtotal))
            m2.metric("Discount", money(discount_amount))
            m3.metric("Tax", money(tax_amount))
            m4.metric("Net Payable", money(grand_total))

            action_cols = st.columns(3)
            if action_cols[0].button("Save Bill", type="primary", use_container_width=True):
                receipt_no = make_receipt_no()
                pdf_bytes = create_slip_pdf(
                    st.session_state.order,
                    st.session_state.customer,
                    st.session_state.table_no,
                    int(st.session_state.discount_percent),
                    int(st.session_state.tax_percent),
                    receipt_no,
                )
                os.makedirs(RECEIPT_DIR, exist_ok=True)
                pdf_path = os.path.join(RECEIPT_DIR, f"{receipt_no}.pdf")
                with open(pdf_path, "wb") as file:
                    file.write(pdf_bytes)
                save_order(
                    st.session_state.order,
                    st.session_state.customer,
                    st.session_state.table_no,
                    int(st.session_state.discount_percent),
                    int(st.session_state.tax_percent),
                    receipt_no,
                    pdf_path,
                )
                st.session_state.last_receipt = receipt_no
                st.session_state.last_pdf = pdf_bytes
                st.success(f"Bill saved: {receipt_no}")

            if action_cols[1].button("New Order", use_container_width=True):
                reset_order()
                st.rerun()

            if st.session_state.last_pdf:
                st.download_button(
                    "Download / Print PDF Receipt",
                    data=st.session_state.last_pdf,
                    file_name=f"{st.session_state.last_receipt}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        else:
            st.info("Menu se item add karein. Order yahan show hoga.")
        st.markdown('</div>', unsafe_allow_html=True)

with history_tab:
    st.subheader("Sales History")
    filters = st.columns([1, 1, 2])
    from_day = filters[0].date_input("From", value=date.today() - timedelta(days=150))
    to_day = filters[1].date_input("To", value=date.today())
    query = filters[2].text_input("Search customer, table, or receipt")

    orders = get_orders(from_day, to_day, query.strip())
    total_sales = sum(row[5] for row in orders)
    c1, c2 = st.columns(2)
    c1.metric("Total Orders", len(orders))
    c2.metric("Total Sales", money(total_sales))

    if orders:
        display_rows = [
            {
                "ID": row[0],
                "Receipt": row[1],
                "Date": row[2],
                "Customer": row[3],
                "Table": row[4],
                "Grand Total": money(row[5]),
            }
            for row in orders
        ]
        st.dataframe(display_rows, use_container_width=True, hide_index=True)

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Receipt", "Date", "Customer", "Table", "Grand Total"])
        for row in orders:
            writer.writerow(row)
        st.download_button(
            "Download Sales CSV",
            data=output.getvalue(),
            file_name=f"sales_history_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

        selected_order = st.selectbox(
            "View order detail",
            [row[0] for row in orders],
            format_func=lambda order_id: next(row[1] for row in orders if row[0] == order_id),
        )
        order, lines = get_order_detail(selected_order)
        if order:
            st.markdown("#### Receipt Detail")
            detail_rows = [
                {"Item": line[0], "Qty": line[1], "Rate": money(line[2]), "Amount": money(line[3])}
                for line in lines
            ]
            st.write(f"Receipt: **{order[0]}** | Date: **{order[1]}** | Customer: **{order[2]}** | Table: **{order[3]}**")
            st.dataframe(detail_rows, use_container_width=True, hide_index=True)
            st.write(
                f"Subtotal: **{money(order[4])}** | Discount {order[5]}%: **{money(order[6])}** | "
                f"Tax {order[7]}%: **{money(order[8])}** | Net Payable: **{money(order[9])}**"
            )
    else:
        st.info("Is date range mein koi saved bill nahi mila.")
