import streamlit as st
import pandas as pd
import re

def clean_only_area(text):
    if not text or text == 'N/A': return 'N/A'
    # Step 1: Remove common noise
    text = re.sub(r',?\s*\bPune\b|,?\s*\bMaharashtra\b|,?\s*\bIndia\b|\bBudruk\b|\bKhurd\b|\d{6}', '', text, flags=re.IGNORECASE).strip()
    # Step 2: Excel sheet ke mutabiq sirf main Locality rakhni hai
    # Agar line mein comma hai "Indira Nagar, Undri", toh aakhri word main area hai
    parts = [p.strip() for p in text.split(',') if p.strip()]
    if len(parts) > 1:
        return parts[-1]
    # Agar single word hai aur building/project keyword hai, toh use saaf karein
    clean_val = re.sub(r'Society|Apartment|Heights|Residency|Villa|Complex|Garden|Park|Vihar|Phase\s?\d+|Project', '', parts[0], flags=re.IGNORECASE).strip()
    return clean_val if clean_val else parts[0]

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

def parse_leads_final(text):
    segments = re.split(r'(?=Property Code)', text)
    data = []
    
    for seg in segments:
        if "Property Code" not in seg: continue
        lines = [line.strip() for line in seg.split('\n') if line.strip()]
        entry = {col: 'N/A' for col in ['property_id', 'property_type', 'special_note', 'owner_name', 'owner_contact', 'area', 'address', 'sub_property_type', 'size', 'furnishing_status', 'availability', 'floor', 'tenant_preference', 'additional_details', 'age', 'rent_or_sell_price', 'deposit', 'date_stamp', 'rent_sold_out']}
        
        # 1. Basic Identity
        date_m = re.search(r'(\d{2}\.\d{2}\.\d{4})', seg)
        if date_m: entry['date_stamp'] = date_m.group(1)
        entry['property_type'] = "Res_rental" if "Rent Property" in seg else "Res_resale"
        id_m = re.search(r'Property Code\s+([A-Z0-9]+)', seg)
        if id_m: entry['property_id'] = id_m.group(1)
        
        # 2. Owner Details
        owner_m = re.search(r'Owner Details:\s*\n?([^\d\n]+)\s+(\d{10})', seg)
        if owner_m:
            entry['owner_name'] = owner_m.group(1).strip()
            entry['owner_contact'] = owner_m.group(2).strip()

        # 3. Locate Size Line for Area/Address
        size_idx = -1
        for i, line in enumerate(lines):
            if any(x in line.lower() for x in ["super built-up area", "sqft", "sq.ft"]):
                size_idx = i
                config = line.split('/')[0].strip()
                config = re.sub(r'(\d+)\s*Bedroom[s]?', r'\1 BHK', config, flags=re.I)
                entry['sub_property_type'] = config.split(',')[0].strip()
                s_m = re.search(r'Area\s+([\d,\.]+)', line, re.I)
                if s_m: entry['size'] = s_m.group(1).replace(',', '') + " sq.ft"
                break
        
        # 4. Area vs Address (Excel logic)
        if size_idx != -1 and size_idx + 1 < len(lines):
            # Area line (Strict Cleaning)
            entry['area'] = clean_only_area(lines[size_idx+1])
            
            # Address line (Puri line as it is)
            if size_idx + 2 < len(lines):
                addr_line = lines[size_idx+2]
                if not any(x in addr_line for x in ["Rent:", "Lac", "Cr", "₹", "L "]):
                    entry['address'] = addr_line.replace(', Pune', '').strip()

        # 5. Price Conversion
        price_val = 'N/A'
        rent_m = re.search(r'Rent:\s*(\d+)', seg)
        price_m = re.search(r'(?:₹|Rs\.?|)\s*(\d+(?:\.\d+)?)\s*(Lac|Cr|L|Cr\.)', seg, re.I)
        if rent_m: price_val = rent_m.group(1)
        elif price_m: price_val = price_m.group(0)
        entry['rent_or_sell_price'] = convert_to_numeric_price(price_val)
        
        # 6. Furnishing
        if "semi" in seg.lower(): entry['furnishing_status'] = "Semi-Furnished"
        elif "unfurnished" in seg.lower(): entry['furnishing_status'] = "Unfurnished"
        elif "fully" in seg.lower() or "furnished" in seg.lower(): entry['furnishing_status'] = "Furnished"

        data.append(entry)
    return pd.DataFrame(data)

st.set_page_config(page_title="Cleardeals Final", layout="wide")
st.title("🎯 Property Extractor (Final Excel Format)")
input_text = st.text_area("Paste Data:", height=400)
if st.button("Generate Excel Data"):
    if input_text:
        df = parse_leads_final(input_text)
        st.dataframe(df)
        st.download_button("Download CSV", df.to_csv(index=False).encode('utf-8'), "leads_final.csv")
