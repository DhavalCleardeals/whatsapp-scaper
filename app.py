import streamlit as st
import pandas as pd
import re

def clean_area_dynamically(text):
    if not text or text == 'N/A': return 'N/A'
    
    # 1. Sirf City aur State level ka kachra saaf karein
    # Pune, Maharashtra, India, Budruk, Khurd, Pin codes hatayein
    text = re.sub(r',?\s*\bPune\b|,?\s*\bMaharashtra\b|,?\s*\bIndia\b|\bBudruk\b|\bKhurd\b|\d{6}', '', text, flags=re.IGNORECASE).strip()
    
    # 2. Shuruat ke 'in ' ya 'at ' hatayein
    text = re.sub(r'^(in|at)\s+', '', text, flags=re.IGNORECASE).strip()
    
    # 3. Agar abhi bhi comma bacha hai aakhri mein, use hatayein
    text = text.strip(',')
    
    return text.strip() if text else 'N/A'

def convert_to_numeric_price(price_str):
    if price_str == 'N/A' or not price_str: return 'N/A'
    
    # Currency symbols aur commas hatayein
    p = str(price_str).replace('₹', '').replace(',', '').replace('Rs', '').strip()
    
    # Number aur Unit (Lac, Cr, L) dhundo
    match = re.search(r'(\d+(?:\.\d+)?)\s*(Lac|Cr|L|Cr\.)?', p, re.IGNORECASE)
    if not match: return 'N/A'
    
    value = float(match.group(1))
    unit = match.group(2).lower() if match.group(2) else ''
    
    if unit in ['lac', 'l']:
        return int(value * 100000)
    elif unit in ['cr', 'cr.']:
        return int(value * 10000000)
    else:
        return int(value) # Normal rent ke liye

def parse_property_leads(text):
    # Message split karein "Property Code" ke hisaab se
    segments = re.split(r'(?=Property Code)', text)
    data = []
    
    for seg in segments:
        if "Property Code" not in seg: continue
        
        lines = [line.strip() for line in seg.split('\n') if line.strip()]
        entry = {col: 'N/A' for col in ['property_id', 'property_type', 'special_note', 'owner_name', 'owner_contact', 'area', 'address', 'sub_property_type', 'size', 'furnishing_status', 'availability', 'floor', 'tenant_preference', 'additional_details', 'age', 'rent_or_sell_price', 'deposit', 'date_stamp', 'rent_sold_out']}
        
        # 1. Basic Info
        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', seg)
        if date_match: entry['date_stamp'] = date_match.group(1)
        entry['property_type'] = "Res_rental" if "Rent Property" in seg else "Res_resale"
        
        id_match = re.search(r'Property Code\s+([A-Z0-9]+)', seg)
        if id_match: entry['property_id'] = id_match.group(1)
        
        # 2. Owner & Contact
        owner_match = re.search(r'Owner Details:\s*\n?([^\d\n]+)\s+(\d{10})', seg)
        if owner_match:
            entry['owner_name'] = owner_match.group(1).strip()
            entry['owner_contact'] = owner_match.group(2).strip()

        # 3. Size & Location detection (Structure base)
        size_idx = -1
        for i, line in enumerate(lines):
            if any(x in line.lower() for x in ["super built-up area", "sqft", "sq.ft", "carpet area"]):
                size_idx = i
                # Configuration (1 Bedroom -> 1 BHK)
                config = line.split('/')[0].strip()
                config = re.sub(r'(\d+)\s*Bedroom[s]?', r'\1 BHK', config, flags=re.I)
                entry['sub_property_type'] = config.split(',')[0].strip()
                # Size
                s_match = re.search(r'Area\s+([\d,\.]+)', line, re.I)
                if s_match: entry['size'] = s_match.group(1).replace(',', '') + " sq.ft"
                break
        
        # DYNAMIC AREA EXTRACTION
        if size_idx != -1 and size_idx + 1 < len(lines):
            area_line = lines[size_idx+1]
            entry['area'] = clean_area_dynamically(area_line)
            
            # Address (Agar uske niche ek aur line hai jo price nahi hai)
            if size_idx + 2 < len(lines):
                addr_line = lines[size_idx+2]
                if not any(x in addr_line for x in ["Rent:", "Lac", "Cr", "₹", "L "]):
                    entry['address'] = addr_line

        # 4. Numeric Price Extraction
        price_found = 'N/A'
        rent_m = re.search(r'Rent:\s*(\d+)', seg)
        # Regex for all price types: ₹53 Lac, 30.0 L, 1.74 Cr
        price_m = re.search(r'(?:₹|Rs\.?|)\s*(\d+(?:\.\d+)?)\s*(Lac|Cr|L|Cr\.)', seg, re.I)
        
        if rent_m: price_found = rent_m.group(1)
        elif price_m: price_found = price_m.group(0)
        
        entry['rent_or_sell_price'] = convert_to_numeric_price(price_found)
        
        # 5. Deposit & Furnishing
        dep_m = re.search(r'Deposite:\s*(\d+)', seg)
        if dep_m: entry['deposit'] = dep_m.group(1)

        if "semi" in seg.lower(): entry['furnishing_status'] = "Semi-Furnished"
        elif "unfurnished" in seg.lower(): entry['furnishing_status'] = "Unfurnished"
        elif "fully" in seg.lower() or "furnished" in seg.lower(): entry['furnishing_status'] = "Furnished"

        data.append(entry)
    
    return pd.DataFrame(data)

# STREAMLIT UI
st.set_page_config(page_title="EasyProp Unlimited", layout="wide")
st.title("📊 Real-Time Property Lead Converter")
st.markdown("Paste messages and get exact data. **No static area limits.**")

input_text = st.text_area("Paste WhatsApp Data Here:", height=400)

if st.button("Extract Real Data"):
    if input_text:
        df = parse_property_leads(input_text)
        st.success(f"Successfully processed {len(df)} leads.")
        st.dataframe(df)
        
        # Download
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV File", data=csv, file_name="property_leads_real.csv", mime="text/csv")
    else:
        st.error("Please paste data first!")
