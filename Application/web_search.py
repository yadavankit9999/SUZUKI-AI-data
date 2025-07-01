import streamlit as st
import os
import pandas as pd
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
import importlib.util
import re
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics.pairwise import cosine_similarity

# --- Feature Engineering (same as model_similarity.py) ---
def extract_number(text):
    text = str(text).replace(",", "")
    match = re.findall(r"[\d.]+", text)
    return float(match[0]) if match else None

def parse_bore_stroke(text):
    text = str(text).replace(",", "")
    match = re.findall(r"([\d.]+)", text)
    if len(match) >= 2:
        return float(match[0]), float(match[1])
    return None, None

def clean_power(text):
    text = str(text).replace(",", "")
    match = re.findall(r"[\d.]+", text)
    return float(match[0]) if match else None

def clean_torque(text):
    text = str(text).replace(",", "")
    match = re.findall(r"[\d.]+", text)
    return float(match[0]) if match else None

# --- Model Similarity Logic ---
def get_top_matches_for_new_model(fetched_data, top_n=5, CSV_PATH=os.path.join(os.path.dirname(__file__), "Model.csv")):
    df = pd.read_csv(CSV_PATH)
    # Add the fetched model as a new row (in memory only)
    row_to_add = {k: (json.dumps(v) if isinstance(v, list) else v) for k, v in fetched_data.items()}
    df = pd.concat([df, pd.DataFrame([row_to_add])], ignore_index=True)
    # --- Feature engineering for all rows ---
    df["Compression Ratio"] = df["Compression Ratio"].apply(extract_number)
    df["Power (PS)"] = df["Maximum Power"].apply(clean_power)
    df["Torque (Nm)"] = df["Maximum Torque"].apply(clean_torque)
    df[["Bore (mm)", "Stroke (mm)"]] = df["Bore X Stroke (mm)"].apply(lambda x: pd.Series(parse_bore_stroke(x)))
    df["Front Brake Size (mm)"] = df["Front Brake Size"] .apply(extract_number)
    df["Rear Brake Size (mm)"] = df["Rear Brake Size"] .apply(extract_number)
    numerical_features = [
        "Displacement (cc)", "Compression Ratio", "Power (PS)", "Torque (Nm)",
        "Bore (mm)", "Stroke (mm)", "Kerb Weight (kg)", "Fuel Tank Capacity (L)",
        "Wheelbase (mm)", "Seat Height (mm)", "Front Brake Size (mm)", "Rear Brake Size (mm)"
    ]
    categorical_features = [
        "Engine Layout", "Gear Box", "Final Drive", "Front Suspension", "Rear Suspension",
        "ABS", "Seat Type", "Wheels", "Headlamp", "Instrument Display"
    ]
    for col in numerical_features:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    for col in categorical_features:
        df[col] = df[col].fillna("")
    # Numeric
    numeric_imputer = SimpleImputer(strategy="mean")
    X_num = numeric_imputer.fit_transform(df[numerical_features])
    scaler = StandardScaler()
    X_num_scaled = scaler.fit_transform(X_num)
    # Label encode categorical
    label_encoders = {}
    X_cat = np.zeros((df.shape[0], len(categorical_features)), dtype=int)
    for i, col in enumerate(categorical_features):
        le = LabelEncoder()
        X_cat[:, i] = le.fit_transform(df[col].astype(str))
        label_encoders[col] = le
    # Custom similarity: treat numerical features within ±1% as perfect match
    model_name = fetched_data.get("Models", "")
    reference_idx = df.index[df["Models"] == model_name].tolist()
    if not reference_idx:
        return []
    reference_idx = reference_idx[0]
    ref_num = X_num[reference_idx]
    ref_num_scaled = X_num_scaled[reference_idx]
    sims = []
    for i in range(X_num.shape[0]):
        candidate_num = X_num[i]
        candidate_num_scaled = X_num_scaled[i].copy()
        for j in range(len(numerical_features)):
            ref_val = ref_num[j]
            cand_val = candidate_num[j]
            if np.isnan(ref_val) or np.isnan(cand_val):
                continue
            if ref_val == 0:
                continue
            if abs(cand_val - ref_val) / abs(ref_val) <= 0.01:
                candidate_num_scaled[j] = ref_num_scaled[j]
        vec = np.hstack([candidate_num_scaled, X_cat[i]])
        ref_vec = np.hstack([ref_num_scaled, X_cat[reference_idx]])
        sim = cosine_similarity([ref_vec], [vec])[0, 0]
        sims.append(sim)
    similarity_df = pd.Series(sims, index=df["Models"])
    similarity_df = similarity_df.drop(model_name)
    return similarity_df.sort_values(ascending=False).head(top_n).index.tolist()

