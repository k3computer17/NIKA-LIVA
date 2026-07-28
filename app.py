import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import urllib.parse
import hashlib

# Page Configuration
st.set_page_config(page_title="NIKA - Multi-Service & Tax Portal", layout="wide")

# Custom Styling
st.markdown("""
    <style>
    .main { 
        background: linear-gradient(135deg, #fff8f5 0%, #fff3ed 50%, #fce4ec 100%); 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
    }
    h1, h2, h3 { color: #d84315 !important; font-weight: 700; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #ffe0b2; }
    .stButton>button {
        background: linear-gradient(90deg, #f4511e 0%, #d32f2f 100%);
        color: white; border-radius: 8px; border: none; padding: 10px 24px; font-weight: bold;
        box-shadow: 0 4px 10px rgba(244, 81, 30, 0.25); transition: 0.3s;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #e64a19 0%, #c62828 100%);
        box-shadow: 0 6px 14px rgba(244, 81, 30, 0.35);
    }
    .stLinkButton>a {
        background: linear-gradient(90deg, #f4511e 0%, #d32f2f 100%) !important;
        color: white !important; border-radius: 8px !important; font-weight: bold !important;
    }
    input, textarea, select { border-color: #ffccbc !important; background-color: #ffffff !important; border-radius: 6px !important; }
    .stAlert { background-color: #fff3e0 !important; border: 1px solid #ffccbc !important; color: #bf360c !important; border-radius: 8px; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #ffffff; border-radius: 6px 6px 0px 0px; padding: 10px 16px; color: #4e342e; border: 1px solid #ffe0b2; }
    .stTabs [aria-selected="true"] { background-color: #fbe9e7 !important; color: #d84315 !important; border-bottom: 2px solid #d84315 !important; }
    </style>
""", unsafe_allow_html=True)

