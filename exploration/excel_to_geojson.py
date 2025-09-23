#!/usr/bin/env python3
"""
Script to explore Excel file structure and convert TempHumiditySensor data to GeoJSON format.
"""

import json
import os
import sys

import pandas as pd


def explore_excel_structure(excel_path):
    """
    Explore the structure of the Excel file and display information about each sheet.
    """
    print(f"Exploring Excel file: {excel_path}")
    print("=" * 60)

    # Read all sheets
    excel_file = pd.ExcelFile(excel_path)

    print(f"Found {len(excel_file.sheet_names)} sheets:")
    for i, sheet_name in enumerate(excel_file.sheet_names, 1):
        print(f"{i}. {sheet_name}")

    print("\n" + "=" * 60)

    # Examine each sheet
    for sheet_name in excel_file.sheet_names:
        print(f"\nSheet: {sheet_name}")
        print("-" * 40)

        df = pd.read_excel(excel_path, sheet_name=sheet_name)

        print(f"Rows: {len(df)}")
        print(f"Columns: {len(df.columns)}")
        print(f"Column names: {list(df.columns)}")

        # Show first few rows
        print("\nFirst 3 rows:")
        print(df.head(3).to_string())

        # Show data types
        print("\nData types:")
        for col, dtype in df.dtypes.items():
            print(f"  {col}: {dtype}")

        print("\n" + "=" * 60)


def parse_geometry(geometry_str):
    """
    Parse POINT geometry string to coordinates array.
    Input: "POINT (24.95214986305944 60.19603679151048)" or "POINT (24.9713103, 60.1960368)"
    Output: [24.95214986305944, 60.19603679151048]
    """
    if pd.isna(geometry_str) or not geometry_str.startswith("POINT"):
        return None

    # Extract coordinates from "POINT (lon lat)" format
    coords_str = geometry_str.replace("POINT (", "").replace(")", "").strip()

    # Handle both space and comma separated coordinates
    if "," in coords_str:
        # Split by comma and clean up
        parts = [part.strip() for part in coords_str.split(",")]
        if len(parts) >= 2:
            lon, lat = float(parts[0]), float(parts[1])
        else:
            return None
    else:
        # Split by space
        parts = coords_str.split()
        if len(parts) >= 2:
            lon, lat = float(parts[0]), float(parts[1])
        else:
            return None

    return [lon, lat]


def create_geojson_from_excel(excel_path, output_path):
    """
    Create GeoJSON file from Excel data.
    Uses "Properties geojsonista" sheet for basic data and "Yhdenmukaistettu" for additional fields.
    """
    print("Creating GeoJSON from Excel data...")

    # Read both sheets
    df_properties = pd.read_excel(excel_path, sheet_name="Properties geojsonista")
    df_unified = pd.read_excel(excel_path, sheet_name="Yhdenmukaistettu")

    features = []

    for _, row_props in df_properties.iterrows():
        # Skip rows with missing essential data
        if pd.isna(row_props["id"]) or pd.isna(row_props["geometry"]):
            continue

        # Parse coordinates
        coordinates = parse_geometry(row_props["geometry"])
        if coordinates is None:
            continue

        # Find matching row in unified sheet by id
        # Handle cases where id might have extra characters (like parentheses)
        prop_id = str(row_props["id"]).strip()
        unified_row = df_unified[df_unified["id"] == prop_id]

        # If exact match not found, try to match by removing trailing characters
        if len(unified_row) == 0:
            # Try matching with cleaned id (remove trailing non-alphanumeric characters)
            import re

            clean_prop_id = re.sub(r"[^\w]+$", "", prop_id)
            unified_row = df_unified[
                df_unified["id"].astype(str).str.replace(r"[^\w]+$", "", regex=True) == clean_prop_id
            ]

        if len(unified_row) > 0:
            row_unified = unified_row.iloc[0]
        else:
            row_unified = None

        # Create feature
        feature = {
            "type": "Feature",
            "id": str(row_props["id"]),
            "geometry": {"type": "Point", "coordinates": coordinates},
            "properties": {},
        }

        # Store special properties to add at the end
        special_properties = {
            "fid": "fid",
            "Tyyppi": "Tyyppi",
            "Huomiot": "Huomiot",
            "Kiinnitystapa": "Kiinnitystapa",
            "Sensori": "Sensori",
        }
        special_props_values = {}

        # Process special properties first but don't add them yet
        for excel_col, geojson_prop in special_properties.items():
            if excel_col in row_props:
                value = row_props[excel_col]
                if pd.isna(value):
                    special_props_values[geojson_prop] = None
                else:
                    # Apply type conversions
                    if geojson_prop == "fid":
                        # Convert fid to integer
                        value = int(float(value)) if not pd.isna(value) else None
                    elif geojson_prop == "Sensori":
                        # Convert Sensori to integer
                        value = int(float(value)) if not pd.isna(value) else None
                    elif isinstance(value, pd.Timestamp):
                        # Convert datetime to string
                        value = value.strftime("%Y-%m-%d")
                    elif hasattr(value, "item"):
                        # Convert numpy types to native Python types
                        value = value.item()

                    special_props_values[geojson_prop] = value

        # Add additional properties from Yhdenmukaistettu sheet
        if row_unified is not None:
            additional_fields = [
                "project",
                "installationDate",
                "street",
                "postalcode",
                "city",
                "district",
                "sunExposure",
                "solarShielding",
                "heightFromGround",
                "mountingType",
                "terrain",
                "groundCover",
                "landUse",
                "buildingDensity",
                "LCZ",
                "LCZ long",
                "Kuvaus",
            ]

            for field in additional_fields:
                if field in row_unified:
                    value = row_unified[field]
                    if pd.isna(value):
                        feature["properties"][field] = None
                    else:
                        # Apply type conversions for specific fields
                        if field == "postalcode":
                            # Convert postalcode to string with proper formatting (e.g., 510.0 -> "00510")
                            if isinstance(value, (int, float)):
                                value = f"{int(value):05d}"  # Format as 5-digit string with leading zeros
                            else:
                                value = str(value)
                        elif field == "solarShielding":
                            # Convert solarShielding to integer
                            value = int(float(value)) if not pd.isna(value) else None
                        elif isinstance(value, pd.Timestamp):
                            # Convert datetime to string
                            value = value.strftime("%Y-%m-%d")
                        elif hasattr(value, "item"):
                            # Convert numpy types to native Python types
                            value = value.item()

                        feature["properties"][field] = value
                else:
                    feature["properties"][field] = None

        # Finally, add the special properties at the end to maintain desired order
        for prop_name, prop_value in special_props_values.items():
            feature["properties"][prop_name] = prop_value

        features.append(feature)

    # Create GeoJSON structure
    geojson = {"type": "FeatureCollection", "features": features}

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)

    print(f"Created GeoJSON file with {len(features)} features: {output_path}")
    return geojson


def main():
    # Path to the Excel file
    excel_path = sys.argv[1]
    output_path = sys.argv[2]

    if not os.path.exists(excel_path):
        print(f"Error: Excel file not found at {excel_path}")
        return

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print("=== Excel Structure Exploration ===")
    explore_excel_structure(excel_path)

    print("\n=== Creating GeoJSON ===")
    geojson_data = create_geojson_from_excel(excel_path, output_path)

    # Show a sample of the created GeoJSON
    if geojson_data and geojson_data.get("features"):
        print("\nSample feature from created GeoJSON:")
        print(json.dumps(geojson_data["features"][0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