def main():
    # Load environment
    load_dotenv()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # Gemini setup
    client = genai.Client(api_key=GEMINI_API_KEY)
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    config = types.GenerateContentConfig(tools=[grounding_tool])

    # Model CSV path
    CSV_PATH = os.path.join(os.path.dirname(__file__), "Model.csv")

    st.set_page_config(page_title="Model Data Fetching (Web search)", layout="wide")
    st.title("Model Data Fetching (Web search)")

    use_hardcoded = st.checkbox("Use hardcoded AI response (for testing)")

    # --- User Input ---
    with st.form("fetch_form"):
        model = st.text_input("Model", "Royal Enfield Super Meteor 650")
        variant = st.text_input("Variant", "Super Meteor 650")
        submitted = st.form_submit_button("Fetch Data from Web")

    fetched_data = None
    if submitted:
        if use_hardcoded:
            # Use the hardcoded JSON response
            fetched_data = {
                "Models": "Royal Enfield Classic 650",
                "Variant": "Classic 650",
                "Ex-Showroom Price INR": [
                    "Hotrod (Bruntingthorpe Blue) - 3,37,000",
                    "Hotrod (Vallam Red) - 3,37,000",
                    "Classic (Teal) - 3,41,000",
                    "Chrome (Black Chrome) - 3,50,000"
                ],
                "Bharat Stage": "BS6 Phase 2B",
                "FI/Carburettor": "Fuel Injection",
                "Displacement (cc)": 647.95,
                "Engine Layout": "Inline Twin Cylinder",
                "Head Cam Layout": "SOHC",
                "Valve Type": "4 Valves Per Cylinder",
                "Engine Cool Type": "Air/Oil-Cooled",
                "Compression Ratio": "9.5:1",
                "Bore X Stroke (mm)": "78 x 67.8",
                "Maximum Power": "46.39 bhp @ 7250 rpm",
                "Maximum Torque": "52.3 Nm @ 5650 rpm",
                "Final Drive": "Chain",
                "Gear Box": "6 Speed Constant Mesh",
                "Length (mm)": 2318,
                "Width (mm)": 892,
                "Height (mm)": 1137,
                "Wheelbase (mm)": 1475,
                "Ground Clearence (mm)": 154,
                "Seat Height (mm)": 800,
                "Seat Type": "Single, with optional removable pillion",
                "Kerb Weight (kg)": 243,
                "Fuel Tank Capacity (L)": 14.8,
                "Front Tyre Size": "100/90-19",
                "Rear Tyre Size": "140/70 R18",
                "Wheels": "Spoked",
                "Front Suspension": "Telescopic Fork 43 mm (Showa)",
                "Fork Diameter": 43,
                "Adjustable Front Suspension": "No",
                "Front Suspension Stroke": 120,
                "Rear Suspension": "Twin Shock (Showa)",
                "Adjustable Rear Suspension": "Yes (Preload Adjustable)",
                "Rear Suspension Stroke": 90,
                "Front Brake Size": 320,
                "Rear Brake Size": 300,
                "ABS": "Dual Channel",
                "Switachable ABS": "NA",
                "Cornering ABS": "No",
                "Traction Control": "No",
                "Switachable Traction control": "NA",
                "Ride by Wire": "NA",
                "Riding Mode": "No",
                "Steering Stabiliser": "NA",
                "Cruise Control": "NA",
                "Slipper clutch": "Yes",
                "Quickshifter": "No",
                "Day Time Running Lamp (DRL)": "LED",
                "Headlamp": "LED",
                "Taillamp": "LED",
                "Indicators": "LED",
                "Instrument Display": "Digi-Analog (Speedometer, LCD inset for fuel level, tripmeter, gear position indicator) with Tripper Navigation pod",
                "Connected Features": "Tripper Navigation, USB Charging Port",
                "GPS Navigation": "Yes",
                "Starting System": "Electric Start",
                "Silent Start": "NA",
                "Idle Start Stop": "NA",
                "Windshiled": "NA",
                "Adjustable Windshield": "NA",
                "Rear Luggage rack": "Optional, via removable subframe",
                "Rear Luggage rack (Capacity)": "NA",
                "Under Engine Cowling": "NA",
                "Side stand Indicator": "Yes",
                "Side stand Inhibitor": "Yes",
                "Engine Kill Switch": "NA",
                "Pass Switch": "Yes",
                "Hazard lamps": "Yes",
                "USB /Charging Socket": "Yes",
                "Colors": [
                    "Black Chrome",
                    "Bruntingthorpe Blue",
                    "Vallam Red",
                    "Teal"
                ]
            }
            print("\n[Gemini AI JSON Response]\n", json.dumps(fetched_data, indent=2, ensure_ascii=False))
        else:
            with st.spinner("Fetching data from Gemini..."):
                prompt = f"""
Return the following motorcycle's full specification as a JSON object with all the following keys (even if some values are missing, keep the key with value as 'NA').
Model: {model}
Variant: {variant}

For 'Ex-Showroom Price INR', return a list of all available prices for all variants/colors, e.g. ["Astral - 3,63,123", "Interstellar Grey - 3,79,123 (DT)", ...]. If only one price is available, return it as a single-item list.

Keys: [Models, Variant, Ex-Showroom Price INR, Bharat Stage , FI/Carburettor, Displacement (cc), Engine Layout, Head Cam Layout, Valve Type, Engine Cool Type, Compression Ratio, Bore X Stroke (mm), Maximum Power, Maximum Torque, Final Drive , Gear Box, Length (mm), Width (mm), Height (mm), Wheelbase (mm), Ground Clearence (mm), Seat Height (mm), Seat Type , Kerb Weight (kg), Fuel Tank Capacity (L), Front Tyre Size, Rear Tyre Size, Wheels, Front Suspension, Fork Diameter, Adjustable Front Suspension, Front Suspension Stroke , Rear Suspension, Adjustable Rear Suspension, Rear Suspension Stroke, Front Brake Size , Rear Brake Size , ABS, Switachable ABS , Cornering ABS, Traction Control , Switachable Traction control, Ride by Wire, Riding Mode, Steering Stabiliser , Cruise Control, Slipper clutch , Quickshifter , Day Time Running Lamp (DRL), Headlamp,  Taillamp, Indicators , Instrument Display, Connected Features , GPS Navigation, Starting System, Silent Start , Idle Start Stop, Windshiled, Adjustable Windshield, Rear Luggage rack, Rear Luggage rack (Capacity), Under Engine Cowling, Side stand Indicator , Side stand Inhibitor, Engine Kill Switch, Pass Switch , Hazard lamps , USB /Charging Socket, Colors]

Return only the JSON object, no explanation. If a value is a list, return as a JSON array.
"""
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=config,
                )
                # Try to extract JSON from response
                try:
                    text = response.text
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    json_str = text[start:end]
                    fetched_data = json.loads(json_str)
                    print("\n[Gemini AI JSON Response]\n", json.dumps(fetched_data, indent=2, ensure_ascii=False))
                    # --- Post-process Ex-Showroom Price INR ---
                    price_val = fetched_data.get("Ex-Showroom Price INR", "NA")
                    if not isinstance(price_val, list):
                        # Try to split by newlines, semicolons, or commas
                        if isinstance(price_val, str):
                            if "\n" in price_val:
                                fetched_data["Ex-Showroom Price INR"] = [x.strip() for x in price_val.split("\n") if x.strip()]
                            elif ";" in price_val:
                                fetched_data["Ex-Showroom Price INR"] = [x.strip() for x in price_val.split(";") if x.strip()]
                            elif "," in price_val and len(price_val.split(",")) > 1:
                                fetched_data["Ex-Showroom Price INR"] = [x.strip() for x in price_val.split(",") if x.strip()]
                            else:
                                fetched_data["Ex-Showroom Price INR"] = [price_val]
                        else:
                            fetched_data["Ex-Showroom Price INR"] = [str(price_val)]
                except Exception as e:
                    st.error(f"Could not parse JSON from Gemini response: {e}")
                    fetched_data = None
        # Store in session state
        st.session_state['fetched_data'] = fetched_data
        # Get top matches and store in session state
        if fetched_data:
            st.session_state['top_matches'] = get_top_matches_for_new_model(fetched_data, top_n=5, CSV_PATH=CSV_PATH)
        else:
            st.session_state['top_matches'] = []

    # Use session state for persistence
    fetched_data = st.session_state.get('fetched_data', None)
    top_matches = st.session_state.get('top_matches', [])

    # --- Display Table and Add Option ---
    if fetched_data:
        st.success("Fetched data for model: " + fetched_data.get("Models", model))
        # Load Model.csv for comparison
        df = pd.read_csv(CSV_PATH)
        # Prepare columns: fetched model + top 5 matches
        models_to_show = [fetched_data.get("Models", model)] + top_matches
        # Build a list of dicts for each model
        model_dicts = []
        # Fetched model (from fetched_data)
        model_dicts.append(fetched_data)
        # Top 5 matches (from Model.csv)
        for m in top_matches:
            row = df[df["Models"] == m]
            if not row.empty:
                model_dicts.append(row.iloc[0].to_dict())
            else:
                model_dicts.append({})
        # Get all unique fields
        FIELD_ORDER = [
            "Models", "Variant", "Ex-Showroom Price INR", "Bharat Stage", "FI/Carburettor", "Displacement (cc)", "Engine Layout", "Head Cam Layout", "Valve Type", "Engine Cool Type", "Compression Ratio", "Bore X Stroke (mm)", "Maximum Power", "Maximum Torque", "Final Drive", "Gear Box", "Length (mm)", "Width (mm)", "Height (mm)", "Wheelbase (mm)", "Ground Clearence (mm)", "Seat Height (mm)", "Seat Type", "Kerb Weight (kg)", "Fuel Tank Capacity (L)", "Front Tyre Size", "Rear Tyre Size", "Wheels", "Front Suspension", "Fork Diameter", "Adjustable Front Suspension", "Front Suspension Stroke", "Rear Suspension", "Adjustable Rear Suspension", "Rear Suspension Stroke", "Front Brake Size", "Rear Brake Size", "ABS", "Switachable ABS", "Cornering ABS", "Traction Control", "Switachable Traction control", "Ride by Wire", "Riding Mode", "Steering Stabiliser", "Cruise Control", "Slipper clutch", "Quickshifter", "Day Time Running Lamp (DRL)", "Headlamp", "Taillamp", "Indicators", "Instrument Display", "Connected Features", "GPS Navigation", "Starting System", "Silent Start", "Idle Start Stop", "Windshiled", "Adjustable Windshield", "Rear Luggage rack", "Rear Luggage rack (Capacity)", "Under Engine Cowling", "Side stand Indicator", "Side stand Inhibitor", "Engine Kill Switch", "Pass Switch", "Hazard lamps", "USB /Charging Socket", "Colors"
        ]
        # Add any extra fields not in FIELD_ORDER at the end
        all_fields = set()
        for d in model_dicts:
            all_fields.update(d.keys())
        extra_fields = [f for f in all_fields if f not in FIELD_ORDER]
        ordered_fields = FIELD_ORDER + extra_fields
        # Compute similarity percentages for each top match
        similarity_percents = []
        # Prepare for similarity calculation
        # Feature engineering for all rows
        df_sim = pd.concat([df, pd.DataFrame([fetched_data])], ignore_index=True)
        df_sim["Compression Ratio"] = df_sim["Compression Ratio"].apply(extract_number)
        df_sim["Power (PS)"] = df_sim["Maximum Power"].apply(clean_power)
        df_sim["Torque (Nm)"] = df_sim["Maximum Torque"].apply(clean_torque)
        df_sim[["Bore (mm)", "Stroke (mm)"]] = df_sim["Bore X Stroke (mm)"].apply(lambda x: pd.Series(parse_bore_stroke(x)))
        df_sim["Front Brake Size (mm)"] = df_sim["Front Brake Size"].apply(extract_number)
        df_sim["Rear Brake Size (mm)"] = df_sim["Rear Brake Size"].apply(extract_number)
        numerical_features = [
            "Displacement (cc)", "Compression Ratio", "Power (PS)", "Torque (Nm)",
            "Bore (mm)", "Stroke (mm)", "Kerb Weight (kg)", "Fuel Tank Capacity (L)",
            "Wheelbase (mm)", "Seat Height (mm)", "Front Brake Size (mm)", "Rear Brake Size (mm)"
        ]
        categorical_features = [
            "Engine Layout", "Gear Box", "Final Drive", "Front Suspension", "Rear Suspension",
            "ABS", "Seat Type", "Wheels", "Headlamp", "Instrument Display"
        ]
        for col in numerical_features:
            df_sim[col] = pd.to_numeric(df_sim[col], errors='coerce')
        for col in categorical_features:
            df_sim[col] = df_sim[col].fillna("")
        numeric_imputer = SimpleImputer(strategy="mean")
        X_num = numeric_imputer.fit_transform(df_sim[numerical_features])
        scaler = StandardScaler()
        X_num_scaled = scaler.fit_transform(X_num)
        label_encoders = {}
        X_cat = np.zeros((df_sim.shape[0], len(categorical_features)), dtype=int)
        for i, col in enumerate(categorical_features):
            le = LabelEncoder()
            X_cat[:, i] = le.fit_transform(df_sim[col].astype(str))
            label_encoders[col] = le
        fetched_model_name = fetched_data.get("Models", model)
        idx_fetched = df_sim.index[df_sim["Models"] == fetched_model_name].tolist()
        if idx_fetched:
            idx_fetched = idx_fetched[0]
            ref_num = X_num[idx_fetched]
            ref_num_scaled = X_num_scaled[idx_fetched]
            ref_vec = np.hstack([ref_num_scaled, X_cat[idx_fetched]])
            for m in top_matches:
                idx_match = df_sim.index[df_sim["Models"] == m].tolist()
                if idx_match:
                    idx_match = idx_match[0]
                    cand_num = X_num[idx_match]
                    cand_num_scaled = X_num_scaled[idx_match].copy()
                    for j in range(len(numerical_features)):
                        ref_val = ref_num[j]
                        cand_val = cand_num[j]
                        if np.isnan(ref_val) or np.isnan(cand_val):
                            continue
                        if ref_val == 0:
                            continue
                        if abs(cand_val - ref_val) / abs(ref_val) <= 0.01:
                            cand_num_scaled[j] = ref_num_scaled[j]
                    vec = np.hstack([cand_num_scaled, X_cat[idx_match]])
                    sim_pct = cosine_similarity([ref_vec], [vec])[0, 0] * 100
                    similarity_percents.append(sim_pct)
                else:
                    similarity_percents.append(None)
        else:
            similarity_percents = [None] * len(top_matches)
        # Build table data: each row is a field, columns are models
        table_data = []
        col_headers = [f"{models_to_show[0]} (fetched online data)"]
        for i, m in enumerate(models_to_show[1:]):
            sim = similarity_percents[i]
            if sim is not None:
                col_headers.append(f"{m} ({sim:.2f}% Similar)")
            else:
                col_headers.append(f"{m} (Similarity N/A)")
        for field in ordered_fields:
            row = {"Field": field}
            for i, d in enumerate(model_dicts):
                val = d.get(field, "NA")
                if isinstance(val, float) and pd.isna(val):
                    val = "NA"
                if isinstance(val, list):
                    val = ", ".join(map(str, val))
                row[col_headers[i]] = val
            table_data.append(row)
        df_table = pd.DataFrame(table_data)
        # Reorder columns: Field first, then models
        df_table = df_table[["Field"] + col_headers]
        # Convert all values to string to avoid ArrowTypeError
        df_table = df_table.astype(str)
        st.write("### Model Comparison Table (Fetched + Top 5 Matches)")
        st.dataframe(
            df_table,
            column_config={"Field": st.column_config.Column(label="Field", pinned=True)},
            use_container_width=True
        )
        # Add download button for the comparison table
        csv_data = df_table.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Model Comparison Table as CSV",
            data=csv_data,
            file_name="model_comparison_table.csv",
            mime="text/csv"
        )
        st.caption(" ")
        # Add to Model.csv
        if st.button("Add fetched data to Model.csv"):
            # Convert lists to string for CSV
            row_to_add = {k: (json.dumps(v) if isinstance(v, list) else v) for k, v in fetched_data.items()}
            df = pd.read_csv(CSV_PATH)
            df = pd.concat([df, pd.DataFrame([row_to_add])], ignore_index=True)
            df.to_csv(CSV_PATH, index=False)
            st.success("Added fetched data to Model.csv!")

if __name__ == "__main__":
    main()