# Password Utilities
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# Database Setup
DB_FILE = 'nika_clients_v3.db'

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT,
                        role TEXT,
                        client_id INTEGER,
                        is_approved INTEGER DEFAULT 1)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS clients (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        unique_client_id TEXT,
                        name TEXT,
                        father_name TEXT,
                        pan_number TEXT,
                        mobile TEXT,
                        address TEXT,
                        itr_username TEXT,
                        itr_password TEXT,
                        created_date TEXT,
                        latitude TEXT,
                        longitude TEXT)''')

        c.execute('''CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category_name TEXT UNIQUE)''')

        c.execute('''CREATE TABLE IF NOT EXISTS services (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT,
                        service_name TEXT,
                        unit TEXT DEFAULT 'Pc',
                        price_rate REAL,
                        description TEXT,
                        is_active INTEGER DEFAULT 1)''')

        c.execute('''CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id INTEGER,
                        items_summary TEXT,
                        total_price REAL,
                        order_date TEXT,
                        delivery_address TEXT,
                        order_status TEXT DEFAULT 'Pending',
                        remarks TEXT,
                        FOREIGN KEY(client_id) REFERENCES clients(id))''')

        c.execute('''CREATE TABLE IF NOT EXISTS admin_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        setting_key TEXT UNIQUE,
                        setting_value TEXT)''')

        # Default Categories
        default_categories = ["किराना (Grocery)", "कपड़ा प्रेस / ड्राई क्लीन", "टैक्स व अकाउंटिंग"]
        for cat in default_categories:
            c.execute("INSERT OR IGNORE INTO categories (category_name) VALUES (?)", (cat,))

        # Migrations
        for table, col, col_type in [
            ("services", "unit", "TEXT DEFAULT 'Pc'"),
            ("orders", "order_status", "TEXT DEFAULT 'Pending'"),
            ("orders", "delivery_address", "TEXT"),
            ("users", "is_approved", "INTEGER DEFAULT 1"),
            ("clients", "unique_client_id", "TEXT"),
            ("clients", "latitude", "TEXT"),
            ("clients", "longitude", "TEXT")
        ]:
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass

        # Create Default Admin
        c.execute("SELECT id FROM users WHERE username = 'admin'")
        if not c.fetchone():
            c.execute("INSERT INTO users (username, password, role, is_approved) VALUES (?, ?, ?, ?)",
                      ('admin', make_hashes('admin123'), 'Admin', 1))
        conn.commit()

init_db()

# Helper Functions
MY_CONTACT = "8358013017"

def generate_auto_client_id():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT MAX(id) FROM clients")
        res = c.fetchone()
        last_id = res[0] if res and res[0] is not None else 0
        return f"NIKA-{last_id + 1001}"

def create_whatsapp_link(client_mobile, message):
    if not client_mobile:
        return None
    clean_mobile = "".join(filter(str.isdigit, str(client_mobile)))
    if len(clean_mobile) == 10:
        clean_mobile = "91" + clean_mobile
    encoded_msg = urllib.parse.quote(message)
    return f"https://api.whatsapp.com/send?phone={clean_mobile}&text={encoded_msg}"

def get_setting(key):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT setting_value FROM admin_settings WHERE setting_key = ?", (key,))
        res = c.fetchone()
        return res[0] if res else ""

def get_categories():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT category_name FROM categories ORDER BY category_name ASC")
        return [r[0] for r in c.fetchall()]

# Session State Initialization
for key in ["logged_in", "username", "user_role", "client_id", "cart"]:
    if key not in st.session_state:
        st.session_state[key] = False if key == "logged_in" else ([] if key == "cart" else None)

# Branding Header
app_logo = get_setting("logo_url")
app_banner = get_setting("banner_url")
global_tax_info = get_setting("tax_info")

if app_banner:
    st.image(app_banner, use_container_width=True)

if app_logo:
    col_l1, col_l2 = st.columns([1, 6])
    with col_l1:
        st.image(app_logo, width=90)
    with col_l2:
        st.title("🏢 NIKA - Multi-Service & Tax Portal")
else:
    st.title("🏢 NIKA - Multi-Service & Tax Portal")

if global_tax_info:
    st.markdown(f"""
        <div style="background-color: #fbe9e7; padding: 12px; border-radius: 8px; border-left: 5px solid #d84315; margin-bottom: 15px;">
            <strong style="color: #d84315;">📢 Tax & Portal Notice:</strong> {global_tax_info}
        </div>
    """, unsafe_allow_html=True)

# Authentication Flow
if not st.session_state.logged_in:
    login_choice = st.sidebar.selectbox("📌 Navigation", ["🔐 Admin Login", "👤 Customer Login", "📝 New Registration", "🔄 Reset Password"])

    if login_choice == "🔐 Admin Login":
        st.subheader("👨‍💼 Master Admin Login")
        user = st.text_input("👤 Admin Username")
        passwd = st.text_input("🔑 Admin Password", type="password")
        if st.button("🚀 Master Login"):
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT password FROM users WHERE username = ? AND role = 'Admin'", (user,))
                res = c.fetchone()
                if res and check_hashes(passwd, res[0]):
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    st.session_state.user_role = "Admin"
                    st.success("Welcome Admin!")
                    st.rerun()
                else:
                    st.error("Invalid Admin Credentials")

    elif login_choice == "👤 Customer Login":
        st.subheader("👤 Customer Portal Login")
        user = st.text_input("🆔 User ID / Username")
        passwd = st.text_input("🔑 Password", type="password")
        if st.button("🚀 Customer Login"):
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT password, client_id, is_approved FROM users WHERE username = ? AND role = 'Customer'", (user,))
                res = c.fetchone()
                if res:
                    if res[2] == 0:
                        st.warning("⚠️ आपका अकाउंट अभी एडमिन द्वारा अप्रूव नहीं किया गया है।")
                        w_msg = f"नमस्ते एडमिन, मैंने नया रजिस्ट्रेशन किया है। कृपया मेरा यूजर आईडी ({user}) अप्रूव कर दें।"
                        st.link_button("💬 Send Approval Request on WhatsApp", create_whatsapp_link(MY_CONTACT, w_msg))
                    elif check_hashes(passwd, res[0]):
                        st.session_state.logged_in = True
                        st.session_state.username = user
                        st.session_state.user_role = "Customer"
                        st.session_state.client_id = res[1]
                        st.success("Login Successful!")
                        st.rerun()
                    else:
                        st.error("Invalid Password")
                else:
                    st.error("User ID not found!")

    elif login_choice == "📝 New Registration":
        st.subheader("📝 Self Register as New Customer")
        auto_id = generate_auto_client_id()
        
        col1, col2 = st.columns(2)
        with col1:
            c_name = st.text_input("👤 Full Name *")
            c_father = st.text_input("👨‍👦 Father's Name")
            c_mobile = st.text_input("📱 Mobile Number *")
            c_address = st.text_area("🏠 Delivery / Home Address *")
        with col2:
            c_unique = st.text_input("🆔 Unique Client ID (Auto) *", value=auto_id)
            c_userid = st.text_input("🧑‍💻 Create User ID *")
            c_pass = st.text_input("🔑 Create Password *", type="password")

        st.markdown("---")
        st.subheader("📍 लोकेशन विवरण")
        lat_input = st.text_input("🌐 Latitude (अक्षांश)", value="23.2599")
        lon_input = st.text_input("🌐 Longitude (देशांतर)", value="77.4126")

        if st.button("✨ Register & Send Approval Request"):
            if not all([c_name, c_userid, c_pass, c_mobile, c_address, c_unique]):
                st.error("कृपया सभी आवश्यक (*) फ़ील्ड भरें!")
            else:
                try:
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        today = datetime.now().strftime("%Y-%m-%d")
                        c.execute("""
                            INSERT INTO clients (unique_client_id, name, father_name, mobile, address, created_date, latitude, longitude) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (c_unique.upper(), c_name, c_father, c_mobile, c_address, today, lat_input, lon_input))
                        
                        new_client_id = c.lastrowid
                        c.execute("INSERT INTO users (username, password, role, client_id, is_approved) VALUES (?, ?, 'Customer', ?, 0)",
                                  (c_userid, make_hashes(c_pass), new_client_id))
                        conn.commit()
                        st.success(f"✅ रजिस्ट्रेशन सफल हुआ! आपकी यूनिक आईडी है: **{c_unique.upper()}**")
                        
                        wa_text = f"नमस्ते एडमिन, मैंने नया रजिस्ट्रेशन किया है।\n\nनाम: {c_name}\nयूजर आईडी: {c_userid}\nयूनिक आईडी: {c_unique.upper()}\nलोकेशन: https://maps.google.com/?q={lat_input},{lon_input}\n\nकृपया मेरा अकाउंट अप्रूव करें।"
                        st.link_button("💬 Send Approval WhatsApp to Admin", create_whatsapp_link(MY_CONTACT, wa_text))
                except sqlite3.IntegrityError:
                    st.error("⚠️ यह Username पहले से मौजूद है। कृपया दूसरा चुनें।")

    elif login_choice == "🔄 Reset Password":
        st.subheader("🔄 Reset Your Password")
        f_user = st.text_input("🆔 Enter Your User ID / Username")
        f_mobile = st.text_input("📱 Enter Registered Mobile Number")
        f_unique = st.text_input("🏷️ Enter Unique Client ID")
        new_pass = st.text_input("🔑 Enter New Password", type="password")

        if st.button("🔄 Reset Password"):
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT u.id, c.mobile, c.unique_client_id 
                    FROM users u 
                    JOIN clients c ON u.client_id = c.id 
                    WHERE u.username = ? AND u.role = 'Customer'
                ''', (f_user,))
                r = c.fetchone()
                if r and r[1] == f_mobile and str(r[2]).upper() == f_unique.upper():
                    c.execute("UPDATE users SET password = ? WHERE username = ?", (make_hashes(new_pass), f_user))
                    conn.commit()
                    st.success("✅ पासवर्ड सफलतापूर्वक बदल दिया गया है!")
                else:
                    st.error("❌ विवरण (Details) मेल नहीं खा रहे हैं।")

