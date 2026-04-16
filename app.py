import streamlit as st
import pandas as pd
import re
import io

def clean_area(text):
    if text == 'N/A': return text
    # Remove 'in ', 'Pune', 'Maharashtra' and extra spaces
    text = re.sub(r'\bin\b|\bPune\b|\bMaharashtra\b', '', text, flags=re.IGNORECASE)
    # Sirf pehla hissa rakhein agar comma ho (Example: "Kondhwa, Pune" -> "Kondhwa")
    text = text.split(',')[0].strip()
    return text

def convert_price(price_str):
    if price_str == 'N/A': return price_str
    price_str = str(price_str).lower().replace(',', '').strip()
    
    try:
        if 'lac' in price_str:
            num = float(re.findall(r"[-+]?\d*\.\d+|\d+", price_str)[0])
            return int(num * 100000)
        elif 'cr' in price_str:
            num = float(re.findall(r"[-+]?\d*\.\d+|\d+", price_str)[0])
            return int(num * 10000000)
        else:
            # Agar sirf number hai (Rent ke liye)
            return int(float(re.findall(r"\d+", price_str)[0]))
    except:
        return price_str

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
        
        # Basic Extraction
        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', msg)
        if date_match: entry['date_stamp'] = date_match.group(1)
        if "Rent Property" in msg: entry['property_type'] = "Res_rental"
        elif "Resale Property" in msg: entry['property_type'] = "Res_resale"
        
        # Owner & Contact
        owner_match = re.search(r'Owner Details:\s*\n?(.*?)\s+(\d{10})', msg)
        if owner_match:
            entry['owner_name'] = owner_match.group(1).strip()
            entry['owner_contact'] = owner_match.group(2).strip()

        # Size, Area and Address
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
            raw_area = lines[size_idx+1]
            entry['area'] = clean_area(raw_area) # Cleaning Area Here
            if size_idx + 2 < len(lines):
                next_line = lines[size_idx+2]
                if not any(x in next_line for x in ["Rent:", "Lac", "Cr", "Furnished", "Floor", "MagicBricks", "99acres"]):
                    entry['address'] = next_line

        # Furnishing & Price
        f_lower = msg.lower()
        if "semi-furnished" in f_lower or "semifurnished" in f_lower: entry['furnishing_status'] = "Semi-Furnished"
        elif "unfurnished" in f_lower: entry['furnishing_status'] = "Unfurnished"
        elif "furnished" in f_lower: entry['furnishing_status'] = "Furnished"
                
        # Price Logic
        price_val = 'N/A'
        rent_match = re.search(r'Rent:\s*(\d+)', msg)
        price_match = re.search(r'(\d+(?:\.\d+)?\s*(?:Lac|Cr))', msg, re.IGNORECASE)
        
        if rent_match: price_val = rent_match.group(1)
        elif price_match: price_val = price_match.group(1)
        
        entry['rent_or_sell_price'] = convert_price(price_val) # Converting Price to Numeric

        data.append(entry)
    return pd.DataFrame(data)

# STREAMLIT UI
st.set_page_config(page_title="Cleardeals Automation", layout="wide")
st.title("📋 Property Lead Converter (Pro)")
st.info("Note: Area names are now cleaned and Lac/Cr converted to numbers.")

input_text = st.text_area("WhatsApp Messages Paste Karein:", height=300)
if st.button("Extract Data"):
    if input_text:
        df = parse_property_data(input_text)
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", data=csv, file_name="leads_cleaned.csv", mime="text/csv")
