import streamlit as st
import pandas as pd
import re

def clean_area(text):
    if text == 'N/A' or not text: return 'N/A'
    # Remove noise words
    text = re.sub(r'\bin\b|\bat\b|\bPune\b|\bMaharashtra\b|\bBudruk\b|\bKhurd\b', '', text, flags=re.IGNORECASE)
    # Comma se split karke parts saaf karein
    parts = [p.strip() for p in text.split(',') if p.strip()]
    if not parts: return 'N/A'
    
    # Aksar aakhri word main area hota hai (Jaise: "Majestique Undri" -> "Undri")
    main_part = parts[0] # Pehla part lete hain
    words = main_part.split()
    if len(words) > 1:
        # Agar multiple words hain, toh aakhri word aksar locality hoti hai
        return words[-1].strip()
    return main_part

def convert_to_numeric_price(price_str):
    if price_str == 'N/A' or not price_str: return 'N/A'
    # Cleaning symbols
    p = str(price_str).replace('₹', '').replace(',', '').replace('Rs', '').strip()
    
    match = re.search(r'(\d+(?:\.\d+)?)\s*(Lac|Cr|L|Cr\.)?', p, re.IGNORECASE)
    if not match: return 'N/A'
    
    value = float(match.group(1))
    unit = match.group(2).lower() if match.group(2) else ''
    
    if unit in ['lac', 'l']:
        return int(value * 100000)
    elif unit in ['cr', 'cr.']:
        return int(value * 10000000)
    else:
        return int(value) # Normal Rent numbers

def parse_leads(text):
    # Split using Property Code as a more reliable anchor
    segments = re.split(r'(?=Property Code)', text)
    data = []
    
    for seg in segments:
        if "Property Code" not in seg: continue
        
        lines = [line.strip() for line in seg.split('\n') if line.strip()]
        entry = {col: 'N/A' for col in ['property_id', 'property_type', 'special_note', 'owner_name', 'owner_contact', 'area', 'address', 'sub_property_type', 'size', 'furnishing_status', 'availability', 'floor', 'tenant_preference', 'additional_details', 'age', 'rent_or_sell_price', 'deposit', 'date_stamp', 'rent_sold_out']}
        
        # 1. ID & Type
        id_match = re.search(r'Property Code\s+([A-Z0-9]+)', seg)
        if id_match: entry['property_id'] = id_match.group(1)
        entry['property_type'] = "Res_rental" if "Rent Property" in seg else "Res_resale"
        
        # 2. Owner & Contact
        owner_match = re.search(r'Owner Details:\s*\n?([^\d\n]+)\s+(\d{10})', seg)
        if owner_match:
            entry['owner_name'] = owner_match.group(1).strip()
            entry['owner_contact'] = owner_match.group(2).strip()
        
        # 3. Size & Area (Anchor point search)
        size_idx = -1
        for i, line in enumerate(lines):
            if any(x in line.lower() for x in ["super built-up area", "sqft", "sq.ft"]):
                size_idx = i
                # Config
                config = line.split('/')[0].strip()
                config = re.sub(r'(\d+)\s*Bedroom[s]?', r'\1 BHK', config, flags=re.I)
                entry['sub_property_type'] = config.split(',')[0].strip()
                # Size
                s_match = re.search(r'Area\s+([\d,\.]+)', line, re.I)
                if s_match: entry['size'] = s_match.group(1).replace(',', '') + " sq.ft"
                break
        
        if size_idx != -1 and size_idx + 1 < len(lines):
            entry['area'] = clean_area(lines[size_idx+1])
            if size_idx + 2 < len(lines):
                addr_line = lines[size_idx+2]
                if not any(x in addr_line for x in ["Rent:", "Lac", "Cr", "₹"]):
                    entry['address'] = addr_line

        # 4. Price & Deposit
        price_val = 'N/A'
        # Check Rent: label first
        rent_m = re.search(r'Rent:\s*(\d+)', seg)
        # Then check for currency symbols or Lac/Cr
        price_m = re.search(r'(?:₹|Rs\.?|)\s*(\d+(?:\.\d+)?)\s*(Lac|Cr|L|Cr\.)', seg, re.I)
        
        if rent_m: price_val = rent_m.group(1)
        elif price_m: price_val = price_m.group(0)
        entry['rent_or_sell_price'] = convert_to_numeric_price(price_val)
        
        dep_m = re.search(r'Deposite:\s*(\d+)', seg)
        if dep_m: entry['deposit'] = dep_m.group(1)

        # 5. Furnishing
        f_map = {"semi": "Semi-Furnished", "unfurnished": "Unfurnished", "fully": "Furnished", "furnished": "Furnished"}
        for k, v in f_map.items():
            if k in seg.lower():
                entry['furnishing_status'] = v
                break

        data.append(entry)
    return pd.DataFrame(data)

# STREAMLIT UI
st.set_page_config(page_title="Easy Prop Automation", layout="wide")
st.title("🏠 Property Lead Extractor v3.0")
st.markdown("Paste messages and click **Extract**. Area and Prices are now auto-formatted.")

text_input = st.text_area("Paste WhatsApp Data:", height=400)

if st.button("Extract All Leads"):
    if text_input:
        df_final = parse_leads(text_input)
        st.success(f"Total {len(df_final)} Leads Found!")
        st.dataframe(df_final)
        
        csv_data = df_final.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", data=csv_data, file_name="cleansed_leads.csv")
    else:
        st.error("Please paste some data first.")
