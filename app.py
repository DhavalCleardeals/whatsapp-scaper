import streamlit as st
import pandas as pd
import re

def get_pure_area(text):
    if not text or text == 'N/A': return 'N/A'
    
    # Sirf City aur State ko hatayein jo har message mein common hote hain
    # Iske alawa hum kuch bhi "masala" (Society, Project etc.) delete nahi karenge
    noise = [r',?\s*Pune', r',?\s*Maharashtra', r',?\s*India', r'\d{6}']
    clean_text = text
    for n in noise:
        clean_text = re.sub(n, '', clean_text, flags=re.IGNORECASE)
    
    # Shuruat mein agar 'in ' ya 'at ' likha hai toh bas wo hatayein
    clean_text = re.sub(r'^(in|at)\s+', '', clean_text.strip(), flags=re.IGNORECASE)
    
    return clean_text.strip().strip(',')

def convert_to_numeric_price(price_str):
    if price_str == 'N/A' or not price_str: return 'N/A'
    p = str(price_str).replace('₹', '').replace(',', '').replace('Rs', '').strip()
    match = re.search(r'(\d+(?:\.\d+)?)\s*(Lac|Cr|L|Cr\.)?', p, re.IGNORECASE)
    if not match: return 'N/A'
    value = float(match.group(1))
    unit = match.group(2).lower() if match.group(2) else ''
    if unit in ['lac', 'l']: return int(value * 100000)
    elif unit in ['cr', 'cr.']: return int(value * 10000000)
    else: return int(value)

def parse_leads_strict(text):
    segments = re.split(r'(?=Property Code)', text)
    data = []
    
    for seg in segments:
        if "Property Code" not in seg: continue
        lines = [line.strip() for line in seg.split('\n') if line.strip()]
        entry = {col: 'N/A' for col in ['property_id', 'property_type', 'special_note', 'owner_name', 'owner_contact', 'area', 'address', 'sub_property_type', 'size', 'furnishing_status', 'availability', 'floor', 'tenant_preference', 'additional_details', 'age', 'rent_or_sell_price', 'deposit', 'date_stamp', 'rent_sold_out']}
        
        # ID, Type, Date
        date_m = re.search(r'(\d{2}\.\d{2}\.\d{4})', seg)
        if date_m: entry['date_stamp'] = date_m.group(1)
        entry['property_type'] = "Res_rental" if "Rent Property" in seg else "Res_resale"
        id_m = re.search(r'Property Code\s+([A-Z0-9]+)', seg)
        if id_m: entry['property_id'] = id_m.group(1)
        
        # Owner & Contact
        owner_m = re.search(r'Owner Details:\s*\n?([^\d\n]+)\s+(\d{10})', seg)
        if owner_m:
            entry['owner_name'] = owner_m.group(1).strip()
            entry['owner_contact'] = owner_m.group(2).strip()

        # Find Size Line to locate Area
        size_idx = -1
        for i, line in enumerate(lines):
            if any(x in line.lower() for x in ["super built-up area", "sqft", "sq.ft", "carpet area"]):
                size_idx = i
                config = line.split('/')[0].strip()
                config = re.sub(r'(\d+)\s*Bedroom[s]?', r'\1 BHK', config, flags=re.I)
                entry['sub_property_type'] = config.split(',')[0].strip()
                s_m = re.search(r'Area\s+([\d,\.]+)', line, re.I)
                if s_m: entry['size'] = s_m.group(1).replace(',', '') + " sq.ft"
                break
        
        # STRICT AREA PICKUP
        if size_idx != -1 and size_idx + 1 < len(lines):
            area_raw = lines[size_idx+1]
            # Bas basic cleaning, koi extra filter nahi
            entry['area'] = get_pure_area(area_raw)
            
            # Address (Next line)
            if size_idx + 2 < len(lines):
                addr_candidate = lines[size_idx+2]
                if not any(x in addr_candidate for x in ["Rent:", "Lac", "Cr", "₹", "L "]):
                    entry['address'] = addr_candidate

        # Price Conversion
        price_val = 'N/A'
        rent_m = re.search(r'Rent:\s*(\d+)', seg)
        price_m = re.search(r'(?:₹|Rs\.?|)\s*(\d+(?:\.\d+)?)\s*(Lac|Cr|L|Cr\.)', seg, re.I)
        if rent_m: price_val = rent_m.group(1)
        elif price_m: price_val = price_m.group(0)
        entry['rent_or_sell_price'] = convert_to_numeric_price(price_val)
        
        # Deposit & Furnishing
        dep_m = re.search(r'Deposite:\s*(\d+)', seg)
        if dep_m: entry['deposit'] = dep_m.group(1)
        if "semi" in seg.lower(): entry['furnishing_status'] = "Semi-Furnished"
        elif "unfurnished" in seg.lower(): entry['furnishing_status'] = "Unfurnished"
        elif "fully" in seg.lower() or "furnished" in seg.lower(): entry['furnishing_status'] = "Furnished"

        data.append(entry)
    return pd.DataFrame(data)

# STREAMLIT UI
st.set_page_config(page_title="EasyProp Strict", layout="wide")
st.title("🎯 Property Lead Converter (Strict Mode)")
st.write("Ab Area as-it-is extract hoga, bina kisi extra badlav ke.")

input_text = st.text_area("Paste WhatsApp Data Here:", height=400)
if st.button("Extract Raw Data"):
    if input_text:
        df = parse_leads_strict(input_text)
        st.success(f"Processed {len(df)} leads.")
        st.dataframe(df)
        st.download_button("Download CSV", df.to_csv(index=False).encode('utf-8'), "strict_leads.csv")
