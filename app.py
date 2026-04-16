import streamlit as st
import pandas as pd
import re
import io

def parse_property_data(text):
    text = re.sub(r'\[\d{1,2}:\d{2}\s?[ap]m,\s\d{1,2}/\d{1,2}/\d{4}\]\sEasy\sProp\sNew:\s', '\nNEW_MSG\n', text)
    messages = re.split(r'\nNEW_MSG\n|\n(?=\d{2}\.\d{2}\.\d{4})', text)
    data = []
    columns = ['property_id', 'property_type', 'special_note', 'owner_name', 'owner_contact', 'area', 'address', 'sub_property_type', 'size', 'furnishing_status', 'availability', 'floor', 'tenant_preference', 'additional_details', 'age', 'rent_or_sell_price', 'deposit', 'date_stamp', 'rent_sold_out']

    for msg in messages:
        msg = msg.strip()
        if len(msg) < 40: continue 
        lines = [line.strip() for line in msg.split('\n') if line.strip()]
        entry = {col: 'N/A' for col in columns}
        
        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', msg)
        if date_match: entry['date_stamp'] = date_match.group(1)
        if "Rent Property" in msg: entry['property_type'] = "Res_rental"
        elif "Resale Property" in msg: entry['property_type'] = "Res_resale"
        v_match = re.search(r'(Verified|Not Verified\(.*?\))', msg)
        if v_match: entry['special_note'] = v_match.group(1)
        code_match = re.search(r'Property Code\s+([A-Z0-9]+)', msg)
        if code_match: entry['property_id'] = code_match.group(1)
        
        owner_match = re.search(r'Owner Details:\s*\n?(.*?)\s+(\d{10})', msg)
        if owner_match:
            entry['owner_name'] = owner_match.group(1).strip()
            entry['owner_contact'] = owner_match.group(2).strip()
        
        size_idx = -1
        for i, line in enumerate(lines):
            if any(x in line.lower() for x in ["super built-up area", "sqft", "sq.ft"]):
                size_idx = i
                config_part = line.split('/')[0].strip()
                entry['sub_property_type'] = config_part.split(',')[0].strip().replace("Bedrooms", "BHK").replace("Bedroom", "BHK") if "BHK" not in config_part else config_part
                s_match = re.search(r'Area\s+([\d\.]+)', line, re.I)
                if s_match: entry['size'] = s_match.group(1) + " sq.ft"
                break
        
        if size_idx != -1 and size_idx + 1 < len(lines):
            entry['area'] = lines[size_idx+1]
            if size_idx + 2 < len(lines):
                next_line = lines[size_idx+2]
                if not any(x in next_line for x in ["Rent:", "Lac", "Cr", "Furnished", "Floor", "MagicBricks", "99acres"]):
                    entry['address'] = next_line

        f_lower = msg.lower()
        if "semi-furnished" in f_lower or "semifurnished" in f_lower: entry['furnishing_status'] = "Semi-Furnished"
        elif "unfurnished" in f_lower: entry['furnishing_status'] = "Unfurnished"
        elif "furnished" in f_lower: entry['furnishing_status'] = "Furnished"
                
        rent_match = re.search(r'Rent:\s*(\d+)', msg)
        if rent_match: entry['rent_or_sell_price'] = rent_match.group(1)
        price_match = re.search(r'(\d+(?:\.\d+)?\s*(?:Lac|Cr))', msg)
        if price_match: entry['rent_or_sell_price'] = price_match.group(1)
        
        for line in lines:
            if "Deposite:" in line:
                d_match = re.search(r'Deposite:\s*(\d+)', line)
                if d_match: entry['deposit'] = d_match.group(1)

        data.append(entry)
    return pd.DataFrame(data)

st.set_page_config(page_title="Cleardeals Automation", layout="wide")
st.title("📋 Property Lead Converter")
input_text = st.text_area("WhatsApp Messages Paste Karein:", height=300)
if st.button("Extract Data"):
    if input_text:
        df = parse_property_data(input_text)
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", data=csv, file_name="leads.csv", mime="text/csv")
