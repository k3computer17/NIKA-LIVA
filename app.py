import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection

# =========================================================
# 1. PAGE CONFIG & BRANDING
# =========================================================
st.set_page_config(page_title="NIKA Multi-Service & Grocery Portal", page_icon="🛍️", layout="wide")

MY_CONTACT = "919000000000"  # Aapka WhatsApp Number

# =========================================================
# 2. GOOGLE SHEETS CONNECTION & HELPER FUNCTIONS
# =========================================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Google Sheets connection error! Kripya Streamlit Settings me Secrets check karein.")

def load_sheet(sheet_name):
    """Google Sheet se data read karne ke liye"""
    try:
        df = conn.read(worksheet=sheet_name)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def save_sheet(sheet_name, df):
    """Google Sheet me data save/update karne ke liye"""
    conn.update(worksheet=sheet_name, data=df)

def create_whatsapp_link(mobile, text_msg):
    import urllib.parse
    return f"https://wa.me/{mobile}?text={urllib.parse.quote(text_msg)}"

def generate_auto_client_id(clients_df):
    count = len(clients_df) if not clients_df.empty else 0
    return f"NK-CUST-{1001 + count}"

# =========================================================
# 3. AUTHENTICATION & SESSION STATE
# =========================================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

st.title("🛍️ NIKA Multi-Service & Grocery Portal")

# Worksheets ka Data Load Karein
users_df = load_sheet("Users")
clients_df = load_sheet("Clients")
categories_df = load_sheet("Categories")
subcategories_df = load_sheet("Subcategories")
services_df = load_sheet("Services")

if not st.session_state['logged_in']:
    login_tab, reg_tab = st.tabs(["🔐 Login", "📝 New Registration"])

    # ---------------- LOGIN ----------------
    with login_tab:
        st.subheader("कस्टमर / एडमिन लॉगिन")
        username = st.text_input("User ID")
        password = st.text_input("Password", type="password")
        
        if st.button("🚀 Login"):
            if not users_df.empty:
                user_match = users_df[(users_df['username'].astype(str) == username) & (users_df['password'].astype(str) == password)]
                if not user_match.empty:
                    user_row = user_match.iloc[0]
                    if int(user_row['is_approved']) == 1:
                        st.session_state['logged_in'] = True
                        st.session_state['user_info'] = user_row
                        st.success("✅ लॉगिन सफल हुआ!")
                        st.rerun()
                    else:
                        st.warning("⚠️ आपका खाता अभी स्वीकृत (Approved) नहीं हुआ है। कृपया एडमिन से संपर्क करें।")
                else:
                    st.error("❌ गलत Username या Password!")
            else:
                st.error("❌ Users sheet me koi data nahi mil raha!")

    # ---------------- NEW REGISTRATION ----------------
    with reg_tab:
        st.subheader("📝 नया कस्टमर रजिस्ट्रेशन (Live GPS)")
        auto_id = generate_auto_client_id(clients_df)
        
        col1, col2 = st.columns(2)
        with col1:
            c_name = st.text_input("👤 पूरा नाम (Full Name) *")
            c_father = st.text_input("👨‍👦 पिता/पति का नाम")
            c_mobile = st.text_input("📱 मोबाइल नंबर *")
        with col2:
            c_unique = st.text_input("🆔 Client ID (Auto Generated)", value=auto_id, disabled=True)
            c_userid = st.text_input("🧑‍💻 User ID बनाएं *")
            c_pass = st.text_input("🔑 Password बनाएं *", type="password")

        st.markdown("---")
        st.subheader("📍 लाइव जीपीएस लोकेशन (GPS Fetcher)")

        gps_html_code = """
        <div style="font-family: sans-serif; background: #fff3e0; padding: 15px; border-radius: 8px; border: 1px solid #ffccbc;">
            <p style="margin:0 0 10px 0; font-weight: bold; color: #d84315;">📡 ऑटोमेटिक लाइव लोकेशन डिटेक्टर:</p>
            <button onclick="getLiveLocation()" style="background: #f4511e; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; font-weight: bold;">
                📍 GPS से लोकेशन प्राप्त करें
            </button>
            <p id="status" style="margin-top:8px; font-size:13px; color:#555;">बटन दबाएं...</p>
            
            <div style="margin-top: 10px;">
                <label style="font-size: 12px; font-weight: bold;">ऑटो डिटेक्टेड एड्रेस:</label><br>
                <textarea id="fetched_address" rows="2" style="width: 100%; border-radius: 5px; border: 1px solid #ccc; padding: 5px;" readonly></textarea>
            </div>
            <div style="display: flex; gap: 10px; margin-top: 5px;">
                <div><small>Latitude:</small> <input type="text" id="lat" style="width: 100%;" readonly></div>
                <div><small>Longitude:</small> <input type="text" id="lng" style="width: 100%;" readonly></div>
            </div>
        </div>

        <script>
        function getLiveLocation() {
            var status = document.getElementById('status');
            if (navigator.geolocation) {
                status.innerText = "लोकेशन फेच हो रही है...";
                navigator.geolocation.getCurrentPosition(showPosition, showError, {enableHighAccuracy: true});
            } else {
                status.innerText = "जीपीएस सपोर्ट उपलब्ध नहीं है।";
            }
        }
        function showPosition(position) {
            var lat = position.coords.latitude;
            var lng = position.coords.longitude;
            document.getElementById('lat').value = lat;
            document.getElementById('lng').value = lng;
            
            fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`)
                .then(response => response.json())
                .then(data => {
                    if (data && data.display_name) {
                        document.getElementById('fetched_address').value = data.display_name;
                        status.innerText = "✅ लोकेशन सफलतापूर्वक मिली!";
                    } else {
                        document.getElementById('fetched_address').value = "Lat: " + lat + ", Lng: " + lng;
                        status.innerText = "Coordinates मिल गए।";
                    }
                }).catch(err => {
                    document.getElementById('fetched_address').value = "Lat: " + lat + ", Lng: " + lng;
                });
        }
        function showError(error) {
            document.getElementById('status').innerText = "⚠️ लोकेशन एरर: " + error.message;
        }
        window.onload = getLiveLocation;
        </script>
        """
        components.html(gps_html_code, height=250)

        c_address = st.text_area("🏠 डिलीवरी का पूरा पता (Manual/Confirm) *", placeholder="ऊपर से देखकर या अपना सही पता यहाँ लिखें...")
        lat_val = st.text_input("Latitude", value="0.0")
        lon_val = st.text_input("Longitude", value="0.0")

        if st.button("✨ Register Account"):
            if not all([c_name, c_userid, c_pass, c_mobile, c_address]):
                st.error("कृपया सभी आवश्यक (*) जानकारी भरें!")
            else:
                today = datetime.now().strftime("%Y-%m-%d")
                
                # 1. New Client Data
                new_client = {
                    "id": len(clients_df) + 1,
                    "unique_client_id": auto_id,
                    "name": c_name,
                    "father_name": c_father,
                    "mobile": c_mobile,
                    "address": c_address,
                    "created_date": today,
                    "latitude": lat_val,
                    "longitude": lon_val
                }
                updated_clients = pd.concat([clients_df, pd.DataFrame([new_client])], ignore_index=True)
                save_sheet("Clients", updated_clients)

                # 2. New User Data
                new_user = {
                    "id": len(users_df) + 1,
                    "username": c_userid,
                    "password": c_pass,
                    "plain_pass": c_pass,
                    "role": "Customer",
                    "client_id": auto_id,
                    "is_approved": 0
                }
                updated_users = pd.concat([users_df, pd.DataFrame([new_user])], ignore_index=True)
                save_sheet("Users", updated_users)

                st.success(f"✅ रजिस्ट्रेशन सफल हुआ! आपकी यूनिक ID है: **{auto_id}**")
                wa_msg = f"नमस्ते एडमिन, नया यूजर रजिस्टर हुआ है:\nनाम: {c_name}\nयूजर ID: {c_userid}\nClient ID: {auto_id}"
                st.link_button("💬 Send Approval Request to Admin", create_whatsapp_link(MY_CONTACT, wa_msg))

