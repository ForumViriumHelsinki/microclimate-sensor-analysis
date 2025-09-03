import argparse
from pathlib import Path

import pandas as pd

from fvhdata.utils.geojson import combine_geojson
from fvhdata.utils.parquet import combine_parquet


"""
This script combines GeoJSON and/or Parquet files into a single file.

Usage:
python combine_raw_data.py --geojson-in data/raw/makelankatu_latest.geojson data/raw/r4c_all_latest.geojson  --geojson-out data/interim/data_latest.geojson --parquet-in data/raw/makelankatu.parquet data/raw/r4c_all.parquet --parquet-out data/interim/data.parquet

Sample temp/humidity data:

--- SAMPLE DATA (random rows) ---
                                            dev-id  humidity  temperature
time                                                                     
2025-06-23 07:42:00.300000+00:00  24E124136E106684      38.5         23.8
2025-03-28 09:39:25.669000+00:00  24E124136E146080      98.5          4.9
2024-06-10 00:36:57.816000+00:00  24E124136E106636      78.5         10.8
2024-07-28 22:57:18.538000+00:00  24E124136E106638      64.0         19.6
2025-04-20 19:13:25.466000+00:00  24E124136E140283      97.5          6.1

"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Combine GeoJSON and/or Parquet files")
    parser.add_argument("--geojson-in", nargs="+", type=Path, help="List of input GeoJSON files")
    parser.add_argument("--geojson-out", type=Path, help="Path for combined GeoJSON output file")
    parser.add_argument("--parquet-in", nargs="+", type=Path, help="List of input Parquet files")
    parser.add_argument("--parquet-out", type=Path, help="Path for combined Parquet output file")
    parser.add_argument("--fmi-in", nargs="+", type=Path, help="List of input FMI parquet files")
    parser.add_argument("--fmi-out", type=Path, help="Path for combined FMI parquet output file")

    parser.add_argument(
        "--aggregate", type=str, default="1h", help="Time aggregation level for output data (e.g., '15T', '1h', '1D')"
    )
    args = parser.parse_args()

    # Check that at least one input/output pair is provided
    if not ((args.geojson_in and args.geojson_out) or (args.parquet_in and args.parquet_out)):
        parser.error("Provide at least one input/output pair (GeoJSON or Parquet)")

    return args


def save_aggregated_data(df: pd.DataFrame, gdf, output_path: Path, aggregation_level: str = "1h"):
    """Filter and aggregate sensor data based on device IDs from GeoJSON metadata.

    This function filters the time series data to include only devices that exist
    in the GeoJSON metadata, then aggregates the data at the specified time resolution.
    Also filters out data from before installation date for each sensor.

    Args:
        df: DataFrame with time series sensor data (time index, dev-id column)
        gdf: GeoDataFrame with sensor metadata containing device IDs in 'id' column
        output_path: Path where to save the aggregated data
        aggregation_level: Time aggregation level (default "1h")
            Examples: "15T" (15 minutes), "1h" (1 hour), "1D" (1 day)

    Returns:
        pd.DataFrame: Filtered and aggregated DataFrame

    Raises:
        KeyError: If required columns are missing
        ValueError: If no matching devices found
    """
    # Validate input DataFrames
    if "dev-id" not in df.columns:
        raise KeyError("DataFrame must contain 'dev-id' column")

    if "id" not in gdf.columns:
        raise KeyError("GeoDataFrame must contain 'id' column")

    # Parse installation dates from GeoJSON metadata
    device_install_dates = {}
    for idx, row in gdf.iterrows():
        device_id = row["id"]
        install_date = None

        # Check for installation date in either Date_installed or Asennettu_pvm fields
        if pd.notna(row.get("Date_installed")):
            install_date = row["Date_installed"]
        elif pd.notna(row.get("Asennettu_pvm")):
            install_date = row["Asennettu_pvm"]

        if install_date is not None:
            try:
                # Parse the installation date string and convert to pandas timestamp
                install_datetime = pd.to_datetime(install_date)
                # Add one day to get the cutoff date (data from next day onwards is kept)
                cutoff_date = install_datetime + pd.Timedelta(days=1)

                # Ensure cutoff_date has the same timezone as the DataFrame index
                if hasattr(df.index, "tz") and df.index.tz is not None:
                    if cutoff_date.tz is None:
                        # If cutoff_date is timezone-naive but df.index is timezone-aware, localize to UTC
                        cutoff_date = cutoff_date.tz_localize("UTC")
                    elif cutoff_date.tz != df.index.tz:
                        # Convert to the same timezone as df.index
                        cutoff_date = cutoff_date.tz_convert(df.index.tz)

                device_install_dates[device_id] = cutoff_date
                print(
                    f"Device {device_id}: installation date {install_datetime.strftime('%Y-%m-%d')}, data cutoff at {cutoff_date.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            except Exception as e:
                print(f"Error parsing installation date for device {device_id}: {install_date} - {e}")
        else:
            print(
                f"Warning: No installation date found for device {device_id} (missing both Date_installed and Asennettu_pvm)"
            )

    # Get all device IDs from GeoJSON metadata
    valid_device_ids = set(gdf["id"].unique())
    print(f"Found {len(valid_device_ids)} unique device IDs in metadata")

    # Filter DataFrame to include only devices present in GeoJSON
    original_count = len(df)
    filtered_df = df[df["dev-id"].isin(valid_device_ids)].copy()
    filtered_count = len(filtered_df)

    print(
        f"Filtered data: {original_count:,} → {filtered_count:,} rows "
        f"({filtered_count / original_count * 100:.1f}% retained)"
    )

    if filtered_df.empty:
        raise ValueError("No matching devices found between DataFrame and GeoDataFrame")

    # Filter out data before installation date for each device
    pre_install_filter_count = len(filtered_df)
    devices_with_install_dates = []

    for device_id, cutoff_date in device_install_dates.items():
        # Filter this device's data to keep only data from cutoff date onwards
        device_mask = (filtered_df["dev-id"] == device_id) & (filtered_df.index >= cutoff_date)

        # Count data before and after filtering for this device
        device_total = len(filtered_df[filtered_df["dev-id"] == device_id])
        device_kept = len(filtered_df[device_mask])
        device_removed = device_total - device_kept

        if device_removed > 0:
            print(f"Device {device_id}: removed {device_removed:,} pre-installation data points, kept {device_kept:,}")
            devices_with_install_dates.append(device_id)

        # Apply the filter - keep data that is either not from this device, or from this device after cutoff
        filtered_df = filtered_df[(filtered_df["dev-id"] != device_id) | (filtered_df.index >= cutoff_date)]

    post_install_filter_count = len(filtered_df)
    total_removed = pre_install_filter_count - post_install_filter_count

    print(f"Installation date filtering: {pre_install_filter_count:,} → {post_install_filter_count:,} rows")
    print(f"Removed {total_removed:,} data points from before installation dates")
    print(f"Filtered {len(devices_with_install_dates)} devices with installation date data")

    # Aggregate data by time and device
    # Group by device ID and resample by time
    numeric_columns = filtered_df.select_dtypes(include=["number"]).columns
    numeric_columns = [col for col in numeric_columns if col != "dev-id"]

    if not numeric_columns:
        print("Warning: No numeric columns found for aggregation")
        aggregated_df = filtered_df
    else:
        # Aggregate using groupby and resample
        aggregated_list = []

        for device_id in filtered_df["dev-id"].unique():
            device_data = filtered_df[filtered_df["dev-id"] == device_id].copy()

            # Resample numeric columns (mean aggregation)
            # Use label='right' for meteorological convention (timestamp at end of period)
            device_resampled = device_data[numeric_columns].resample(aggregation_level, label="right").mean()

            # Add device ID back
            device_resampled["dev-id"] = device_id

            # Only keep rows with at least one non-null value
            device_resampled = device_resampled.dropna(how="all", subset=numeric_columns)

            if not device_resampled.empty:
                aggregated_list.append(device_resampled)

        if aggregated_list:
            aggregated_df = pd.concat(aggregated_list, axis=0)
            aggregated_df = aggregated_df.sort_index()
            print(f"Aggregated to {len(aggregated_df):,} rows with {aggregation_level} resolution")
        else:
            print("Warning: No data remained after aggregation")
            aggregated_df = pd.DataFrame()

    # Save the aggregated data
    if not aggregated_df.empty:
        # Memory usage before optimization
        memory_before = aggregated_df.memory_usage(deep=True).sum() / 1024 / 1024  # MB

        # Convert to float32 to save memory without significant precision loss
        # Sensor data precision is much lower than float32 precision loss (~0.000003)
        if "humidity" in aggregated_df.columns:
            aggregated_df["humidity"] = aggregated_df["humidity"].astype("float32")
        if "temperature" in aggregated_df.columns:
            aggregated_df["temperature"] = aggregated_df["temperature"].astype("float32")

        # Convert dev-id to categorical for memory efficiency and better performance
        # Only use device IDs that are present in the metadata
        if "dev-id" in aggregated_df.columns:
            categories = sorted(list(valid_device_ids))
            aggregated_df["dev-id"] = aggregated_df["dev-id"].astype(
                pd.CategoricalDtype(categories=categories, ordered=False)
            )

        # Memory usage after optimization
        memory_after = aggregated_df.memory_usage(deep=True).sum() / 1024 / 1024  # MB
        memory_saved = memory_before - memory_after
        print(
            f"Memory optimization: {memory_before:.1f} MB → {memory_after:.1f} MB "
            f"(saved {memory_saved:.1f} MB, {memory_saved / memory_before * 100:.1f}%)"
        )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        aggregated_df.to_parquet(output_path)
        print(f"Aggregated data saved to: {output_path}")

        # Print data type information
        print(f"Data types: {dict(aggregated_df.dtypes)}")
        print(f"Categorical categories: {len(aggregated_df['dev-id'].cat.categories)} unique device IDs")
    else:
        print("Warning: No data to save")

    return aggregated_df


def combine_fmi_data(args: argparse.Namespace):
    """
    Combine FMI data from multiple parquet files into a single parquet file.
    Drop unnecessary stations, columns and convert to float32 to save memory.
    """
    stations_to_save = [
        "Helsinki Kaisaniemi",
        "Helsinki Kumpula",
        "Helsinki Malmi lentokenttä",
        "Helsinki Harmaja",
        "Vantaa Helsinki-Vantaan lentoasema",
    ]
    # Read all parquet files
    df_list = []
    for f in args.fmi_in:
        df = pd.read_parquet(f)
        df_list.append(df)

    # Concatenate all dataframes
    df = pd.concat(df_list, ignore_index=False)
    # Drop all rows where time index is before 2024-05-01
    df = df[df.index >= "2024-05-01"]

    # Drop unnecessary stations
    df = df[df["Station"].isin(stations_to_save)]

    print(df.head(50))
    # Drop unnecessary columns
    # Save to parquet
    args.fmi_out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.fmi_out)
    print(f"FMI data saved to: {args.fmi_out}")
    # Save aggregated data too, aggregating each Station separately
    # Get only numeric columns for aggregation
    numeric_columns = df.select_dtypes(include=["number"]).columns

    # Aggregate each station separately
    aggregated_list = []

    for station in df["Station"].unique():
        station_data = df[df["Station"] == station].copy()

        # Resample numeric columns for this station (mean aggregation)
        station_resampled = station_data[numeric_columns].resample(args.aggregate).mean()

        # Add back Station and fmisid columns
        station_resampled["Station"] = station
        if "fmisid" in station_data.columns:
            # Use the fmisid from this station (should be consistent within station)
            station_resampled["fmisid"] = station_data["fmisid"].iloc[0]

        # Only keep rows with at least one non-null value
        station_resampled = station_resampled.dropna(how="all", subset=numeric_columns)

        if not station_resampled.empty:
            aggregated_list.append(station_resampled)

    if aggregated_list:
        df_agg = pd.concat(aggregated_list, axis=0)
        df_agg = df_agg.sort_index()
        print(
            f"Aggregated to {len(df_agg):,} rows with {args.aggregate} resolution across {len(df['Station'].unique())} stations"
        )
    else:
        print("Warning: No data remained after aggregation")
        df_agg = pd.DataFrame()
    fname_agg = f"{args.fmi_out.parent}/{args.fmi_out.stem}_{args.aggregate}{args.fmi_out.suffix}"
    df_agg.to_parquet(fname_agg)
    return df


def main():
    args = parse_args()
    gdf = df = None

    # GeoJSON processing
    if args.geojson_in and args.geojson_out:
        # Use combine_geojson directly and convert to JSON
        gdf = combine_geojson(args.geojson_in, args.geojson_out)
        print(f"GeoJSON files combined: {args.geojson_out}")

    # Parquet processing
    if args.parquet_in and args.parquet_out:
        # Create output directory if needed
        args.parquet_out.parent.mkdir(parents=True, exist_ok=True)

        # Combine Parquet files using the utility function
        df = combine_parquet(args.parquet_in, args.parquet_out)
        print(f"Parquet files combined: {args.parquet_out}")

    # FMI processing
    if args.fmi_in and args.fmi_out:
        _fmi_df = combine_fmi_data(args)

    if gdf is not None and df is not None:
        fname_agg = f"{args.parquet_out.parent}/{args.parquet_out.stem}_{args.aggregate}{args.parquet_out.suffix}"
        save_aggregated_data(df, gdf, fname_agg, args.aggregate)


if __name__ == "__main__":
    main()
