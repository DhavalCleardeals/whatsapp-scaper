import streamlit as st
import pandas as pd
import re

# Aapki di gayi areas ki complete list
LOCALITY_LIST = [
    "Baner", "Wakad", "Tathawade", "Punawale", "Nigdi", "Ravet", "Rahatani", "Khadki", "Kiwale", 
    "Walhekarwadi", "Morwadi", "Vikasnagar", "Mamurdi", "Wagholi", "Kharadi", "Viman Nagar", 
    "Lohegaon", "Lohgaon", "Chandan Nagar", "Koregaon Park", "Magarpatta", "Kesnand", "Mundhwa", 
    "Manjari", "manjri", "Keshavnagar", "Bakori", "Kalyani Nagar", "Wadgaon Sheri", "Vadgaon Sheri", 
    "Hadapsar", "Undri", "Undari", "NIBM", "Pisoli", "Handewadi", "Ghorpadi", "Fursungi", "saswad", 
    "Dapodi", "Kasarwadi", "Bhosari", "Moshi", "Dighi", "Alandi", "Kondhwa", "Tingre Nagar", 
    "Bhekraiwadi", "BMCC", "Peth", "Bibewadi", "Sadashiv Peth", "Narayan Peth", "Shaniwar Peth", 
    "Navi Peth", "Nana Peth", "Rasta Peth", "Bhawani Peth", "Laxmi Road", "Appa Balwant Chowk", 
    "Kasba Peth", "Ganesh Peth", "Shivajinagar", "Deccan", "Model Colony", "Gokhale Nagar", 
    "Bhosale Nagar", "Range Hills", "Prabhat Road", "FC Road", "Fergusson College Road", 
    "Agarkar Road", "Appasaheb Chiplunkar Road", "Hanuman Nagar", "Senapati Bapat Road", 
    "Parvati Peth", "Padmavati Peth", "Budhwar Peth", "Shukrawar Peth", "Raviwar Peth", 
    "Somwar Peth", "Mangalwar Peth", "Guruwar Peth", "Hinjewadi", "Aundh", "Balewadi", "Bavdhan", 
    "Sus", "Pashan", "Kothrud", "Warje", "Katraj", "Sinhgadh Road", "Sinhgad Road", "Blue Ridge", 
    "Camp", "Dhayri", "Dhayari", "Dhanori", "Gahunje", "Karvenagar", "Lodha Belmondo", "Pimple Gurav", 
    "Pimple Nilakh", "Pimple Saudagar", "Pride World City", "Vishrantwadi", "Pimpri", "Chinchwad", 
    "Bhokhel", "Khadakwasla", "Ambegaon Budruk", "Ambegaon Bk", "Ambegaon", "Shikrapur", 
    "Charholi Budruk", "Talegaon Dabhade", "Bhoirwadi", "Wadmukhwadi", "Bhugaon", "Kanhe", 
    "Dhankawadi", "Nanded", "Karandi Kh.", "Chakan", "Lonikand", "Borhade Wadi", "Bhukum", 
    "Ghotawade", "Jambhul", "Thergaon", "Mahalunge", "Sudumbre", "Kamshet", "Dudulgaon", "Charoli",
    "Hinjewadi Phase 1", "Hinjewadi Phase 2", "Hinjewadi Phase 3", "Phase 1 Hinjewadi", 
    "Phase 2 Hinjewadi", "Phase 3 Hinjewadi"
]

def extract_clean_locality(text):
    if not text or text == 'N/A': return 'N/A'
    
    # 1. Sabse pehle line mein check karein ki kya hamari list ka koi area hai
    # Badi string pehle check karenge (e.g. 'Hinjewadi Phase 1' before 'Hinjewadi')
    sorted_localities = sorted(LOCALITY_LIST, key=len, reverse=True)
    
    for area in sorted_localities:
        if area.lower() in text.lower():
            return area
            
    # 2. Agar list mein nahi mila, toh 'in ', 'at ' hatakar last word lo (fallback)
    text_clean = re.sub(r'^(in|at|the)\s+', '', text.strip(), flags=re.IGNORECASE)
    text_clean = re.sub(r',?\s*Pune|,?\s*Maharashtra|\d{6}', '', text_clean, flags=re.IGNORECASE).strip()
    
    main_part = text_clean.split(',')[0].strip()
    words = main_part.split()
    return words[-1].strip() if words else text_clean

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

def parse_leads_v11(text):
    segments = re.split(r'(?=Property Code)', text)
    data = []
    
    for seg in segments:
        if "Property Code" not in seg: continue
        lines = [line.strip() for line in seg.split('\n') if line.strip()]
        entry = {col: 'N/A' for col in ['property_id', 'property_type', 'special_note', 'owner_name', 'owner_contact', 'area', 'address', 'sub_property_type', 'size', 'furnishing_status', 'availability', 'floor', 'tenant_preference', 'additional_details', 'age', 'rent_or_sell_price', 'deposit', 'date_stamp', 'rent_sold_out']}
        
        # Date & ID
        date_m = re.search(r'(\d{2}\.\d{2}\.\d{4})', seg)
        if date_m: entry['date_stamp'] = date_m.group(1)
        entry['property_type'] = "Res_rental" if "Rent Property" in seg else "Res_resale"
        id_m = re.search(r'Property Code\s+([A-Z0-9]+)', seg)
        if id_m: entry['property_id'] = id_m.group(1)
        
        # Owner
        owner_m = re.search(r'Owner Details:\s*\n?([^\d\n]+)\s+(\d{10})', seg)
        if owner_m:
            entry['owner_name'] = owner_m.group(1).strip()
            entry['owner_contact'] = owner_m.group(2).strip()

        # Size Line
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
        
        # AREA EXTRACTION
        if size_idx != -1 and size_idx + 1 < len(lines):
            area_raw = lines[size_idx+1]
            entry['area'] = extract_clean_locality(area_raw)
            
            # Address
            if size_idx + 2 < len(lines):
                addr_line = lines[size_idx+2]
                if not any(x in addr_line for x in ["Rent:", "Lac", "Cr", "₹", "L "]):
                    entry['address'] = addr_line.strip()

        # Price
        price_val = 'N/A'
        rent_m = re.search(r'Rent:\s*(\d+)', seg)
        price_m = re.search(r'(?:₹|Rs\.?|)\s*(\d+(?:\.\d+)?)\s*(Lac|Cr|L|Cr\.)', seg, re.I)
        if rent_m: price_val = rent_m.group(1)
        elif price_m: price_val = price_m.group(0)
        entry['rent_or_sell_price'] = convert_to_numeric_price(price_val)
        
        # Furnishing
        if "semi" in seg.lower(): entry['furnishing_status'] = "Semi-Furnished"
        elif "unfurnished" in seg.lower(): entry['furnishing_status'] = "Unfurnished"
        elif "fully" in seg.lower() or "furnished" in seg.lower(): entry['furnishing_status'] = "Furnished"

        data.append(entry)
    return pd.DataFrame(data)

st.set_page_config(page_title="EasyProp v11", layout="wide")
st.title("🏡 Property Lead Extractor (Full Pune Areas)")
st.info("Ab ye tool aapke diye gaye 200+ Pune areas ko priority dega.")
input_text = st.text_area("Paste Data:", height=400)
if st.button("Extract Data"):
    if input_text:
        df = parse_leads_v11(input_text)
        st.dataframe(df)
        st.download_button("Download CSV", df.to_csv(index=False).encode('utf-8'), "property_leads_v11.csv")
