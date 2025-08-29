from pathlib import Path
from typing import List, Union, Optional
import pandas as pd


def combine_parquet(files: List[Union[str, Path]], output_path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """Combine multiple Parquet files into a single DataFrame.

    Args:
        files: List of paths to Parquet files to combine
        output_path: Optional path to save the combined Parquet file

    Returns:
        DataFrame containing combined data from all input files, with preserved time index

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
    dfs = [pd.read_parquet(f) for f in file_paths]
    combined_df = pd.concat(dfs, axis=0)

    # Sort by time index
    combined_df = combined_df.sort_index()

    # Remove any duplicate indices while keeping the last occurrence
    combined_df = combined_df[~combined_df.index.duplicated(keep="last")]

    # Save if output path provided
    if output_path:
        output_path = Path(output_path)
        # Create directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined_df.to_parquet(output_path)

    return combined_df
