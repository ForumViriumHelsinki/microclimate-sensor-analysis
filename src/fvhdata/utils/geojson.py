from pathlib import Path
from typing import List, Optional, Union

import geopandas as gpd
import pandas as pd


def combine_geojson(files: List[Union[str, Path]], output_path: Optional[Union[str, Path]] = None) -> gpd.GeoDataFrame:
    """Combine multiple GeoJSON files into a single GeoDataFrame.

    Args:
        files: List of paths to GeoJSON files to combine
        output_path: Optional path to save the combined GeoJSON file

    Returns:
        GeoDataFrame containing combined data from all input files

    Raises:
        FileNotFoundError: If any input file doesn't exist
        ValueError: If input files list is empty or files are not compatible
    """
    if not files:
        raise ValueError("No input files provided")

    # Convert all paths to Path objects
    file_paths = [Path(f) for f in files]

    # Verify all files exist
    for file_path in file_paths:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

    # Read and combine files
    gdfs = [gpd.read_file(f) for f in file_paths]
    combined_gdf = pd.concat(gdfs, ignore_index=True)
    print(combined_gdf.head())

    # Save if output path provided
    if output_path:
        output_path = Path(output_path)
        # Create directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined_gdf.to_file(output_path, driver="GeoJSON")

    return combined_gdf
