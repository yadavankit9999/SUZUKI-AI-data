import pandas as pd
import numpy as np
import re
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.metrics.pairwise import cosine_similarity
import os

# --- CONFIG ---
CSV_PATH = os.path.join(os.path.dirname(__file__), "Model.csv")
TOP_N = 5

def extract_number(text):
    text = str(text).replace(",", "")
    match = re.findall(r"[\d.]+", text)
    return float(match[0]) if match else np.nan

def parse_bore_stroke(text):
    text = str(text).replace(",", "")
    match = re.findall(r"([\d.]+)", text)
    if len(match) >= 2:
        return float(match[0]), float(match[1])
    return np.nan, np.nan

def clean_power(text):
    text = str(text).replace(",", "")
    match = re.findall(r"[\d.]+", text)
    return float(match[0]) if match else np.nan

def clean_torque(text):
    text = str(text).replace(",", "")
    match = re.findall(r"[\d.]+", text)
    return float(match[0]) if match else np.nan

def binary_encode(text):
    text = str(text).strip().lower()
    if text in ["x", "yes", "true", "available"]:
        return 1
    elif text in ["no", "na", "n/a", ""]:
        return 0
    else:
        return 0

def get_similarity_df():
    df = pd.read_csv(CSV_PATH)
    numerical_features = [
        "Displacement (cc)", "Compression Ratio", "Power (PS)", "Torque (Nm)",
        "Bore (mm)", "Stroke (mm)", "Kerb Weight (kg)", "Fuel Tank Capacity (L)",
        "Wheelbase (mm)", "Seat Height (mm)", "Front Brake Size (mm)", "Rear Brake Size (mm)"
    ]
    categorical_features = [
        "Engine Layout", "Gear Box", "Final Drive", "Front Suspension", "Rear Suspension",
        "ABS", "Seat Type", "Wheels", "Headlamp", "Instrument Display"
    ]
    # Feature engineering
    df["Compression Ratio"] = df["Compression Ratio"].apply(extract_number)
    df["Power (PS)"] = df["Maximum Power"].apply(clean_power)
    df["Torque (Nm)"] = df["Maximum Torque"].apply(clean_torque)
    df[["Bore (mm)", "Stroke (mm)"]] = df["Bore X Stroke (mm)"].apply(lambda x: pd.Series(parse_bore_stroke(x)))
    df["Front Brake Size (mm)"] = df["Front Brake Size"] .apply(extract_number)
    df["Rear Brake Size (mm)"] = df["Rear Brake Size"] .apply(extract_number)
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
    X_processed = np.hstack([X_num_scaled, X_cat])
    cosine_sim_matrix = cosine_similarity(X_processed)
    similarity_df = pd.DataFrame(
        cosine_sim_matrix,
        index=df["Models"],
        columns=df["Models"]
    )
    return similarity_df, df

def show_top_matches(model_name, top_n=5):
    similarity_df, df = get_similarity_df()
    if model_name not in similarity_df.index:
        print(f"Model '{model_name}' not found.")
        return
    sim_scores = similarity_df.loc[model_name].drop(model_name)  # exclude itself
    sim_scores = sim_scores.sort_values(ascending=False)
    print(f"\nTop {top_n} matches for '{model_name}':\n")
    for other_model, score in sim_scores.head(top_n).items():
        print(f"{other_model}: {round(score * 100, 2)}% match")

if __name__ == "__main__":
    model_name = input("Enter the model name to compare: ")
    show_top_matches(model_name, top_n=TOP_N) 