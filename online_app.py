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


APP_NAME = "S J Restaurant Menu Software"
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
        Paragraph("S J RESTAURANT", title_style),
        Paragraph("Fresh - Tasty - Quality", center_style),
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
    .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
    [data-testid="stMetricValue"] {font-size: 1.3rem;}
    .receipt-box {border:1px solid #ddd; padding:12px; border-radius:6px; background:#fff;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("S J Restaurant")
st.caption("Online Menu, Billing, PDF Receipt and Sales History")

order_tab, history_tab = st.tabs(["Order", "Sales History"])

with order_tab:
    left, right = st.columns([1.35, 1], gap="large")

    with left:
        st.subheader("Menu")
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

        for menu_item in filtered_items:
            col_item, col_price, col_qty, col_btn = st.columns([3, 1, 1, 1])
            col_item.write(f"**{menu_item.name}**")
            col_item.caption(menu_item.category)
            col_price.write(money(menu_item.price))
            qty = col_qty.number_input(
                "Qty",
                min_value=1,
                max_value=99,
                value=1,
                key=f"qty_{menu_item.code}",
                label_visibility="collapsed",
            )
            if col_btn.button("Add", key=f"add_{menu_item.code}", use_container_width=True):
                st.session_state.order[menu_item.code] = st.session_state.order.get(menu_item.code, 0) + int(qty)
                st.session_state.last_receipt = None
                st.session_state.last_pdf = None
                st.rerun()

    with right:
        st.subheader("Current Order")
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
