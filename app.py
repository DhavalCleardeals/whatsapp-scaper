import streamlit as st
import pandas as pd
import re

def clean_dynamic_area(text):
    if not text or text == 'N/A': return 'N/A'
    
    # 1. Sabse pehle city aur state noise hatayein
    text = re.sub(r'\bin\b|\bat\b|\bPune\b|\bMaharashtra\b|\bBudruk\b|\bKhurd\b|\bIndia\b|\d{6}', '', text, flags=re.IGNORECASE).strip()
    
    # 2. Agar multiple commas hain, toh aakhri wala hissa aksar main Area hota hai
    # Example: "Indira Nagar, Undri" -> Undri
    parts = [p.strip() for p in text.split(',') if p.strip()]
    if parts:
        candidate = parts[-1]
        # Building keywords ko hatayein (agar akele bache hon)
        candidate = re.sub(r'Society|Apartment|Heights|Residency|Villa|Complex|Garden|Park|Vihar|Phase\s?\d+|Project', '', candidate, flags=re.IGNORECASE).strip()
        return candidate
    
    return text

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

def parse_leads_unlimited(text):
    # Property Code ko anchor banakar split karein
    segments = re.split(r'(?=Property Code)', text)
    data = []
    
    for seg in segments:
        if "Property Code" not in seg: continue
        lines = [line.strip() for line in seg.split('\n') if line.strip()]
        entry = {col: 'N/A' for col in ['property_id', 'property_type', 'special_note', 'owner_name', 'owner_contact', 'area', 'address', 'sub_property_type', 'size', 'furnishing_status', 'availability', 'floor', 'tenant_preference', 'additional_details', 'age', 'rent_or_sell_price', 'deposit', 'date_stamp', 'rent_sold_out']}
        
        # Date & Basic Info
        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', seg)
        if date_match: entry['date_stamp'] = date_match.group(1)
        entry['property_type'] = "Res_rental" if "Rent Property" in seg else "Res_resale"
        
        id_match = re.search(r'Property Code\s+([A-Z0-9]+)', seg)
        if id_match: entry['property_id'] = id_match.group(1)
        
        # Owner & Contact
        owner_match = re.search(r'Owner Details:\s*\n?([^\d\n]+)\s+(\d{10})', seg)
        if owner_match:
            entry['owner_name'] = owner_match.group(1).strip()
            entry['owner_contact'] = owner_match.group(2).strip()
        
        # Configuration & Location Line detection
        size_idx = -1
        for i, line in enumerate(lines):
            if any(x in line.lower() for x in ["super built-up area", "sqft", "sq.ft", "carpet area"]):
                size_idx = i
                # Config Clean
                config = line.split('/')[0].strip()
                config = re.sub(r'(\d+)\s*Bedroom[s]?', r'\1 BHK', config, flags=re.I)
                entry['sub_property_type'] = config.split(',')[0].strip()
                # Size Clean
                s_match = re.search(r'Area\s+([\d,\.]+)', line, re.I)
                if s_match: entry['size'] = s_match.group(1).replace(',', '') + " sq.ft"
                break
        
        # AREA EXTRACTION (The Dynamic Part)
        if size_idx != -1 and size_idx + 1 < len(lines):
            area_line = lines[size_idx+1]
            entry['area'] = clean_dynamic_area(area_line)
            
            # Address line
            if size_idx + 2 < len(lines):
                addr_line = lines[size_idx+2]
                if not any(x in addr_line for x in ["Rent:", "Lac", "Cr", "₹", "L "]):
                    entry['address'] = addr_line

        # Numeric Price
        price_found = 'N/A'
        rent_m = re.search(r'Rent:\s*(\d+)', seg)
        price_m = re.search(r'(?:₹|Rs\.?|)\s*(\d+(?:\.\d+)?)\s*(Lac|Cr|L|Cr\.)', seg, re.I)
        if rent_m: price_found = rent_m.group(1)
        elif price_m: price_found = price_m.group(0)
        entry['rent_or_sell_price'] = convert_to_numeric_price(price_found)
        
        # Deposit
        dep_m = re.search(r'Deposite:\s*(\d+)', seg)
        if dep_m: entry['deposit'] = dep_m.group(1)

        # Furnishing
        f_map = {"semi": "Semi-Furnished", "unfurnished": "Unfurnished", "fully": "Furnished", "furnished": "Furnished"}
        for k, v in f_map.items():
            if k in seg.lower():
                entry['furnishing_status'] = v
                break

        data.append(entry)
    return pd.DataFrame(data)

# STREAMLIT UI
st.set_page_config(page_title="EasyProp Unlimited", layout="wide")
st.title("🚀 Property Lead Converter (No Area Limits)")
st.write("Ab ye Pune ke kisi bhi naye area ko message structure ke hisaab se pehchan lega.")

text_input = st.text_area("Paste WhatsApp Data Here:", height=400)
if st.button("Extract Data"):
    if text_input:
        df = parse_leads_unlimited(text_input)
        st.success(f"Successfully processed {len(df)} leads.")
        st.dataframe(df)
        st.download_button("Download CSV", df.to_csv(index=False).encode('utf-8'), "property_leads.csv")
