import pandas as pd
import re
import json
def numify(value):
    """
    Convert string to numeric, handling accounting notation.
    Keeps only digits, decimal points, and minus signs.
    Returns None if conversion fails.
    """
    # Handle None/NaN
    if pd.isna(value) or value is None:
        return None
    
    str_value = str(value).strip()
    
    # Return None for empty strings
    if not str_value:
        return None
    
    # Remove whitespace
    str_value = str_value.replace(' ', '')
    
    # Convert (123) to -123
    str_value = re.sub(r'^\((.+)\)$', r'-\1', str_value)
    
       
    # Keep only digits, decimal, and minus
    str_value = re.sub(r'[^\d.\-]', '', str_value)
    
    # Try to parse as float
    if not str_value or str_value in ('-', '.', '-.'):
        return None
    
    try:
        return float(str_value)
    except ValueError:
        return None


def get_notes(self, sheet, year):
    """
    Match notes from sheet to tables found in the document.
    Uses exact matching with bidirectional scaling.
    """
    try:
    # Filter to rows with notes and initialize path column
        notes_sheet = sheet.dropna(subset=["notes"]).copy()
        if notes_sheet.empty:
            sheet['path'] = []
            return sheet
        
        notes_sheet["path"] = [[] for _ in range(len(notes_sheet))]
        
        # Pre-compute year columns and get numeric values as floats
        years_to_check = [year, str(int(year) - 1)]
        notes_values = set()
        
        for yr in years_to_check:
            if yr in notes_sheet.columns:
                vals = pd.to_numeric(notes_sheet[yr], errors='coerce').dropna()
                vals = vals[vals != 0]
                # Store as floats for exact comparison
                notes_values.update(float(v) for v in vals.values)
        
        if not notes_values:
            sheet['path'] = notes_sheet['path']
            return sheet
        
        # print(f"Looking for {len(notes_values)} note values")
        
        # Process each table
        for idx, table in enumerate(self.notes_tables):
            try:
                table_df = table.to_pandas()
                
                # Extract numeric values from table (store as floats)
                table_values = set()
                for col in table_df.columns:
                    for val in table_df[col]:
                        numeric_val = numify(val)
                        if numeric_val is not None and numeric_val != 0:
                            # Store absolute value as float
                            table_values.add(float(abs(numeric_val)))
                
            except Exception:
                continue
            
            # Skip if no values
            if not table_values:
                continue
            
            # Skip tables with only very small values (likely indices/text artifacts)
            if max(table_values) < 10:
                continue
            
            # Check for exact matches with bidirectional scaling
            matched_values = set()
            scale_factor = None
            scale_direction = None
            
            scales = [1, 10, 100, 1000, 10000, 100000, 1000000]
            
            for scale in scales:
                # Option 1: Scale table values UP
                table_scaled_up = {v * scale for v in table_values}
                matches_up = notes_values & table_scaled_up
                
                if matches_up:
                    matched_values.update(matches_up)
                    if scale > 1:
                        scale_factor = scale
                        scale_direction = "table_scaled_up"
                
                # Option 2: Scale notes values UP (equivalently, scale table DOWN)
                notes_scaled_up = {v * scale for v in notes_values}
                matches_down = notes_scaled_up & table_values
                
                if matches_down:
                    # Convert back to original note values
                    matched_values.update(m / scale for m in matches_down)
                    if scale > 1:
                        scale_factor = scale
                        scale_direction = "notes_scaled_up"
            
            if not matched_values:
                continue
            
            # Find rows that match (exact floating point comparison)
            years_to_check = [x for x in years_to_check if x in notes_sheet.columns.tolist()]
            mask = notes_sheet[years_to_check].apply(
                lambda col: col.apply(lambda x: float(x) in matched_values if pd.notna(x) else False)
            ).any(axis=1)
            
            if mask.any():
                # print(f"\n✓ Table {idx}: Found {mask.sum()} matching rows")
                # print(f"  Matched values: {sorted(list(matched_values))[:10]}")
                # print(f"  Table values sample: {sorted(list(table_values))[:10]}")
                
                # if scale_factor:
                #     if scale_direction == "table_scaled_up":
                #         print(f"  → Table values scaled UP by {scale_factor}")
                #     else:
                #         print(f"  → Notes values scaled UP by {scale_factor} (table scaled down)")
                
                # Append table index to matching rows
                matched_indices = notes_sheet[mask].index
                for i in matched_indices:
                    notes_sheet.at[i, 'path'].append(idx)
        
        sheet['path'] = notes_sheet['path'].apply(lambda x: json.dumps(x)).astype(str)
    except Exception as e:
        print(e,years_to_check,notes_sheet.columns.tolist())
    return sheet