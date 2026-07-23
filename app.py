import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from streamlit_geolocation import streamlit_geolocation
import io

# पेज कॉन्फ़िगरेशन
st.set_page_config(page_title="CA & Client Management System", layout="wide")

# 1. Google Sheets और Drive API कनेक्शन
@st.cache_resource
def get_gspread_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("ClientData").sheet1
    
    drive_service = build('drive', 'v3', credentials=creds)
    return sheet, drive_service

try:
    sheet, drive_service = get_gspread_client()
except Exception as e:
    st.error("Google APIs से कनेक्ट करने में समस्या आई। कृपया 'credentials.json' फाइल चेक करें।")

# 2. गूगल ड्राइव में फाइल/सेल्फी अपलोड करने का फ़ंक्शन
def upload_to_drive(file, folder_id=None):
    file_metadata = {'name': file.name if hasattr(file, 'name') else 'selfie.jpg'}
    if folder_id:
        file_metadata['parents'] = [folder_id]
        
    media = MediaIoBaseUpload(io.BytesIO(file.getvalue()), mimetype="image/jpeg" if not hasattr(file, 'type') else file.type, resumable=True)
    uploaded_file = drive_service.files().create(
        body=file_metadata, media_body=media, fields='id, webViewLink'
    ).execute()
    
    return uploaded_file.get('webViewLink')

# मुख्य शीर्षक
st.title("💼 क्लाइंट एवं टैक्स रिटर्न मैनेजमेंट सिस्टम")

# रोल्स चुनना (Admin/CA या Client Portal)
user_role = st.sidebar.radio("सिस्टम मोड चुनें:", ["👨‍💼 Admin (CA/टैक्स कंसलटेंट)", "👤 Client Portal (क्लाइंट लॉगिन)"])

