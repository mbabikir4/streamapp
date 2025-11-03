import pandas as pd
import datefinder 
import re
from datetime import datetime
from main.normalizing import change_title, fix_total_labels



def extract_year(title):
    """Extract the first 4-digit year from a string."""
    match = re.search(r'\b\d{4}\b', str(title))
    if match:
        return match.group()
    return str(title)


def rename_duplicates(headers):
    """Rename duplicate column names by appending _r{count}."""
    count = {}
    new_headers = []
    
    for col in headers:
        if col in count:
            count[col] += 1
            new_col_name = f"{col}_r{count[col]}"
        else:
            count[col] = 0
            new_col_name = col
        new_headers.append(new_col_name)
    
    return new_headers


def clean_cell_value(value):
    """Clean cell values from textractor output."""
    if pd.isna(value) or value is None:
        return ''
    return str(value).strip()


def adjust_header(df):
    """
    Adjust headers for DataFrames from textractor table.to_pandas().
    Textractor tables may have:
    - Multi-row headers
    - Merged cells represented as empty strings
    - Inconsistent data types
    """
    
    # Handle empty dataframe
    if df.empty or len(df.columns) == 0:
        return df
    
    # Clean all cells in the dataframe
    # old was applymap
    df = df.map(clean_cell_value)
    
    # Get original column names (textractor usually names them col_0, col_1, etc.)
    # Handle cases where column names might be integers
    original_cols = [str(col).lower().strip().replace('usd', '').replace('sr', '') 
                     for col in df.columns.tolist()]
    
    # Get the first few rows to search for headers
    first_row = df.iloc[0].tolist() if len(df) > 0 else []
    second_row = df.iloc[1].tolist() if len(df) > 1 else []
    
    # Find the "notes" row - search in first 5 rows
    notes_row = [''] * len(original_cols)
    notes_row_idx = None
    
    for idx in range(min(5, len(df))):
        row_values = df.iloc[idx].tolist()
        # Check if any cell contains only "note" or "notes"
        for val in row_values:
            if isinstance(val, str) and 'note' in val.lower() and len(val.strip().split()) <= 2:
                notes_row_idx = idx
                notes_row = row_values
                break
        if notes_row_idx is not None:
            break
    
    # Remove notes row if found
    if notes_row_idx is not None:
        df = df.drop(notes_row_idx).reset_index(drop=True)
        # Update first and second rows after dropping notes row
        first_row = df.iloc[0].tolist() if len(df) > 0 else []
        second_row = df.iloc[1].tolist() if len(df) > 1 else []
    
    # Collect dates with priority: notes row, second row, first row, then original columns
    date_sources = [notes_row, second_row, first_row, original_cols]
    date_columns = []

    for date_source in date_sources:
        # Filter out non-string/non-numeric values and NaN
        date_source = [
            string for string in date_source 
            if (isinstance(string, (str, int, float)) and 
                string != '' and 
                not (isinstance(string, float) and pd.isna(string)))
        ]
        
        if not date_source:
            continue
        
        date_source_applied = []
        
        for string in date_source:
            string_str = str(string).strip()
            
            # Skip empty strings
            if not string_str:
                continue
            
            # Try pandas to_datetime first
            original_pd_dt = pd.to_datetime(string_str, errors='coerce')
            if not pd.isnull(original_pd_dt) and original_pd_dt.year > 1900:
                date_source_applied.append(original_pd_dt)
            else:
                # Try datefinder as fallback
                try:
                    datefinder_list = list(
                        datefinder.find_dates(
                            string_str, 
                            strict=False, 
                            index=True,
                            base_date=datetime(2000, 1, 1)  # Use reasonable base date
                        )
                    )
                    
                    if datefinder_list and datefinder_list[0][0].year > 1900:
                        date_obj = datefinder_list[0][0]
                        date_source_applied.append(pd.Timestamp(date_obj))
                except Exception:
                    # If datefinder fails, skip this value
                    continue
        
        # If we found valid dates, use them
        if len(date_source_applied) > 0:
            date_columns = [date_obj.year for date_obj in date_source_applied]
            if len(date_columns)==2:
                date_columns[1]=date_columns[0]-1
            break
    
    # Construct the new header with 'labels', 'notes', and date columns
    new_header = ['labels', 'notes'] + date_columns
    
    # Adjust header length to match dataframe columns
    if len(new_header) > len(df.columns):
        new_header = new_header[:len(df.columns)]
    
    if len(df.columns) > len(new_header):
        diff = len(df.columns) - len(new_header)
        for i in range(len(new_header), len(new_header) + diff):
            if i < len(original_cols):
                new_header.append(original_cols[i])
            else:
                new_header.append(f'col_{i}')
    
    # Apply extracted years to column names and handle duplicates
    df.columns = rename_duplicates([extract_year(str(col)) for col in new_header])
    df['labels_as_is'] = df['labels']
    df['labels'] = df['labels'].apply(change_title)
    return df


def process_textractor_table(table):
    """
    Convenience function to process a textractor table object directly.
    
    Args:
        table: Textractor table object
        
    Returns:
        pd.DataFrame: Processed dataframe with adjusted headers
    """
    df = table.to_pandas()
    return df.pipe(adjust_header)
    # return df.pipe(adjust_header).pipe(fix_total_labels)



def numify(series):
    """
    Bare minimum version
    """
    return pd.to_numeric(
        series.astype(str)
        .str.replace(r'[^\d.\-]', '', regex=True)  # Keep digits, decimal, minus
        .str.replace(r'^\((.+)\)$', r'-\1', regex=True),  # Convert (123) to -123
        errors='coerce'
    )