else:
    # Logout Header
    st.sidebar.write(f"Logged in as: **{st.session_state['user_info']['username']}** ({st.session_state['user_info']['role']})")
    if st.sidebar.button("🚪 Logout"):
        st.session_state['logged_in'] = False
        st.session_state['user_info'] = None
        st.rerun()

    user_role = st.session_state['user_info']['role']

    # =========================================================
    # 4. MASTER ADMIN DASHBOARD (GOOGLE SHEETS BACKEND)
    # =========================================================
    if user_role == "Admin":
        st.sidebar.title("👑 Admin Panel")
        admin_choice = st.sidebar.radio("Navigation", ["🏬 Category & Item Master", "👥 Customers List", "⚙️ Approval Requests"])

        # ------------ 1. CATEGORY & ITEM MASTER ------------
        if admin_choice == "🏬 Category & Item Master":
            st.title("🏬 श्रेणी, उप-श्रेणी एवं सामान प्रबंधन")
            
            t1, t2, t3 = st.tabs(["📁 1. Main Category", "📑 2. Sub-Category", "📦 3. Items / Products"])

            # ---- MAIN CATEGORY ----
            with t1:
                st.subheader("नई श्रेणी जोड़ें")
                with st.form("add_cat_form", clear_on_submit=True):
                    cat_name = st.text_input("Category Name")
                    submit_cat = st.form_submit_button("➕ Safe & Permanent Save")
                    if submit_cat and cat_name:
                        new_cat = {"id": len(categories_df) + 1, "category_name": cat_name.strip()}
                        updated_cats = pd.concat([categories_df, pd.DataFrame([new_cat])], ignore_index=True)
                        save_sheet("Categories", updated_cats)
                        st.success(f"✅ Category '{cat_name}' Google Sheet me save ho gayi!")
                        st.rerun()

                st.markdown("---")
                st.subheader("📋 वर्तमान श्रेणियाँ (Current Categories)")
                st.dataframe(categories_df, use_container_width=True)

            # ---- SUB CATEGORY ----
            with t2:
                st.subheader("नई उप-श्रेणी (Sub-Category) जोड़ें")
                cat_list = categories_df['category_name'].tolist() if not categories_df.empty else []

                if cat_list:
                    with st.form("add_subcat_form", clear_on_submit=True):
                        sel_cat = st.selectbox("मुख्य श्रेणी चुनें", cat_list)
                        subcat_name = st.text_input("Sub-Category Name")
                        sub_btn = st.form_submit_button("➕ Save Sub-Category")

                        if sub_btn and subcat_name:
                            new_subcat = {
                                "id": len(subcategories_df) + 1,
                                "category_name": sel_cat,
                                "sub_category_name": subcat_name.strip()
                            }
                            updated_subcats = pd.concat([subcategories_df, pd.DataFrame([new_subcat])], ignore_index=True)
                            save_sheet("Subcategories", updated_subcats)
                            st.success(f"✅ Sub-Category '{subcat_name}' save ho gayi!")
                            st.rerun()
                else:
                    st.warning("कृपया पहले मेन श्रेणी जोड़ें!")

                st.markdown("---")
                st.dataframe(subcategories_df, use_container_width=True)

            # ---- ITEMS / PRODUCTS ----
            with t3:
                st.subheader("नया आइटम/सामान जोड़ें")
                cats = categories_df['category_name'].tolist() if not categories_df.empty else []

                if cats:
                    sel_item_cat = st.selectbox("Category", cats, key="item_cat")
                    subcats_filtered = subcategories_df[subcategories_df['category_name'] == sel_item_cat]['sub_category_name'].tolist() if not subcategories_df.empty else []
                    
                    if not subcats_filtered:
                        subcats_filtered = ["General"]

                    with st.form("add_item_form", clear_on_submit=True):
                        sel_item_subcat = st.selectbox("Sub-Category", subcats_filtered)
                        i_name = st.text_input("Item Name *")
                        col_p1, col_p2 = st.columns(2)
                        with col_p1:
                            i_unit = st.selectbox("Unit", ["Kg", "Gram", "Liter", "Piece", "Packet", "Box"])
                        with col_p2:
                            i_price = st.number_input("Rate / Price (₹)", min_value=0.0, step=1.0)
                        
                        item_btn = st.form_submit_button("📦 Save Item")

                        if item_btn and i_name:
                            new_item = {
                                "id": len(services_df) + 1,
                                "category": sel_item_cat,
                                "sub_category": sel_item_subcat,
                                "service_name": i_name,
                                "unit": i_unit,
                                "price_rate": i_price,
                                "is_active": 1
                            }
                            updated_services = pd.concat([services_df, pd.DataFrame([new_item])], ignore_index=True)
                            save_sheet("Services", updated_services)
                            st.success(f"✅ Item '{i_name}' Sheet me save ho gaya!")
                            st.rerun()
                else:
                    st.info("पहले Category जोड़ें।")

                st.markdown("---")
                st.subheader("📦 संपूर्ण सामान सूची (Items Database)")
                st.dataframe(services_df, use_container_width=True)

        # ------------ 2. CUSTOMERS LIST ------------
        elif admin_choice == "👥 Customers List":
            st.title("👥 ग्राहक सूची (Registered Customers)")
            st.dataframe(clients_df, use_container_width=True)

        # ------------ 3. APPROVAL REQUESTS ------------
        elif admin_choice == "⚙️ Approval Requests":
            st.title("⚙️ Pending Customer Approvals")
            if not users_df.empty:
                pending_users = users_df[users_df['is_approved'].astype(int) == 0]
                if not pending_users.empty:
                    for idx, row in pending_users.iterrows():
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            st.write(f"🧑‍💻 User: **{row['username']}** | Role: {row['role']}")
                        with col_b:
                            if st.button(f"Approve {row['username']}", key=f"app_{row['id']}"):
                                users_df.loc[users_df['id'] == row['id'], 'is_approved'] = 1
                                save_sheet("Users", users_df)
                                st.success("Approved!")
                                st.rerun()
                else:
                    st.info("कोई पेंडिंग रिक्वेस्ट नहीं है।")

    # =========================================================
    # 5. CUSTOMER DASHBOARD (SHOPPING & PORTAL)
    # =========================================================
    else:
        st.title("🛒 Grocery & Portal Shop")
        st.write("आपका स्वागत है!")
        
        categories = categories_df['category_name'].tolist() if not categories_df.empty else []
        
        if categories:
            selected_cat = st.selectbox("📂 Category चुनें:", categories)
            if not services_df.empty:
                filtered_items = services_df[(services_df['category'] == selected_cat) & (services_df['is_active'].astype(int) == 1)]
                if not filtered_items.empty:
                    st.table(filtered_items[['service_name', 'unit', 'price_rate']])
                else:
                    st.info("इस श्रेणी में अभी कोई आइटम उपलब्ध नहीं हैं।")
            else:
                st.info("कोई आइटम उपलब्ध नहीं हैं।")
        else:
            st.info("दुकान में अभी कोई श्रेणी नहीं जोड़ी गई है।")
