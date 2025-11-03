import pandas as pd
import numpy as np


def merge_sts(df1, df2, max_year):
    return pd.merge(df1, df2, how='outer', on='merge_index', 
                    suffixes=(f"_{max_year}", f"_{max_year-1}"))


def is_column_unique(df, column_name):
    # Filter out zeros and NaNs
    filtered_df = df[column_name].dropna()
    filtered_df = filtered_df[filtered_df != 0]
    
    # Check for uniqueness
    return filtered_df.is_unique


def get_max_numeric_value(df, column_name):
    numeric_values = pd.to_numeric(df[column_name], errors='coerce')
    # Get the maximum value, ignoring NaN
    max_value = numeric_values.max()
    
    return max_value


def get_max_numeric_value_dfs(dfs, column_name):
    return max([get_max_numeric_value(df, column_name) for df in dfs])


def rename_duplicates(df, column_name, suffix='_dup'):
    """
    Vectorized version - much faster than the original implementation.
    """
    series = df[column_name]
    
    # Group by value and count occurrences
    duplicates_count = series.groupby(series).cumcount()
    
    # Only add suffix to duplicates (where count > 0)
    mask = duplicates_count > 0
    result = series.copy()
    result[mask] = series[mask] + suffix + duplicates_count[mask].astype(str)
    
    return result


def create_merge_key(df, year_col, label_col='labels'):
    """
    Create a merge key combining year column values and labels.
    Handles NaN and zero values appropriately.
    """
    # Convert year column to string, handling NaN and zeros
    year_vals = df[year_col].copy()
    year_vals = year_vals.replace(0, np.nan)
    year_str = year_vals.astype(str).replace('nan', 'MISSING')
    
    # Combine with labels
    merge_key = year_str + '|||' + df[label_col].astype(str)
    
    return merge_key


def get_merge_column(df1, df2, year_common):
    """
    Original function - kept for backwards compatibility if needed.
    Not used in the optimized version.
    """
    used_numbers = 0
    for row_ind, row in df1.iterrows():
        match = df2[(df2[year_common] == row[year_common]) & 
                   (~pd.isnull(df2[year_common])) & 
                   (~pd.isna(df2[year_common])) & 
                   (df2[year_common] != 0)]
        if len(match) == 1:
            df2.loc[match.index.tolist(), 'merge_index'] = used_numbers
            df1.loc[row_ind, 'merge_index'] = used_numbers
            used_numbers += 1
        elif len(match) > 1:
            match_new = match[(match['labels'] == row['labels'])]
            if len(match_new) == 1:
                df2.loc[match_new.index.tolist(), 'merge_index'] = used_numbers
                df1.loc[row_ind, 'merge_index'] = used_numbers
                used_numbers += 1


def get_merge_column_alt(df1, df2, year_common):
    """
    Original function - kept for backwards compatibility if needed.
    Not used in the optimized version.
    """
    for row_ind, row in df1.iterrows():
        match = df2[(df2[year_common] == row[year_common]) & 
                   (~pd.isnull(df2[year_common])) & 
                   (~pd.isna(df2[year_common])) & 
                   (df2[year_common] != 0)]
        if len(match) == 1:
            for row_df2_ind, row_df2 in match.iterrows():
                df2.loc[row_df2_ind, 'merge_index'] = (
                    row['merge_index'] if type(row['merge_index']) in [int, float] 
                    else df2.loc[row_df2_ind, 'merge_index']
                )
        elif len(match) > 1:
            match_new = match[(match['labels'] == row['labels'])]
            if len(match_new) == 1:
                for row_df2_ind, row_df2 in match_new.iterrows():
                    df2.loc[row_df2_ind, 'merge_index'] = row['merge_index']


def concat_sts(sheets_by_symbol):
    """
    Optimized version using vectorized operations and pandas merge.
    
    This version:
    1. Uses vectorized operations instead of iterrows()
    2. Leverages pandas' optimized merge functionality
    3. Handles duplicate labels efficiently
    4. Matches rows based on year column values and labels
    
    Args:
        sheets_by_symbol: Dictionary of {year: DataFrame}
    
    Returns:
        Merged DataFrame with columns suffixed by year
    """
    # Handle single year case
    if len(sheets_by_symbol) == 1:
        year = list(sheets_by_symbol.keys())[0]
        df = sheets_by_symbol[year].copy()
        df.columns = df.columns.str.lower() + f'_{year}'
        return df
    
    # Sort years in ascending order
    sorted_years = sorted(sheets_by_symbol.keys())
    
    # Find the common year column across consecutive dataframes
    # This is typically the column that contains year values used for matching
    year_col = None
    for i in range(len(sorted_years) - 1):
        curr_year = sorted_years[i]
        next_year = sorted_years[i + 1]
        
        curr_cols = set(sheets_by_symbol[curr_year].columns)
        next_cols = set(sheets_by_symbol[next_year].columns)
        
        common_cols = curr_cols & next_cols
        common_cols.discard('labels')
        
        if common_cols:
            # Prefer numeric columns
            for col in common_cols:
                if pd.api.types.is_numeric_dtype(sheets_by_symbol[curr_year][col]):
                    year_col = col
                    break
            if year_col:
                break
    
    # Process each year's dataframe
    processed_dfs = []
    
    for year_idx, year in enumerate(sorted_years):
        df = sheets_by_symbol[year].copy()
        
        # Handle duplicate labels using vectorized operation
        df['labels'] = rename_duplicates(df, 'labels')
        
        # Create merge key
        if year_col and year_col in df.columns:
            # Create composite key: year_value + label
            # This matches the original logic of matching on year column + labels
            year_vals = df[year_col].copy()
            year_vals = year_vals.replace(0, np.nan)
            year_str = year_vals.astype(str).replace('nan', 'MISSING')
            df['_merge_key'] = year_str + '|||' + df['labels'].astype(str)
        else:
            # Fall back to labels only
            df['_merge_key'] = df['labels'].astype(str)
        
        # Store the merge key for this specific year
        df[f'_merge_key_{year}'] = df['_merge_key']
        
        # Rename all columns except merge keys
        cols_to_rename = [col for col in df.columns if not col.startswith('_merge_key')]
        for col in cols_to_rename:
            df = df.rename(columns={col: f"{col.lower()}_{year}"})
        
        processed_dfs.append(df)
    
    # Start with the first dataframe
    result = processed_dfs[0]
    first_year = sorted_years[0]
    
    # Sequentially merge each subsequent year
    # This mimics the original algorithm's sequential merging approach
    for i in range(1, len(processed_dfs)):
        current_year = sorted_years[i]
        df_to_merge = processed_dfs[i]
        
        # For the first merge, use the first year's key
        # For subsequent merges, try to use keys from already-merged data
        left_key = f'_merge_key_{first_year}'
        right_key = f'_merge_key_{current_year}'
        
        # Merge on the merge keys
        result = pd.merge(
            result,
            df_to_merge,
            left_on=left_key,
            right_on=right_key,
            how='outer',
            suffixes=('', '_dup')
        )
        
        # Update merge key columns for next iteration
        # If a row matched, propagate the merge key
        if f'_merge_key_{current_year}' in result.columns and left_key in result.columns:
            result[left_key] = result[left_key].fillna(result[f'_merge_key_{current_year}'])
    
    # Clean up: remove all merge key columns
    result = result[[col for col in result.columns if not col.startswith('_merge_key')]]
    
    # Remove duplicate columns that might have been created
    result = result.loc[:, ~result.columns.str.endswith('_dup')]
    
    return result