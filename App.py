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
    .main { background-color: #f4f6f9; font-family: 'Segoe UI', sans-serif; }
    h1, h2, h3 { color: #1a237e !important; }
    .stButton>button {
        background: linear-gradient(90deg, #1e88e5 0%, #1565c0 100%);
        color: white; border-radius: 8px; border: none; padding: 10px 24px; font-weight: bold;
    }
    .bill-box { background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #ddd; }
    </style>
""", unsafe_allow_html=True)

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# Database Connection
conn = sqlite3.connect('nika_clients_v2.db', check_same_thread=False)
c = conn.cursor()

# ----------------- DATABASE TABLES SETUP & MIGRATION -----------------
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        client_id INTEGER,
        is_approved INTEGER DEFAULT 1
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unique_client_id TEXT,
        name TEXT,
        father_name TEXT,
        pan_number TEXT,
        mobile TEXT,
        address TEXT,
        itr_username TEXT,
        itr_password TEXT,
        created_date TEXT
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS client_gst (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        gst_number TEXT,
        gst_username TEXT,
        gst_password TEXT,
        trade_name TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS client_years (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        financial_year TEXT,
        annual_fee REAL DEFAULT 0,
        return_type TEXT,
        income_tax_status TEXT,
        gst_status TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        financial_year TEXT,
        payment_date TEXT,
        amount_paid REAL,
        payment_mode TEXT,
        remarks TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        service_name TEXT,
        price_rate REAL,
        description TEXT,
        is_active INTEGER DEFAULT 1
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        items_summary TEXT,
        total_price REAL,
        order_date TEXT,
        delivery_address TEXT,
        order_status TEXT DEFAULT 'Pending',
        remarks TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )
''')

# Check & Add missing columns safely for old databases
try:
    c.execute("ALTER TABLE clients ADD COLUMN unique_client_id TEXT")
except sqlite3.OperationalError:
    pass 

try:
    c.execute("ALTER TABLE users ADD COLUMN is_approved INTEGER DEFAULT 1")
except sqlite3.OperationalError:
    pass

try:
    c.execute("ALTER TABLE orders ADD COLUMN order_status TEXT DEFAULT 'Pending'")
except sqlite3.OperationalError:
    pass

try:
    c.execute("ALTER TABLE orders ADD COLUMN delivery_address TEXT")
except sqlite3.OperationalError:
    pass

try:
    c.execute("ALTER TABLE orders ADD COLUMN remarks TEXT")
except sqlite3.OperationalError:
    pass

# Create Default Admin User if not exists
c.execute("SELECT * FROM users WHERE username = 'admin'")
if not c.fetchone():
    c.execute("INSERT INTO users (username, password, role, is_approved) VALUES (?, ?, ?, ?)", 
              ('admin', make_hashes('admin123'), 'Admin', 1))
conn.commit()

# ----------------- AUTO GENERATE CLIENT ID FUNCTION -----------------
def generate_auto_client_id():
    c.execute("SELECT MAX(id) FROM clients")
    last_id = c.fetchone()[0]
    next_id = (last_id if last_id else 0) + 1001
    return f"NIKA-{next_id}"

FY_LIST = ["2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025", "2025-2026", "2026-2027"]
MY_CONTACT = "8358013017"

def create_whatsapp_link(client_mobile, message):
    if not client_mobile:
        return None
    clean_mobile = "".join(filter(str.isdigit, str(client_mobile)))
    if len(clean_mobile) == 10:
        clean_mobile = "91" + clean_mobile
    encoded_msg = urllib.parse.quote(message)
    return f"https://api.whatsapp.com/send?phone={clean_mobile}&text={encoded_msg}"

# Session State Initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_role" not in st.session_state:
    st.session_state.user_role = ""
if "client_id" not in st.session_state:
    st.session_state.client_id = None
if "cart" not in st.session_state:
    st.session_state.cart = []

# ================= LOGIN, SIGNUP & FORGOT PORTAL =================
if not st.session_state.logged_in:
    st.title("🏢 NIKA Multi-Service & Tax Portal")
    login_menu = ["🔐 Admin Login", "👤 Customer Login", "📝 New Customer Self-Registration", "🔄 Forgot Password / Reset"]
    login_choice = st.sidebar.selectbox("Navigation", login_menu)

    # 1. ADMIN LOGIN
    if login_choice == "🔐 Admin Login":
        st.subheader("👨‍💼 Master Admin Login")
        user = st.text_input("Admin Username")
        passwd = st.text_input("Admin Password", type="password")
        if st.button("Master Login"):
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

    # 2. CUSTOMER LOGIN
    elif login_choice == "👤 Customer Login":
        st.subheader("👤 Customer Portal Login")
        user = st.text_input("User ID / Username")
        passwd = st.text_input("Password", type="password")
        if st.button("Customer Login"):
            c.execute("SELECT password, client_id, is_approved FROM users WHERE username = ? AND role = 'Customer'", (user,))
            res = c.fetchone()
            if res:
                if res[2] == 0:
                    st.warning("⚠️ आपका अकाउंट अभी एडमिन द्वारा अप्रूव नहीं किया गया है। कृपया व्हाट्सएप पर एडमिन से संपर्क करें।")
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

    # 3. NEW CUSTOMER SELF-REGISTRATION
    elif login_choice == "📝 New Customer Self-Registration":
        st.subheader("📝 Self Register as New Customer")
        
        auto_id = generate_auto_client_id()
        
        col1, col2 = st.columns(2)
        with col1:
            c_name = st.text_input("Full Name *")
            c_father = st.text_input("Father's Name")
            c_mobile = st.text_input("Mobile Number *")
            c_address = st.text_area("Delivery / Home Address *")
        with col2:
            c_unique = st.text_input("Unique Client ID (Auto-Generated) *", value=auto_id)
            c_userid = st.text_input("Create User ID / Username *")
            c_pass = st.text_input("Create Password *", type="password")

        if st.button("Register & Send Approval Request"):
            if not c_name or not c_userid or not c_pass or not c_mobile or not c_address or not c_unique:
                st.error("कृपया सभी आवश्यक (*) फ़ील्ड भरें!")
            else:
                try:
                    today = datetime.now().strftime("%Y-%m-%d")
                    c.execute("INSERT INTO clients (unique_client_id, name, father_name, mobile, address, created_date) VALUES (?, ?, ?, ?, ?, ?)",
                              (c_unique.upper(), c_name, c_father, c_mobile, c_address, today))
                    new_client_id = c.lastrowid
                    
                    c.execute("INSERT INTO users (username, password, role, client_id, is_approved) VALUES (?, ?, 'Customer', ?, 0)",
                              (c_userid, make_hashes(c_pass), new_client_id))
                    conn.commit()
                    st.success(f"✅ रजिस्ट्रेशन सफल हुआ! आपकी यूनिक आईडी है: **{c_unique.upper()}**")
                    
                    wa_text = f"नमस्ते एडमिन, मैंने नया रजिस्ट्रेशन किया है।\n\nनाम: {c_name}\nयूजर आईडी: {c_userid}\nयूनिक आईडी: {c_unique.upper()}\nमोबाइल: {c_mobile}\n\nकृपया मेरा अकाउंट अप्रूव करें।"
                    st.link_button("💬 Send Approval SMS/WhatsApp to Admin", create_whatsapp_link(MY_CONTACT, wa_text))
                except sqlite3.IntegrityError:
                    st.error("⚠️ यह Username पहले से मौजूद है। कृपया दूसरा चुनें।")

    # 4. FORGOT PASSWORD
    elif login_choice == "🔄 Forgot Password / Reset":
        st.subheader("🔄 Reset Your Password")
        f_user = st.text_input("Enter Your User ID / Username")
        f_mobile = st.text_input("Enter Registered Mobile Number")
        f_unique = st.text_input("Enter Unique Client ID")
        new_pass = st.text_input("Enter New Password", type="password")

        if st.button("Reset Password"):
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
                st.success("✅ पासवर्ड सफलतापूर्वक बदल दिया गया है! अब आप 'Customer Login' से लॉगिन कर सकते हैं।")
            else:
                st.error("❌ विवरण (Details) मेल नहीं खा रहे हैं। कृपया सही जानकारी दर्ज करें।")

# ================= LOGGED IN DASHBOARD =================
else:
    st.sidebar.write(f"Logged in as: **{st.session_state.username}** ({st.session_state.user_role})")
    if st.sidebar.button("🔴 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.user_role = ""
        st.session_state.client_id = None
        st.session_state.cart = []
        st.rerun()

    # --------------- ADMIN MENU ---------------
    if st.session_state.user_role == "Admin":
        st.title("👨‍💼 Master Admin Control Center")
        menu = [
            "⚙️ Manage Customers (Update / Delete)",
            "👥 Approve New Customers",
            "🛍️ Manage Services & Rates",
            "📦 View & Manage Customer Orders",
            "➕ Add New Client Profile", 
            "🔍 Client Ledger & Credentials", 
            "📊 Overall Business Report"
        ]
        choice = st.sidebar.radio("Admin Menu", menu)

        # 0. MANAGE CUSTOMERS (UPDATE / DELETE)
        if choice == "⚙️ Manage Customers (Update / Delete)":
            st.subheader("⚙️ कस्टमर आईडी और डेटा अपडेट या डिलीट करें")
            
            c.execute("SELECT id, name, unique_client_id, mobile FROM clients ORDER BY id DESC")
            all_clients = c.fetchall()
            
            if not all_clients:
                st.info("कोई कस्टमर डेटा उपलब्ध नहीं है।")
            else:
                c_dict = {f"[{r[2] if r[2] else 'NO ID'}] {r[1]} - Mob: {r[3]} (Db ID: {r[0]})": r[0] for r in all_clients}
                selected_label = st.selectbox("कस्टमर चुनें जिन्हें अपडेट या डिलीट करना है:", list(c_dict.keys()))
                sel_cid = c_dict[selected_label]

                # Fetch Client Data
                c.execute("SELECT unique_client_id, name, father_name, pan_number, mobile, address FROM clients WHERE id = ?", (sel_cid,))
                c_data = c.fetchone()

                # Fetch Associated User Account
                c.execute("SELECT username FROM users WHERE client_id = ?", (sel_cid,))
                u_data = c.fetchone()
                current_username = u_data[0] if u_data else "No User Account"

                st.markdown("---")
                tab_update, tab_delete = st.tabs(["✏️ अपडेट करें (Update Profile)", "🗑️ डिलीट करें (Delete Customer)"])

                with tab_update:
                    st.write("### ✏️ कस्टमर प्रोफाइल और आईडी अपडेट करें")
                    col1, col2 = st.columns(2)
                    with col1:
                        up_unique = st.text_input("Unique Client ID", value=c_data[0] if c_data[0] else generate_auto_client_id())
                        up_name = st.text_input("Full Name", value=c_data[1] if c_data[1] else "")
                        up_father = st.text_input("Father Name", value=c_data[2] if c_data[2] else "")
                    with col2:
                        up_mobile = st.text_input("Mobile Number", value=c_data[4] if c_data[4] else "")
                        up_pan = st.text_input("PAN Number", value=c_data[3] if c_data[3] else "")
                        up_address = st.text_area("Address", value=c_data[5] if c_data[5] else "")

                    st.markdown("#### 🔑 यूजरनेम / पासवर्ड अपडेट (यदि बदलना हो)")
                    col3, col4 = st.columns(2)
                    with col3:
                        up_uname = st.text_input("User ID / Username", value=current_username)
                    with col4:
                        up_pass = st.text_input("New Password (खाली छोड़ें अगर नहीं बदलना)", type="password")

                    if st.button("💾 अपडेट सहेजें (Save Changes)"):
                        c.execute('''
                            UPDATE clients 
                            SET unique_client_id = ?, name = ?, father_name = ?, pan_number = ?, mobile = ?, address = ?
                            WHERE id = ?
                        ''', (up_unique.upper(), up_name, up_father, up_pan.upper(), up_mobile, up_address, sel_cid))
                        
                        if current_username != "No User Account":
                            if up_pass.strip():
                                c.execute("UPDATE users SET username = ?, password = ? WHERE client_id = ?",
                                          (up_uname, make_hashes(up_pass), sel_cid))
                            else:
                                c.execute("UPDATE users SET username = ? WHERE client_id = ?",
                                          (up_uname, sel_cid))
                        
                        conn.commit()
                        st.success("✅ कस्टमर की डिटेल्स और आईडी सफलतापूर्वक अपडेट कर दी गई हैं!")
                        st.rerun()

                with tab_delete:
                    st.warning("⚠️ **सावधान!** डिलीट करने पर इस ग्राहक का संपूर्ण डेटा (ऑर्डर, लेजर, अकाउंट) हमेशा के लिए हट जाएगा।")
                    confirm_del = st.checkbox(f"हाँ, मैं ग्राहक '{c_data[1]}' को हमेशा के लिए डिलीट करना चाहता/चाहती हूँ।")
                    if st.button("🗑️ Permanently Delete Customer"):
                        if confirm_del:
                            c.execute("DELETE FROM orders WHERE client_id = ?", (sel_cid,))
                            c.execute("DELETE FROM payments WHERE client_id = ?", (sel_cid,))
                            c.execute("DELETE FROM client_years WHERE client_id = ?", (sel_cid,))
                            c.execute("DELETE FROM client_gst WHERE client_id = ?", (sel_cid,))
                            c.execute("DELETE FROM users WHERE client_id = ?", (sel_cid,))
                            c.execute("DELETE FROM clients WHERE id = ?", (sel_cid,))
                            conn.commit()
                            st.success("🗑️ कस्टमर को सफलता पूर्वक डिलीट कर दिया गया है!")
                            st.rerun()
                        else:
                            st.error("कृपया पुष्टि (Checkbox) पर टिक करें!")

        # 1. Approve Customers
        elif choice == "👥 Approve New Customers":
            st.subheader("👥 Pending Customer Approvals")
            df_pend = pd.read_sql_query('''
                SELECT u.id as 'User Table ID', c.unique_client_id as 'Unique ID', c.name as 'Name', u.username as 'Username', c.mobile as 'Mobile', c.address as 'Address'
                FROM users u
                JOIN clients c ON u.client_id = c.id
                WHERE u.role = 'Customer' AND u.is_approved = 0
            ''', conn)
            
            if not df_pend.empty:
                st.dataframe(df_pend, use_container_width=True)
                app_uid = st.number_input("Enter User Table ID to Approve:", min_value=1, step=1)
                if st.button("✅ Approve Customer"):
                    c.execute("UPDATE users SET is_approved = 1 WHERE id = ?", (app_uid,))
                    conn.commit()
                    st.success("Customer Approved Successfully!")
                    st.rerun()
            else:
                st.info("No pending approvals.")

        elif choice == "🛍️ Manage Services & Rates":
            st.subheader("🛍️ Add & Manage Offered Services (Grocery, Laundry, etc.)")
            with st.form("service_form"):
                col1, col2 = st.columns(2)
                with col1:
                    s_cat = st.selectbox("Category:", ["किराना (Grocery)", "कपड़ा प्रेस / ड्राई क्लीन", "टैक्स व अकाउंटिंग", "अन्य सेवा (Other)"])
                    s_name = st.text_input("Service / Item Name")
                with col2:
                    s_price = st.number_input("Rate / Price (₹):", min_value=0.0, step=10.0)
                    s_desc = st.text_area("Description:")
                
                submitted = st.form_submit_button("💾 Add Service")
                if submitted and s_name.strip():
                    c.execute("INSERT INTO services (category, service_name, price_rate, description) VALUES (?, ?, ?, ?)",
                              (s_cat, s_name.strip(), s_price, s_desc))
                    conn.commit()
                    st.success("Service added!")
                    st.rerun()

            df_serv = pd.read_sql_query("SELECT id as ID, category as Category, service_name as 'Service Name', price_rate as 'Rate (₹)', description as Details FROM services WHERE is_active = 1", conn)
            st.dataframe(df_serv, use_container_width=True)

        elif choice == "📦 View & Manage Customer Orders":
            st.subheader("📦 Customer Orders & Bills")
            df_orders = pd.read_sql_query('''
                SELECT 
                    o.id as 'Order ID',
                    COALESCE(c.unique_client_id, 'N/A') as 'Unique ID',
                    COALESCE(c.name, 'N/A') as 'Customer Name',
                    COALESCE(c.mobile, 'N/A') as 'Mobile',
                    o.items_summary as 'Items Ordered',
                    o.total_price as 'Total Bill (₹)',
                    o.order_date as 'Date',
                    o.delivery_address as 'Address',
                    o.order_status as 'Status'
                FROM orders o
                LEFT JOIN clients c ON o.client_id = c.id
                ORDER BY o.id DESC
            ''', conn)
            if not df_orders.empty:
                st.dataframe(df_orders, use_container_width=True)
                
                c_o1, c_o2 = st.columns(2)
                with c_o1:
                    ord_id = st.number_input("Order ID to Update Status:", min_value=1, step=1)
                with c_o2:
                    new_status = st.selectbox("Status:", ["Pending", "Processing", "Out for Delivery", "Completed", "Cancelled"])
                
                if st.button("Update Order Status"):
                    c.execute("UPDATE orders SET order_status = ? WHERE id = ?", (new_status, ord_id))
                    conn.commit()
                    st.success("Updated!")
                    st.rerun()
            else:
                st.info("No orders found.")

        elif choice == "➕ Add New Client Profile":
            st.subheader("📝 Add Client Profile (Admin)")
            col1, col2 = st.columns(2)
            with col1:
                u_id = st.text_input("Assign Unique Client ID *", value=generate_auto_client_id())
                name = st.text_input("Client Full Name *")
                father = st.text_input("Father's Name")
                mobile = st.text_input("Mobile Number *")
            with col2:
                address = st.text_area("Address")
                pan = st.text_input("PAN Number")

            if st.button("Save Client Profile"):
                today = datetime.now().strftime("%Y-%m-%d")
                c.execute("INSERT INTO clients (unique_client_id, name, father_name, pan_number, mobile, address, created_date) VALUES (?,?,?,?,?,?,?)",
                          (u_id.upper(), name, father, pan.upper(), mobile, address, today))
                conn.commit()
                st.success(f"Client Profile Saved Successfully with ID: {u_id.upper()}")

        elif choice == "🔍 Client Ledger & Credentials":
            st.subheader("🔍 Client Statement & Master Ledger")
            c.execute("SELECT id, name, unique_client_id, mobile FROM clients ORDER BY name ASC")
            clients = c.fetchall()
            if clients:
                opts = {f"{r[1]} | ID: {r[2]} | Mob: {r[3]}": r[0] for r in clients}
                sel = st.selectbox("Select Client:", list(opts.keys()))
                cid = opts[sel]

                fy = st.selectbox("Select Financial Year:", FY_LIST, index=4)
                c.execute("SELECT annual_fee FROM client_years WHERE client_id = ? AND financial_year = ?", (cid, fy))
                fee_r = c.fetchone()
                fee = fee_r[0] if fee_r else 0.0

                df_p = pd.read_sql_query("SELECT payment_date as Date, amount_paid as Paid, payment_mode as Mode, remarks as Remarks FROM payments WHERE client_id = ? AND financial_year = ?", conn, params=(cid, fy))
                tot_p = df_p['Paid'].sum() if not df_p.empty else 0.0
                due = fee - tot_p

                m1, m2, m3 = st.columns(3)
                m1.metric("Fee", f"₹{fee}")
                m2.metric("Received", f"₹{tot_p}")
                m3.metric("Due", f"₹{due}")

                st.dataframe(df_p)

        elif choice == "📊 Overall Business Report":
            st.subheader("📊 Business Report")
            df = pd.read_sql_query("SELECT unique_client_id as 'Unique ID', name, mobile, address FROM clients", conn)
            st.dataframe(df, use_container_width=True)

    # --------------- CUSTOMER MENU ---------------
    elif st.session_state.user_role == "Customer":
        st.title("👤 Customer Service Portal & Cart")
        cid = st.session_state.client_id

        c.execute("SELECT unique_client_id, name, pan_number, mobile, address FROM clients WHERE id = ?", (cid,))
        client_info = c.fetchone()

        c_uid = client_info[0] if client_info and client_info[0] else "N/A"
        c_name = client_info[1] if client_info and client_info[1] else "Customer"
        c_mob = client_info[3] if client_info and client_info[3] else "N/A"
        c_addr = client_info[4] if client_info and client_info[4] else ""

        st.info(f"👤 **{c_name}** | 🆔 **ID:** `{c_uid}` | 📱 **Mobile:** {c_mob}")

        tab_order, tab_cart, tab_my_orders, tab_ledger = st.tabs([
            "🛒 Browse & Add Items", 
            "🛍️ My Cart & Bill", 
            "📦 My Orders Status", 
            "📊 My Ledger"
        ])

        # TAB 1: BROWSE & ADD TO CART
        with tab_order:
            st.subheader("🛍️ Select Items (किराना, कपड़ा प्रेस, आदि)")
            c.execute("SELECT id, category, service_name, price_rate, description FROM services WHERE is_active = 1")
            services_list = c.fetchall()

            if not services_list:
                st.warning("कोई सर्विस उपलब्ध नहीं है।")
            else:
                s_dict = {f"[{s[1]}] {s[2]} (₹{s[3]})": s for s in services_list}
                sel_label = st.selectbox("चुनें:", list(s_dict.keys()))
                s_item = s_dict[sel_label]

                qty = st.number_input("मात्रा (Quantity / Units):", min_value=1, value=1, step=1)
                
                if st.button("➕ कार्ट में जोड़ें (Add to Cart)"):
                    item_total = qty * s_item[3]
                    st.session_state.cart.append({
                        "id": s_item[0],
                        "name": s_item[2],
                        "price": s_item[3],
                        "qty": qty,
                        "total": item_total
                    })
                    st.success(f"✅ {s_item[2]} ({qty} नग) कार्ट में जुड़ गया!")

        # TAB 2: CART & BILL GENERATION
        with tab_cart:
            st.subheader("🛍️ आपकी कार्ट और कुल बिल (Cart & Bill)")
            if st.session_state.cart:
                df_cart = pd.DataFrame(st.session_state.cart)
                st.dataframe(df_cart[['name', 'price', 'qty', 'total']], use_container_width=True)
                
                grand_total = df_cart['total'].sum()
                st.markdown(f"### 💵 कुल योग (Grand Total): **₹{grand_total:,.2f}**")
                
                if st.button("🗑️ कार्ट खाली करें (Clear Cart)"):
                    st.session_state.cart = []
                    st.rerun()

                st.markdown("---")
                st.subheader("📄 बिल जनरेट करें और ऑर्डर दें")
                del_addr = st.text_area("डिलिवरी पता (Delivery Address):", value=c_addr)
                note = st.text_input("विशेष निर्देश (Special Note):")

                if st.button("🚀 आर्डर फाइनल करें (Place Final Order & Bill)"):
                    summary_str = ", ".join([f"{i['name']} (x{i['qty']})" for i in st.session_state.cart])
                    today_dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    c.execute('''
                        INSERT INTO orders (client_id, items_summary, total_price, order_date, delivery_address, remarks)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (cid, summary_str, grand_total, today_dt, del_addr, note))
                    conn.commit()
                    
                    st.success("🎉 आपका ऑर्डर सफलतापूर्वक दर्ज हो गया है!")
                    
                    bill_msg = f"🧾 *NIKA STORE - OFFICIAL BILL* 🧾\n\n👤 कस्टमर: {c_name} (ID: {c_uid})\n📱 मोबाइल: {c_mob}\n\n*सामान सूची:*\n{summary_str}\n\n💰 *कुल योग: ₹{grand_total:,.2f}*\n🏠 पता: {del_addr}\n\nधन्यवाद!"
                    
                    st.markdown(f"""
                    <div class="bill-box">
                        <h3>🧾 डिजिटल बिल (Invoice)</h3>
                        <p><b>कस्टमर:</b> {c_name} ({c_uid})</p>
                        <p><b>आइटम्स:</b> {summary_str}</p>
                        <hr>
                        <h3><b>कुल भुगतान राशि: ₹{grand_total:,.2f}</b></h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    wa_link = create_whatsapp_link(MY_CONTACT, bill_msg)
                    st.link_button("💬 व्हाट्सएप पर बिल और ऑर्डर भेजें", wa_link, use_container_width=True)
                    
                    st.session_state.cart = []
            else:
                st.info("🛒 आपकी कार्ट खाली है। कृपया 'Browse & Add Items' से सामान चुनें।")

        # TAB 3: MY ORDERS STATUS
        with tab_my_orders:
            st.subheader("📦 मेरे ऑर्डर्स का स्टेटस")
            df_my = pd.read_sql_query("SELECT id as 'Order ID', items_summary as 'Items', total_price as 'Total (₹)', order_date as 'Date', order_status as 'Status' FROM orders WHERE client_id = ? ORDER BY id DESC", conn, params=(cid,))
            if not df_my.empty:
                st.dataframe(df_my, use_container_width=True)
            else:
                st.info("आपने अभी तक कोई ऑर्डर नहीं दिया है।")

        # TAB 4: LEDGER
        with tab_ledger:
            st.subheader("📅 टैक्स और फीस लेजर")
            sel_fy = st.selectbox("Financial Year:", FY_LIST, index=4)
            c.execute("SELECT annual_fee, income_tax_status, gst_status FROM client_years WHERE client_id = ? AND financial_year = ?", (cid, sel_fy))
            y_data = c.fetchone()
            fee = y_data[0] if y_data else 0.0
            st.metric("Tax / Annual Fee Due", f"₹{fee:,.2f}")