# Dashboard View
else:
    st.sidebar.write(f"👤 **{st.session_state.username}** ({st.session_state.user_role})")
    
    if st.sidebar.button("🔴 Logout"):
        st.session_state.clear()
        st.rerun()

    # ==================== ADMIN DASHBOARD ====================
    if st.session_state.user_role == "Admin":
        st.title("👨‍💼 Master Admin Control Center")
        choice = st.sidebar.radio("📌 Admin Menu", [
            "⚙️ Manage Customers", "👥 Approve New Users", "🛍️ Manage Categories & Services",
            "📦 Customer Orders", "🖼️ Portal Branding & Tax Settings (Admin Only)", "📊 Business Report"
        ])

        if choice == "⚙️ Manage Customers":
            st.subheader("⚙️ कस्टमर आईडी और डेटा अपडेट या डिलीट करें")
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT id, name, unique_client_id, mobile FROM clients ORDER BY id DESC")
                all_clients = c.fetchall()
                
                if not all_clients:
                    st.info("कोई कस्टमर डेटा उपलब्ध नहीं है।")
                else:
                    c_dict = {f"[{r[2] if r[2] else 'NO ID'}] {r[1]} - Mob: {r[3]}": r[0] for r in all_clients}
                    sel_label = st.selectbox("🔍 कस्टमर चुनें:", list(c_dict.keys()))
                    sel_cid = c_dict[sel_label]

                    c.execute("SELECT unique_client_id, name, father_name, pan_number, mobile, address, latitude, longitude FROM clients WHERE id = ?", (sel_cid,))
                    c_data = c.fetchone()

                    tab_update, tab_delete = st.tabs(["✏️ अपडेट करें", "🗑️ डिलीट करें"])
                    with tab_update:
                        up_unique = st.text_input("🆔 Unique Client ID", value=c_data[0] if c_data[0] else "")
                        up_name = st.text_input("👤 Full Name", value=c_data[1] if c_data[1] else "")
                        up_mobile = st.text_input("📱 Mobile Number", value=c_data[4] if c_data[4] else "")
                        up_address = st.text_area("🏠 Address", value=c_data[5] if c_data[5] else "")
                        
                        if c_data[6] and c_data[7]:
                            st.markdown(f"📍 **लोकेशन लिंक:** [Google Maps देखें](https://maps.google.com/?q={c_data[6]},{c_data[7]})")
                        
                        if st.button("💾 अपडेट सहेजें"):
                            c.execute("UPDATE clients SET unique_client_id = ?, name = ?, mobile = ?, address = ? WHERE id = ?",
                                      (up_unique.upper(), up_name, up_mobile, up_address, sel_cid))
                            conn.commit()
                            st.success("✅ अपडेट सफल रहा!")
                            st.rerun()

                    with tab_delete:
                        if st.button("🗑️ डिलीट करें"):
                            c.execute("DELETE FROM clients WHERE id = ?", (sel_cid,))
                            c.execute("DELETE FROM users WHERE client_id = ?", (sel_cid,))
                            conn.commit()
                            st.success("🗑️ डिलीट कर दिया गया!")
                            st.rerun()

        elif choice == "👥 Approve New Users":
            st.subheader("👥 Pending Customer Approvals")
            with get_db_connection() as conn:
                df_pend = pd.read_sql_query('''
                    SELECT u.id as 'User Table ID', c.unique_client_id as 'Unique ID', c.name as 'Name', u.username as 'Username', c.mobile as 'Mobile'
                    FROM users u JOIN clients c ON u.client_id = c.id
                    WHERE u.role = 'Customer' AND u.is_approved = 0
                ''', conn)
                if not df_pend.empty:
                    st.dataframe(df_pend, use_container_width=True)
                    app_uid = st.number_input("🆔 Enter User Table ID to Approve:", min_value=1, step=1)
                    if st.button("✅ Approve Customer"):
                        c = conn.cursor()
                        c.execute("UPDATE users SET is_approved = 1 WHERE id = ?", (app_uid,))
                        conn.commit()
                        st.success("Approved!")
                        st.rerun()
                else:
                    st.info("No pending approvals.")

        elif choice == "🛍️ Manage Categories & Services":
            st.subheader("🛍️ कैटेगेरी एवं सर्विस/आइटम प्रबंधन")
            
            tab_add_cat, tab_add_item, tab_view_items = st.tabs(["📂 Category जोड़ें", "➕ नया Item/Service जोड़ें", "📋 Items एवं Services लिस्ट"])
            
            categories_list = get_categories()

            with tab_add_cat:
                st.write("### 📂 नई Category दर्ज करें")
                new_cat_input = st.text_input("कैटेगरी का नाम दर्ज करें (जैसे: इलेक्ट्रॉनिक, किराना, कंसल्टेंसी):")
                if st.button("➕ Category सहेजें"):
                    if new_cat_input.strip():
                        try:
                            with get_db_connection() as conn:
                                c = conn.cursor()
                                c.execute("INSERT INTO categories (category_name) VALUES (?)", (new_cat_input.strip(),))
                                conn.commit()
                                st.success(f"✅ Category '{new_cat_input.strip()}' सफलतापूर्वक जोड़ी गई!")
                                st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("⚠️ यह Category पहले से मौजूद है!")
                    else:
                        st.error("कृपया Category का सही नाम लिखें!")

            with tab_add_item:
                st.write("### ➕ Item / Service रेट और इकाई (Unit) के साथ जोड़ें")
                if not categories_list:
                    st.warning("पहले कोई Category जोड़ें!")
                else:
                    with st.form("service_form"):
                        s_cat = st.selectbox("📂 Category चुनें:", categories_list)
                        s_name = st.text_input("🏷️ Service / Item का नाम")
                        col_u, col_p = st.columns(2)
                        with col_u:
                            s_unit = st.selectbox("📏 इकाई (Unit) चुनें:", ["Pc / Piece", "Kg", "Gram", "Ltr", "Packet", "Meter", "Hour", "Visit", "Job"])
                        with col_p:
                            s_price = st.number_input("💵 दर / Rate (₹):", min_value=0.0, step=10.0)
                        
                        if st.form_submit_button("💾 Item/Service जोड़े"):
                            if s_name.strip():
                                with get_db_connection() as conn:
                                    c = conn.cursor()
                                    c.execute("INSERT INTO services (category, service_name, unit, price_rate) VALUES (?, ?, ?, ?)", 
                                              (s_cat, s_name.strip(), s_unit, s_price))
                                    conn.commit()
                                    st.success(f"✅ Item '{s_name.strip()}' ({s_unit}) सफलतापूर्वक Category '{s_cat}' में जोड़ा गया!")
                                    st.rerun()
                            else:
                                st.error("कृपया Item का नाम लिखें!")

            with tab_view_items:
                st.write("### 📋 सभी Items एवं Categories देखें")
                filter_cat = st.selectbox("🔍 Category के अनुसार फ़िल्टर करें:", ["सभी Categories"] + categories_list)
                
                with get_db_connection() as conn:
                    if filter_cat == "सभी Categories":
                        df_serv = pd.read_sql_query("SELECT id as ID, category as Category, service_name as 'Item Name', unit as 'Unit (इकाई)', price_rate as 'Rate (₹)' FROM services WHERE is_active = 1 ORDER BY category ASC", conn)
                    else:
                        df_serv = pd.read_sql_query("SELECT id as ID, category as Category, service_name as 'Item Name', unit as 'Unit (इकाई)', price_rate as 'Rate (₹)' FROM services WHERE is_active = 1 AND category = ? ORDER BY service_name ASC", conn, params=(filter_cat,))
                    
                    st.dataframe(df_serv, use_container_width=True)

        elif choice == "📦 Customer Orders":
            st.subheader("📦 Customer Orders Management")
            with get_db_connection() as conn:
                df_orders = pd.read_sql_query('''
                    SELECT o.id as 'Order ID', COALESCE(c.unique_client_id, 'N/A') as 'Unique ID', COALESCE(c.name, 'N/A') as 'Customer Name',
                           o.items_summary as 'Items Summary', o.total_price as 'Total (₹)', o.order_date as 'Date', o.order_status as 'Status'
                    FROM orders o LEFT JOIN clients c ON o.client_id = c.id ORDER BY o.id DESC
                ''', conn)
                if not df_orders.empty:
                    st.dataframe(df_orders, use_container_width=True)
                    ord_id = st.number_input("🆔 Order ID to Update Status:", min_value=1, step=1)
                    new_status = st.selectbox("🔄 Status:", ["Pending", "Processing", "Out for Delivery", "Completed", "Cancelled"])
                    if st.button("✨ Update Status"):
                        c = conn.cursor()
                        c.execute("UPDATE orders SET order_status = ? WHERE id = ?", (new_status, ord_id))
                        conn.commit()
                        st.success("Status Updated!")
                        st.rerun()
                else:
                    st.info("No orders found.")

        elif choice == "🖼️ Portal Branding & Tax Settings (Admin Only)":
            st.subheader("🖼️ होल्डिंग बैनर, लोगो और टैक्स विवरण सेट करें")
            curr_banner = get_setting("banner_url")
            curr_logo = get_setting("logo_url")
            curr_tax = get_setting("tax_info")

            with st.form("branding_form"):
                b_url = st.text_input("🖼️ होल्डिंग बैनर इमेज लिंक (Banner Image URL):", value=curr_banner)
                l_url = st.text_input("🟢 लोगो इमेज लिंक (Logo Image URL):", value=curr_logo)
                t_info = st.text_area("📊 टैक्स / बिलिंग विवरण (Tax Info):", value=curr_tax)
                
                if st.form_submit_button("💾 सेटिंग्स सहेजें"):
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        for k, val in [("banner_url", b_url), ("logo_url", l_url), ("tax_info", t_info)]:
                            c.execute("INSERT OR REPLACE INTO admin_settings (setting_key, setting_value) VALUES (?, ?)", (k, val))
                        conn.commit()
                        st.success("✅ सेटिंग्स सहेज ली गई हैं!")
                        st.rerun()

        elif choice == "📊 Business Report":
            st.subheader("📊 Business Overview Report")
            with get_db_connection() as conn:
                df = pd.read_sql_query("SELECT unique_client_id as 'Unique ID', name, mobile, address FROM clients", conn)
                st.dataframe(df, use_container_width=True)

    # ==================== CUSTOMER DASHBOARD ====================
    elif st.session_state.user_role == "Customer":
        st.title("👤 Customer Service Portal & Cart")
        cid = st.session_state.client_id

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT unique_client_id, name, mobile, address FROM clients WHERE id = ?", (cid,))
            client_info = c.fetchone()
            
        c_uid = client_info[0] if client_info and client_info[0] else "N/A"
        c_name = client_info[1] if client_info and client_info[1] else "Customer"
        c_mob = client_info[2] if client_info and client_info[2] else "N/A"
        c_addr = client_info[3] if client_info and client_info[3] else ""

        st.info(f"👤 **{c_name}** | 🆔 **ID:** `{c_uid}`")

        tab_order, tab_cart, tab_my_orders = st.tabs(["🛒 Browse & Add", "🛍️ My Cart", "📦 My Orders"])

        with tab_order:
            st.subheader("🛍️ Category से Item चुनें")
            
            categories_list = get_categories()
            if not categories_list:
                st.warning("अभी कोई Category उपलब्ध नहीं है।")
            else:
                selected_cat = st.selectbox("📂 1. Category चुनें:", categories_list)

                with get_db_connection() as conn:
                    c = conn.cursor()
                    c.execute("SELECT id, service_name, unit, price_rate FROM services WHERE is_active = 1 AND category = ?", (selected_cat,))
                    cat_items = c.fetchall()

                if not cat_items:
                    st.info(f"⚠️ Category '{selected_cat}' में कोई Item/Service उपलब्ध नहीं है।")
                else:
                    item_dict = {f"{item[1]} (इकाई: {item[2] if item[2] else 'Pc'}, दर: ₹{item[3]})": item for item in cat_items}
                    
                    st.markdown("---")
                    selected_item_label = st.selectbox(f"🏷️ 2. Item / Service चुनें:", list(item_dict.keys()))
                    chosen_item = item_dict[selected_item_label]
                    
                    item_unit = chosen_item[2] if chosen_item[2] else "Pc"

                    c_qty, c_unit, c_rate = st.columns(3)
                    with c_qty:
                        qty = st.number_input("🔢 मात्रा (Quantity):", min_value=1, value=1, step=1)
                    with c_unit:
                        st.text_input("📏 इकाई (Unit):", value=item_unit, disabled=True)
                    with c_rate:
                        rate = st.number_input("💵 दर / Rate (₹):", value=float(chosen_item[3]), step=1.0)
                    
                    if st.button("➕ कार्ट में जोड़ें"):
                        item_total = qty * rate
                        st.session_state.cart.append({
                            "id": chosen_item[0], 
                            "category": selected_cat, 
                            "name": chosen_item[1], 
                            "unit": item_unit,
                            "qty": qty,
                            "rate": rate, 
                            "total": item_total
                        })
                        st.success(f"✅ '{chosen_item[1]}' कार्ट में जुड़ गया!")

        with tab_cart:
            st.subheader("🛍️ आपकी कार्ट (Cart Details)")
            if st.session_state.cart:
                df_cart = pd.DataFrame(st.session_state.cart)
                
                # Separate columns clearly
                df_cart_display = df_cart[['category', 'name', 'unit', 'qty', 'rate', 'total']]
                df_cart_display.columns = ['Category', 'Item Name (सामग्री का नाम)', 'Unit (इकाई)', 'Quantity (मात्रा)', 'Rate (₹)', 'Total Amount (₹)']
                
                st.dataframe(df_cart_display, use_container_width=True)
                
                grand_total = df_cart['total'].sum()
                st.markdown(f"### 💵 कुल योग (Grand Total): **₹{grand_total:,.2f}**")
                
                del_addr = st.text_area("🏠 डिलिवरी पता:", value=c_addr)
                if st.button("🚀 आर्डर फाइनल करें"):
                    # Structured clear summary text
                    summary_lines = []
                    for i in st.session_state.cart:
                        summary_lines.append(f"• {i['name']} | Qty: {i['qty']} {i['unit']} | Rate: ₹{i['rate']} | Total: ₹{i['total']}")
                    
                    summary_str = "\n".join(summary_lines)
                    today_dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        c.execute('''
                            INSERT INTO orders (client_id, items_summary, total_price, order_date, delivery_address)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (cid, summary_str, grand_total, today_dt, del_addr))
                        conn.commit()
                    
                    st.success("🎉 ऑर्डर दर्ज हो गया!")
                    bill_msg = f"🧾 *NIKA STORE BILL* 🧾\n👤 *Customer:* {c_name} ({c_uid})\n📅 *Date:* {today_dt}\n\n*ITEMS DETAILS:*\n{summary_str}\n\n💰 *Grand Total: ₹{grand_total:,.2f}*\n🏠 *Address:* {del_addr}"
                    st.link_button("💬 व्हाट्सएप पर बिल भेजें", create_whatsapp_link(MY_CONTACT, bill_msg), use_container_width=True)
                    st.session_state.cart = []
            else:
                st.info("🛒 कार्ट खाली है।")

        with tab_my_orders:
            st.subheader("📦 मेरे ऑर्डर्स")
            with get_db_connection() as conn:
                df_my = pd.read_sql_query("SELECT id as 'Order ID', items_summary as 'Order Items (Item | Qty & Unit | Rate)', total_price as 'Total (₹)', order_date as 'Date', order_status as 'Status' FROM orders WHERE client_id = ? ORDER BY id DESC", conn, params=(cid,))
                if not df_my.empty:
                    st.dataframe(df_my, use_container_width=True)
                else:
                    st.info("कोई आर्डर नहीं मिला।")
