import streamlit as st
import pandas as pd
import io

st.title("Energy Source Data Processor")

st.markdown("""
Upload CSV files for **Utility**, **Gen1**, and **Gen2** energy sources.  
The app will:
- Combine `post_date` and `post_time` into `post_datetime`
- Calculate `KWh` from `kwh_import`
- Tag each source
""")

def process_source(uploaded_file, source_name):
    df = pd.read_csv(uploaded_file)

    # Clean and ensure required columns exist
    required = ['post_date', 'post_time', 'total_kw', 'kwh_import']
    if not all(col in df.columns for col in required):
        st.warning(f"Missing required columns in {source_name}")
        return pd.DataFrame()

    df = df[required]
    df['post_datetime'] = pd.to_datetime(df['post_date'] + ' ' + df['post_time'], errors='coerce')
    df = df.sort_values('post_datetime')
    df['KWh'] = df['kwh_import'].diff().fillna(0).round(2)
    df['source'] = source_name
    df = df[['post_datetime', 'post_date', 'post_time', 'total_kw', 'kwh_import', 'KWh', 'source']]
    return df

# File uploads
utility_file = st.file_uploader("Upload Utility CSV", type="csv")
gen1_file = st.file_uploader("Upload Gen1 CSV", type="csv")
gen2_file = st.file_uploader("Upload Gen2 CSV", type="csv")

dataframes = []

if utility_file:
    df_utility = process_source(utility_file, "Utility")
    if not df_utility.empty:
        st.success("Utility file processed.")
        dataframes.append(df_utility)

if gen1_file:
    df_gen1 = process_source(gen1_file, "Gen1")
    if not df_gen1.empty:
        st.success("Gen1 file processed.")
        dataframes.append(df_gen1)

if gen2_file:
    df_gen2 = process_source(gen2_file, "Gen2")
    if not df_gen2.empty:
        st.success("Gen2 file processed.")
        dataframes.append(df_gen2)

# Combine and display
if dataframes:
    combined_df = pd.concat(dataframes, ignore_index=True)
    st.subheader("Combined Data Preview")
    st.dataframe(combined_df)

    st.subheader("KWh Over Time by Source")
    st.line_chart(combined_df.set_index('post_datetime').groupby('source')['KWh'].resample('5T').sum().unstack(0))
