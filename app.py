import streamlit as st
import pandas as pd
import re
import io

def clean_area(text):
    if text == 'N/A' or not text: return 'N/A'
    
    # "Pune", "Maharashtra", "in ", "at " jaise words hatayein
    text = re.sub(r'\bin\b|\bat\b|\bPune\b|\bMaharashtra\b', '', text, flags=re.IGNORECASE)
    
    # Agar comma hai (Example: "Project Name, Area"), toh last vala part aksar Area hota hai
    parts = [p.strip() for p in text.split(',') if p.strip()]
    if len(parts) > 1:
        # Check if the last part is just whitespace or city noise, otherwise take it
        final_area = parts[-1]
    else:
        final_area = parts[0] if parts else 'N/A'
    
    # "Budruk", "Khurd", "Phase" jaise extra words hatayein
    final_area = re.sub(r'\bBudruk\b|\bKhurd\b|\bPhase\s?\d+\b', '', final_area, flags=re.IGNORECASE).strip()
    return final_area

def convert_price(price_str):
    if price_str == 'N/A' or not price_str: return 'N/A'
    
    # Remove Currency symbols and commas
    price_clean = str(price_str).replace('₹', '').replace(',', '').replace('Rs', '').strip()
    
    # Regex to find number and the multiplier (Lac, Cr, L)
    match = re.search(r'(\d+(?:\.\d+)?)\s*(Lac|Cr|L|Cr\.)?', price_clean, re.IGNORECASE)
    if not match: return 'N/A'
    
    num = float(match.group(1))
    unit = match.group(2).lower() if match.group(2) else ''
    
    if unit in ['lac', 'l']:
        return int(num * 100000)
    elif unit in ['cr', 'cr.']:
        return int(num * 10000000)
    else:
        # For Rent (normal numbers)
        return int(num)

def parse_property_data(text):
    # Standardizing messages
    text = re.sub(r'\[\d{1,2}:\d{2}\s?[ap]m,\s\d{1,2}/\d{1,2}/\d{4}\]\sEasy\sProp\sNew:\s', '\nNEW_MSG\n', text)
    messages = re.split(r'\nNEW_MSG\n|\n(?=\d{2}\.\d{2}\.\d{4})', text)
    
    data = []
    columns = ['property_id', 'property_type', 'special_note', 'owner_name', 'owner_contact', 'area', 'address', 'sub_property_type', 'size', 'furnishing_status', 'availability', 'floor', 'tenant_preference', 'additional_details', 'age', 'rent_or_sell_price', 'deposit', 'date_stamp', 'rent_sold_out']

    for msg in messages:
        msg = msg.strip()
        if len(msg) < 30: continue 
        
        lines = [line.strip() for line in msg.split('\n') if line.strip()]
        entry = {col: 'N/A' for col in columns}
        
        # Date & Type
        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', msg)
        if date_match: entry['date_stamp'] = date_match.group(1)
        entry['property_type'] = "Res_rental" if "Rent Property" in msg else "Res_resale"
        
        v_match = re.search(r'(Verified|Not Verified\(.*?\))', msg)
        if v_match: entry['special_note'] = v_match.group(1)
        
        code_match = re.search(r'Property Code\s+([A-Z0-9]+)', msg)
        if code_match: entry['property_id'] = code_match.group(1)
            
        # Owner Details
        owner_match = re.search(r'Owner Details:\s*\n?(.*?)\s+(\d{10})', msg)
        if owner_match:
            entry['owner_name'] = owner_match.group(1).strip()
            entry['owner_contact'] = owner_match.group(2).strip()

        # Size & Config
        size_idx = -1
        for i, line in enumerate(lines):
            if any(x in line.lower() for x in ["super built-up area", "sqft", "sq.ft"]):
                size_idx = i
                # Convert "1 Bedroom" to "1 BHK"
                config = line.split('/')[0].strip()
                config = re.sub(r'(\d+)\s*Bedroom[s]?', r'\1 BHK', config, flags=re.I)
                entry['sub_property_type'] = config.split(',')[0].strip()
                
                s_match = re.search(r'Area\s+([\d,\.]+)', line, re.I)
                if s_match: entry['size'] = s_match.group(1).replace(',', '') + " sq.ft"
                break
        
        # Area & Address
        if size_idx != -1 and size_idx + 1 < len(lines):
            raw_area = lines[size_idx+1]
            entry['area'] = clean_area(raw_area)
            if size_idx + 2 < len(lines):
                next_line = lines[size_idx+2]
                if not any(x in next_line for x in ["Rent:", "Lac", "Cr", "L ", "₹", "Furnished", "Floor"]):
                    entry['address'] = next_line

        # Furnishing
        f_lower = msg.lower()
        if "semi-furnished" in f_lower or "semifurnished" in f_lower or "semi furnished" in f_lower: entry['furnishing_status'] = "Semi-Furnished"
        elif "unfurnished" in f_lower: entry['furnishing_status'] = "Unfurnished"
        elif "fully furnished" in f_lower or "furnished" in f_lower: entry['furnishing_status'] = "Furnished"
                
        # Rent/Price Logic
        price_found = 'N/A'
        rent_match = re.search(r'Rent:\s*(\d+)', msg)
        price_match = re.search(r'(?:₹|Rs\.?|)\s*(\d+(?:\.\d+)?)\s*(Lac|Cr|L|Cr\.)', msg, re.I)
        
        if rent_match: price_found = rent_match.group(1)
        elif price_match: price_found = price_match.group(0)
        
        entry['rent_or_sell_price'] = convert_price(price_found)
        
        # Deposit
        dep_match = re.search(r'Deposite:\s*(\d+)', msg)
        if dep_match: entry['deposit'] = dep_match.group(1)

        data.append(entry)
    return pd.DataFrame(data)

# STREAMLIT UI
st.set_page_config(page_title="Cleardeals Automation", layout="wide")
st.title("📋 Property Lead Converter (Version 2.0)")
st.write("Ab Area aur Price extraction aur behtar hai.")

input_text = st.text_area("WhatsApp Messages Paste Karein:", height=400)
if st.button("Extract Data"):
    if input_text:
        df = parse_property_data(input_text)
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", data=csv, file_name="property_leads_v2.csv", mime="text/csv")
