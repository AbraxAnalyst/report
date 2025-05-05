import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Energy Dashboard", layout="wide")

st.title("⚡ Energy Source Analytics + Fuel Estimation")

st.markdown("""
This tool lets you:
- Upload energy CSVs from Utility, Gen1, and Gen2
- Analyze energy usage over time
- Estimate fuel consumption for generators based on **3.3 kWh per liter**
""")

# --- Constants ---
GEN_EFFICIENCY_KWH_PER_L = 3.3

# --- Processing Function ---
def process_source(uploaded_file, source_name):
    df = pd.read_csv(uploaded_file)

    required = ['post_date', 'post_time', 'total_kw', 'kwh_import']
    if not all(col in df.columns for col in required):
        st.warning(f"❌ Missing required columns in '{source_name}'")
        return pd.DataFrame()

    df = df[required].copy()
    df['post_datetime'] = pd.to_datetime(df['post_date'] + ' ' + df['post_time'], errors='coerce')
    df = df.sort_values('post_datetime')
    df['KWh'] = df['kwh_import'].diff().fillna(0).round(2)
    df['source'] = source_name

    return df[['post_datetime', 'post_date', 'post_time', 'total_kw', 'kwh_import', 'KWh', 'source']]

# --- File Uploads ---
st.header("📁 Upload CSV Files")
utility_file = st.file_uploader("Upload Utility CSV", type="csv")
gen1_file = st.file_uploader("Upload Gen1 CSV", type="csv")
gen2_file = st.file_uploader("Upload Gen2 CSV", type="csv")

# --- Process & Combine ---
dataframes = []

if utility_file:
    df_util = process_source(utility_file, "Utility")
    if not df_util.empty:
        st.success("✅ Utility data loaded.")
        dataframes.append(df_util)

if gen1_file:
    df_gen1 = process_source(gen1_file, "Gen1")
    if not df_gen1.empty:
        st.success("✅ Gen1 data loaded.")
        dataframes.append(df_gen1)

if gen2_file:
    df_gen2 = process_source(gen2_file, "Gen2")
    if not df_gen2.empty:
        st.success("✅ Gen2 data loaded.")
        dataframes.append(df_gen2)

if dataframes:
    combined_df = pd.concat(dataframes, ignore_index=True)

    # --- Calculate Expected Fuel ---
    combined_df['expected_fuel_liters'] = 0.0
    for gen_source in ['Gen1', 'Gen2']:
        mask = combined_df['source'] == gen_source
        combined_df.loc[mask, 'expected_fuel_liters'] = (
            combined_df.loc[mask, 'KWh'] / GEN_EFFICIENCY_KWH_PER_L
        ).round(2)
        
        
            # --- Tariffs ---
    TARIFF_UTILITY = 209.50  # NGN per kWh
    TARIFF_GEN = 1000     # NGN per liter

    # --- Cost Calculation ---
    combined_df['cost_ngn'] = 0.0

    # Utility: cost from KWh
    combined_df.loc[combined_df['source'] == 'Utility', 'cost_ngn'] = (
        combined_df.loc[combined_df['source'] == 'Utility', 'KWh'] * TARIFF_UTILITY
    )

    # Generators: cost from fuel usage
    for gen_source in ['Gen1', 'Gen2']:
        mask = combined_df['source'] == gen_source
        combined_df.loc[mask, 'cost_ngn'] = (
            combined_df.loc[mask, 'expected_fuel_liters'] * TARIFF_GEN
    )

    combined_df['cost_ngn'] = combined_df['cost_ngn'].round(2)


    # --- Data Preview ---
    st.subheader("📄 Combined Data Preview")
    st.dataframe(combined_df)

    # --- Energy Summary ---
    st.subheader("🔢 Energy Summary by Source")
    summary = combined_df.groupby('source')['KWh'].sum().reset_index()
    summary['KWh'] = summary['KWh'].round(2)
    total_kwh = summary['KWh'].sum()
    summary['% of Total'] = (summary['KWh'] / total_kwh * 100).round(1).astype(str) + '%'

    cols = st.columns(len(summary))
    for idx, row in summary.iterrows():
        with cols[idx]:
            st.metric(label=row['source'], value=f"{row['KWh']} KWh", delta=row['% of Total'])

    # --- Fuel Summary ---
    st.subheader("⛽ Expected Fuel Consumption (3.3 kWh/L)")
    fuel_summary = (
        combined_df[combined_df['source'].isin(['Gen1', 'Gen2'])]
        .groupby('source')['expected_fuel_liters']
        .sum()
        .reset_index()
    )

    fuel_summary['expected_fuel_liters'] = fuel_summary['expected_fuel_liters'].round(2)

    fuel_cols = st.columns(len(fuel_summary))
    for idx, row in fuel_summary.iterrows():
        with fuel_cols[idx]:
            st.metric(label=row['source'], value=f"{row['expected_fuel_liters']} Liters")

    
    
    
    st.subheader("💵 Estimated Cost Summary Utility:209.50/KW, Fuel: 1000/Liter")

    cost_summary = (
        combined_df.groupby('source')['cost_ngn']
        .sum()
        .reset_index()
        .sort_values('cost_ngn', ascending=False)
    )

    total_cost = cost_summary['cost_ngn'].sum()
    cost_summary['% of Total'] = (cost_summary['cost_ngn'] / total_cost * 100).round(1).astype(str) + '%'

    cols_cost = st.columns(len(cost_summary))
    for idx, row in cost_summary.iterrows():
        with cols_cost[idx]:
            st.metric(
                label=row['source'],
                value=f"₦{int(row['cost_ngn']):,}",
                delta=row['% of Total']
            )

# --- Line Chart with High/Low ---
        st.subheader("📈 Line Chart: KWh Over Time by Source (Highlighting High & Low)")

        # Prepare data
        chart_data = (
            combined_df
            .set_index('post_datetime')
            .groupby('source')['KWh']
            .resample('5T')
            .sum()
            .reset_index()
        )

        # Create line chart
        fig = px.line(
            chart_data,
            x='post_datetime',
            y='KWh',
            color='source',
            title="KWh by Source Over Time",
            labels={'post_datetime': 'Time', 'KWh': 'Energy (KWh)'}
        )
    
        # Add high/low markers per source
        for source in chart_data['source'].unique():
            source_data = chart_data[chart_data['source'] == source]
            max_row = source_data.loc[source_data['KWh'].idxmax()]
            min_row = source_data.loc[source_data['KWh'].idxmin()]

        # Add highest value marker
            fig.add_scatter(
                x=[max_row['post_datetime']],
                y=[max_row['KWh']],
                mode='markers+text',
                marker=dict(size=10, color='green'),
                text=["🔺 High"],
                textposition="top center",
                name=f"{source} High"
            )

            # Add lowest value marker
            fig.add_scatter(
                x=[min_row['post_datetime']],
                y=[min_row['KWh']],
                mode='markers+text',
                marker=dict(size=10, color='red'),
                text=["🔻 Low"],
                textposition="bottom center",
                name=f"{source} Low"
            )

    fig.update_layout(xaxis_title='Time', yaxis_title='Energy (KWh)', legend_title='Source')
    st.plotly_chart(fig, use_container_width=True)


    # --- Download Button ---
    st.download_button(
        label="📥 Download Combined Data as CSV",
        data=combined_df.to_csv(index=False).encode('utf-8'),
        file_name="combined_energy_data.csv",
        mime='text/csv'
    )
else:
    st.info("👆 Please upload at least one CSV file to begin.")
