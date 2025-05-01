import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import numpy as np  # Import numpy for NaN

# Function to load CSV files
@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)

# Main application
def main():
    st.title("Map and Trend Explorer")

    # Sidebar for file uploads
    st.sidebar.header("Upload Data")
    station_file = st.sidebar.file_uploader("Upload station.csv", type=["csv"])
    narrow_file = st.sidebar.file_uploader("Upload narrowresult.csv", type=["csv"])

    if station_file and narrow_file:
        # Load the dataframes
        station_df = load_data(station_file)
        narrow_df = load_data(narrow_file)

        st.subheader("Unique values in ResultMeasureValue:")
        st.write(narrow_df["ResultMeasureValue"].unique())

        # Convert ResultMeasureValue to numeric, coercing errors to NaN
        narrow_df["ResultMeasureValue"] = pd.to_numeric(narrow_df["ResultMeasureValue"], errors='coerce')

        # Check if required columns exist in station_df for the map
        if "LatitudeMeasure" not in station_df.columns or "LongitudeMeasure" not in station_df.columns:
            st.error("Error: 'LatitudeMeasure' and 'LongitudeMeasure' columns are required in station.csv for the map.")
            return

        # Aggregate duplicates before pivoting
        if "MonitoringLocationIdentifier" in narrow_df.columns and "ActivityStartDate" in narrow_df.columns and "CharacteristicName" in narrow_df.columns and "ResultMeasureValue" in narrow_df.columns:
            narrow_agg = narrow_df.groupby(["MonitoringLocationIdentifier", "ActivityStartDate", "CharacteristicName"])["ResultMeasureValue"].mean().reset_index()
            try:
                pivot_df = narrow_agg.pivot(index=["MonitoringLocationIdentifier", "ActivityStartDate"],
                                              columns="CharacteristicName",
                                              values="ResultMeasureValue").reset_index()
            except Exception as e:
                st.error(f"Error during pivoting: {e}")
                return
        else:
            st.error("Error: Required columns missing in narrowresult.csv for aggregation and pivoting.")
            return

        # Get the list of available characteristics from the pivoted dataframe
        characteristic_columns = [col for col in pivot_df.columns if col not in ["MonitoringLocationIdentifier", "ActivityStartDate"]]
        if not characteristic_columns:
            st.error("Error: No characteristic columns found after pivoting narrowresult.csv.")
            return

        # Sidebar for selecting characteristic
        st.sidebar.header("Map and Trend Options")
        selected_characteristic = st.sidebar.selectbox("Select Characteristic", characteristic_columns)

        # Merge the dataframes based on the common identifier "MonitoringLocationIdentifier"
        if "MonitoringLocationIdentifier" in station_df.columns and "MonitoringLocationIdentifier" in pivot_df.columns:
            merged_df = pd.merge(station_df, pivot_df, on="MonitoringLocationIdentifier", how="inner")
        else:
            st.error("Error: 'MonitoringLocationIdentifier' column is required in both station.csv and the pivoted narrowresult data for merging.")
            return

        if not merged_df.empty:
            st.subheader("Map of Stations")
            # Create a PyDeck layer for the map
            layer = pdk.Layer(
                "ScatterplotLayer",
                merged_df,
                get_position=["LongitudeMeasure", "LatitudeMeasure"],
                get_color=[200, 30, 0, 160],
                get_radius=1000,
                radius_min_pixels=5,
                radius_max_pixels=60,
                pickable=True,
                auto_highlight=True,
                tooltip={"html": "<b>Station ID:</b> {MonitoringLocationIdentifier}"},
            )

            # Set the viewport
            view_state = pdk.ViewState(
                latitude=merged_df["LatitudeMeasure"].mean(),
                longitude=merged_df["LongitudeMeasure"].mean(),
                zoom=8,
                pitch=0,
            )

            # Display the map
            st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))

            st.subheader(f"Trend of {selected_characteristic}")
            # Ensure 'ActivityStartDate' column is in datetime format for plotting
            if "ActivityStartDate" in merged_df.columns and selected_characteristic in merged_df.columns:
                try:
                    merged_df["ActivityStartDate"] = pd.to_datetime(merged_df["ActivityStartDate"])
                    # Plot the trend of the selected characteristic over time
                    fig = px.line(merged_df, x="ActivityStartDate", y=selected_characteristic, title=f"Trend of {selected_characteristic} Over Time")
                    st.plotly_chart(fig)
                except Exception as e:
                    st.error(f"Error processing 'ActivityStartDate' column for the trend plot: {e}")
            else:
                st.warning("Warning: Either 'ActivityStartDate' column not found or the selected characteristic is missing after merging.")

        else:
            st.warning("No common stations found in both datasets.")

if __name__ == "__main__":
    main()