# =====================================================================
# PART 1: ADMIN PANEL (CA के लिए)
# =====================================================================
if user_role == "👨‍💼 Admin (CA/टैक्स कंसलटेंट)":
    menu = ["📊 डैशबोर्ड व लिस्ट", "➕ नया क्लाइंट जोड़ें", "🔄 स्टेटस अपडेट करें"]
    choice = st.sidebar.selectbox("एडमिन मेनू", menu)

    # डैशबोर्ड व लिस्ट
    if choice == "📊 डैशबोर्ड व लिस्ट":
        st.subheader("📋 सभी क्लाइंट्स का रिकॉर्ड")
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            if not df.empty:
                # मुख्य आंकड़े
                col1, col2, col3 = st.columns(3)
                col1.metric("कुल क्लाइंट्स", len(df))
                
                gst_pending = len(df[df['GST Status'] == 'Pending']) if 'GST Status' in df.columns else 0
                col2.metric("पेंडिंग GST रिटर्न्स", gst_pending)
                
                if 'Pending Amount' in df.columns:
                    df['Pending Amount'] = pd.to_numeric(df['Pending Amount'], errors='coerce').fillna(0)
                    total_due = df['Pending Amount'].sum()
                    col3.metric("कुल बकाया फीस", f"₹{total_due:,.2f}")
                
                st.markdown("---")
                
                # सर्च बार
                search = st.text_input("🔍 क्लाइंट का नाम या PAN/GSTIN खोजें:")
                if search:
                    df = df[df['Client Name'].str.contains(search, case=False, na=False) | 
                            df['PAN / GSTIN'].str.contains(search, case=False, na=False)]
                
                st.dataframe(df, use_container_width=True)
            else:
                st.info("अभी कोई डेटा उपलब्ध नहीं है।")
        except Exception as ex:
            st.warning("कृपया सुनिश्चित करें कि Google Sheet में सही कॉलम हेडिंग्स (Client ID, Client Name आदि) मौजूद हैं।")

    # नया क्लाइंट जोड़ें (सेल्फी और लोकेशन के साथ)
    elif choice == "➕ नया क्लाइंट जोड़ें":
        st.subheader("📝 नया क्लाइंट, सेल्फी और लाइव लोकेशन जोड़ें")
        
        with st.form("add_client_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                client_id = st.text_input("Client ID (जैसे: CLT01)*")
                client_name = st.text_input("Client Name (नाम/कंपनी)*")
                pan_gstin = st.text_input("PAN / GSTIN")
                phone_email = st.text_input("Phone / Email")
                password = st.text_input("लॉगिन पासवर्ड सेट करें*", type="password")
                
            with col2:
                gst_status = st.selectbox("GST Status", ["Pending", "Filed", "N/A"])
                itr_status = st.selectbox("ITR Status", ["Pending", "Filed", "N/A"])
                payment_status = st.selectbox("Payment Status", ["Paid", "Due", "Partial"])
                pending_amount = st.number_input("Pending Amount (₹)", min_value=0.0, step=500.0)
            
            submitted = st.form_submit_button("💾 डेटा सुरक्षित करें")

        st.markdown("---")
        st.subheader("📍 लाइव GPS लोकेशन")
        loc = streamlit_geolocation()
        lat = loc.get('latitude', '') if loc else ''
        lon = loc.get('longitude', '') if loc else ''
        if lat and lon:
            st.success(f"लोकेशन कैप्चर हो गई! (Lat: {lat}, Lon: {lon})")

        st.markdown("---")
        st.subheader("📸 क्लाइंट की सेल्फी")
        selfie_file = st.camera_input("कैमरा खोलकर फोटो लें")

        if submitted:
            if client_id and client_name and password:
                with st.spinner("डेटा सेव और अपलोड हो रहा है..."):
                    selfie_link = ""
                    if selfie_file is not None:
                        try:
                            selfie_link = upload_to_drive(selfie_file)
                        except Exception:
                            pass
                    
                    new_row = [
                        client_id, client_name, pan_gstin, phone_email,
                        gst_status, itr_status, payment_status, pending_amount,
                        password, selfie_link, str(lat), str(lon), ""
                    ]
                    sheet.append_row(new_row)
                    st.success(f"क्लाइंट '{client_name}' सफलतापूर्वक जोड़ दिया गया है!")
            else:
                st.warning("कृपया Client ID, Client Name और Password ज़रूर भरें।")

    # स्टेटस अपडेट करें
    elif choice == "🔄 स्टेटस अपडेट करें":
        st.subheader("✏️ क्लाइंट की जानकारी या फीस अपडेट करें")
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            if not df.empty:
                client_list = df['Client Name'].tolist()
                selected_client = st.selectbox("क्लाइंट चुनें", client_list)
                
                client_row = df[df['Client Name'] == selected_client].iloc[0]
                row_index = df[df['Client Name'] == selected_client].index[0] + 2
                
                with st.form("update_form"):
                    u_gst = st.selectbox("GST Status", ["Pending", "Filed", "N/A"], index=["Pending", "Filed", "N/A"].index(client_row['GST Status']) if client_row['GST Status'] in ["Pending", "Filed", "N/A"] else 0)
                    u_itr = st.selectbox("ITR Status", ["Pending", "Filed", "N/A"], index=["Pending", "Filed", "N/A"].index(client_row['ITR Status']) if client_row['ITR Status'] in ["Pending", "Filed", "N/A"] else 0)
                    u_pay = st.selectbox("Payment Status", ["Paid", "Due", "Partial"], index=["Paid", "Due", "Partial"].index(client_row['Payment Status']) if client_row['Payment Status'] in ["Paid", "Due", "Partial"] else 0)
                    u_amount = st.number_input("Pending Amount (₹)", value=float(client_row['Pending Amount']) if client_row['Pending Amount'] != '' else 0.0)
                    
                    update_btn = st.form_submit_button("अपडेट करें")
                    
                    if update_btn:
                        sheet.update_cell(row_index, 5, u_gst)
                        sheet.update_cell(row_index, 6, u_itr)
                        sheet.update_cell(row_index, 7, u_pay)
                        sheet.update_cell(row_index, 8, u_amount)
                        st.success("डेटा सफलताي से अपडेट हो गया!")
            else:
                st.info("कोई डेटा उपलब्ध नहीं है।")
        except Exception as ex:
            st.error(f"त्रुटि: {ex}")

# =====================================================================
# PART 2: CLIENT PORTAL (क्लाइंट्स के लिए)
# =====================================================================
elif user_role == "👤 Client Portal (क्लाइंट लॉगिन)":
    st.subheader("🔐 क्लाइंट लॉगिन पोर्टल")
    
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['client_data'] = None

    if not st.session_state['logged_in']:
        client_id_input = st.text_input("Client ID दर्ज करें")
        password_input = st.text_input("पासवर्ड दर्ज करें", type="password")
        login_btn = st.button("लॉगिन करें")

        if login_btn:
            try:
                data = sheet.get_all_records()
                df = pd.DataFrame(data)
                
                user = df[(df['Client ID'].astype(str) == client_id_input) & (df['Password'].astype(str) == password_input)]
                
                if not user.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['client_data'] = user.iloc[0]
                    st.session_state['row_index'] = user.index[0] + 2
                    st.rerun()
                else:
                    st.error("गलत Client ID या पासवर्ड!")
            except Exception as e:
                st.error("डेटाबेस से कनेक्ट करने में समस्या आई।")

    else:
        client = st.session_state['client_data']
        st.success(f"स्वागत है, **{client['Client Name']}**!")
        
        if st.button("लॉगआउट (बाहर निकलें)"):
            st.session_state['logged_in'] = False
            st.rerun()

        st.markdown("---")
        
        # स्टेटस दिखाना
        col1, col2, col3 = st.columns(3)
        col1.metric("GST Status", client['GST Status'])
        col2.metric("ITR Status", client['ITR Status'])
        col3.metric("Pending Fee", f"₹{client['Pending Amount']}")

        st.markdown("---")
        
        # दस्तावेज़ अपलोड सेक्शन
        st.subheader("📤 अपने दस्तावेज (PDF/Image) अपलोड करें")
        uploaded_file = st.file_uploader("फाइल चुनें", type=["pdf", "jpg", "png"])
        
        if uploaded_file is not None:
            if st.button("Google Drive पर अपलोड करें"):
                with st.spinner("फाइल अपलोड हो रही है..."):
                    try:
                        drive_link = upload_to_drive(uploaded_file)
                        existing_links = str(client.get('Uploaded Documents', ''))
                        updated_links = f"{existing_links} | {drive_link}" if existing_links else drive_link
                        
                        sheet.update_cell(st.session_state['row_index'], 13, updated_links)
                        st.success("फाइल सफलतापूर्वक अपलोड हो गई!")
                        st.markdown(f"🔗 [अपलोड की गई फाइल देखें]({drive_link})")
                    except Exception as ex:
                        st.error(f"अपलोड असफल: {ex}")
