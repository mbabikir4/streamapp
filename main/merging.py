import pandas as pd
from main.normalizing import change_title
from functools import reduce
import numpy as np


def concat_sts(sheets_by_symbol):
    """
    Sequentially merge dataframes from newest to oldest using reduce.
    Example: 2023 + 2022 -> result + 2021 -> result + 2020
    """
    if len(sheets_by_symbol) == 1:
        year = list(sheets_by_symbol.keys())[0]
        df = list(sheets_by_symbol.values())[0].copy()
        df.columns = df.columns.str.lower() + f'_{year}'
        return df
    
    # Convert to list of (year, df) tuples sorted by year descending
    sorted_items = sorted(sheets_by_symbol.items(), key=lambda x: x[0], reverse=True)
    
    # Filter out None/empty dataframes
    valid_items = [(year, df) for year, df in sorted_items 
                   if df is not None and isinstance(df, pd.DataFrame) and not df.empty]
    
    if not valid_items:
        raise ValueError("No valid dataframes to merge!")
    
    if len(valid_items) == 1:
        year, df = valid_items[0]
        result = df.copy()
        result.columns = result.columns.str.lower() + f'_{year}'
        return result
    
    # Extract just the dataframes in order
    list_of_dfs = [df for year, df in valid_items]
    
    # Use reduce to sequentially merge all dataframes
    return reduce(lambda x, y: merge_two_sts(x, y), list_of_dfs)


def merge_two_sts(df1, df2):
    df1 = df1.copy()
    df2 = df2.copy()

    # Find common numeric year columns
    common_cols = set.intersection(set(df1.columns.tolist()), set(df2.columns.tolist()))
    
    common_num_cols = [c for c in common_cols if pd.notna(pd.to_numeric(c, errors='coerce'))]
    
    if not common_num_cols:
        return None
        
    min_of_common_years = str(min([int(c) for c in common_num_cols]))
    int_min_of_common_years = int(min_of_common_years)
    
    # Based on label - labels are strings, so use .str accessor
    df1_valid = df1[df1['labels'].notna() & (df1['labels'].str.strip() != '')]
    df2_valid = df2[df2['labels'].notna() & (df2['labels'].str.strip() != '')]
    
    # Based on value - year column might be numeric (float/int), so just check notna()
    # Don't use .str accessor on numeric columns!
    if pd.api.types.is_numeric_dtype(df1[min_of_common_years]):
        # Numeric column - just check for non-null and non-zero
        df1_valid_2 = df1[df1[min_of_common_years].notna() & (df1[min_of_common_years] != 0)]
        df2_valid_2 = df2[df2[min_of_common_years].notna() & (df2[min_of_common_years] != 0)]
    else:
        # String column - use .str accessor
        df1_valid_2 = df1[df1[min_of_common_years].notna() & (df1[min_of_common_years].str.strip() != '')]
        df2_valid_2 = df2[df2[min_of_common_years].notna() & (df2[min_of_common_years].str.strip() != '')]
    
    result1 = df1_valid.merge(
        df2_valid, 
        on='labels', 
        how='outer', 
        suffixes=(f'_{int_min_of_common_years+1}', f'_{int_min_of_common_years}'),
        indicator='label_merge'
    )

    result1[f'labels_{int_min_of_common_years+1}'] = result1['labels']
    
    # Get successfully matched labels BEFORE second merge
    successful_labels = result1[result1['label_merge'] == 'both']['labels'].unique().tolist()
    
    # Based on val (only unmatched)
    result2 = df1_valid_2.merge(
        df2_valid_2, 
        on=min_of_common_years, 
        how='outer', 
        suffixes=(f'_{int_min_of_common_years+1}', f'_{int_min_of_common_years}'),
        indicator='value_merge'
    )

    successful_labels_by_value = result2[result2['value_merge'] == 'both'][f'labels_{int_min_of_common_years+1}'].unique().tolist()

    result1['successful_both'] = result1.apply(
        lambda x: (x[f'labels_{int_min_of_common_years+1}'] in successful_labels_by_value) and 
                  (x[f'labels_{int_min_of_common_years+1}'] in successful_labels), 
        axis=1
    )
    result1['successful_in_label'] = result1.apply(
        lambda x: (x[f'labels_{int_min_of_common_years+1}'] in successful_labels), 
        axis=1
    )
    result1['successful_in_value'] = result1.apply(
        lambda x: (x[f'labels_{int_min_of_common_years+1}'] in successful_labels_by_value), 
        axis=1
    )
    
    result2['successful_both'] = result2.apply(
        lambda x: (x[f'labels_{int_min_of_common_years+1}'] in successful_labels_by_value) and 
                  (x[f'labels_{int_min_of_common_years+1}'] in successful_labels), 
        axis=1
    )
    result2['successful_in_label'] = result2.apply(
        lambda x: (x[f'labels_{int_min_of_common_years+1}'] in successful_labels), 
        axis=1
    )
    result2['successful_in_value'] = result2.apply(
        lambda x: (x[f'labels_{int_min_of_common_years+1}'] in successful_labels_by_value), 
        axis=1
    )
    
    # Concatenate
    result = pd.concat([
        result1[result1['successful_both'] == True], 
        result2[(result2['successful_both'] == False) & (result2['successful_in_value'] == True)]
    ], ignore_index=True)
    
    result[f'status_{int_min_of_common_years+1}'] = np.where(
        result['successful_both'], 'same_label_and_value',
        np.where(result['successful_in_label'], 'same_label',
        np.where(result['successful_in_value'], 'same_value', None))
    )

    result['labels'] = result['labels'].fillna(result[f'labels_{min_of_common_years}'])
    result[min_of_common_years] = result[min_of_common_years].fillna(result[f'{min_of_common_years}_{min_of_common_years}'])
    
    result = result.drop([
        'label_merge', 'value_merge', 'successful_both', 'successful_in_label', 
        'successful_in_value', f'labels_{min_of_common_years}', 
        f'{min_of_common_years}_{min_of_common_years}', f'labels_{int_min_of_common_years+1}'
    ], axis=1)
    
    return result.drop_duplicates(subset='labels')