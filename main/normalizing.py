import pandas as pd
import re

def change_title(word):
    # remove all spaces and trailing characters
    if not pd.isnull(word):
        new_word = ""
        for ch in str(word).strip().strip(":,-").lower():
            if str(ch).isalpha():
                new_word = new_word + ch
            else:
                new_word = new_word + "_"
        # list_of_labels[ind]=new_word
        new_word = re.sub(r'_+', '_', new_word)
        new_word = new_word.replace(" ", "")
        # to adapt later
        if "total_non_current_liab" in new_word and new_word.startswith("total"):
            new_word = "total_non_current_liabilities"
        elif "total_current_liab" in new_word  and new_word.startswith("total"):
            new_word = "total_current_liabilities"
        elif "non_current_liab" in new_word and  new_word.startswith("non"):
            new_word = "non_current_liabilities"
        elif "current_liab" in new_word  and new_word.startswith("current"):
            new_word = "current_liabilities"
        return new_word.strip("_")

    
    
    return None


is_main = lambda x: any(main in x for main in ['assets','liabilities','equity'])


def fix_total_labels(df, value_col, label_col='labels'):
    """
    Fixes rows where value is null by finding a 'total' row below 
    that has the same sum as the subsequent items.
    
    If a main category row (assets/liabilities/equity) has null value,
    and there's a 'total' row below it whose value equals the sum of 
    rows between them, copy the total's value to the null row.
    
    Args:
        df: DataFrame with financial statement data
        value_col: Column name containing numeric values
        label_col: Column name containing labels (default: 'labels')
    
    Returns:
        DataFrame with fixed values
    """
    df = df.copy()
    
    for i, row in df.iterrows():
        # Check if this is a main category row with null value
        if is_main(row[label_col]) and pd.isna(row[value_col]):
            
            # Look for the next 'total' row
            for j in range(i + 1, len(df)):
                next_row = df.iloc[j]
                
                # Found a total row
                if 'total' in next_row[label_col].lower():
                    total_value = next_row[value_col]
                    
                    # Calculate sum of rows between current row and total row
                    sum_between = df.loc[i+1:j-1, value_col].sum()
                    
                    # If the total matches the sum, copy the value
                    if pd.notna(total_value) and abs(total_value - sum_between) < 0.01:
                        df.at[i, value_col] = total_value
                        print(f"Fixed row {i} ('{row[label_col]}'): copied value {total_value} from total row {j}")
                    
                    break  # Stop looking after finding first total
                
                # Stop if we hit another main category
                if is_main(next_row[label_col]):
                    break
    
    return df