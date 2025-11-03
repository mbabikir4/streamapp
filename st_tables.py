import streamlit as st
import pandas as pd
from typing import List


def display_table_with_expandable_rows(df: pd.DataFrame, path_column: str, tables_list: List[pd.DataFrame]):
    """
    Display a dataframe with expandable rows for nested tables.
    
    Args:
        df: Main dataframe to display
        path_column: Name of the column containing the path indices (as lists)
        tables_list: List of dataframes that can be referenced by the path indices
    
    Example:
        tables = [df1, df2, df3]  # List of nested dataframes
        display_table_with_expandable_rows(main_df, 'path', tables)
    """
    # Get all columns
    columns = df.columns.tolist()
    
    # Display header row
    header_cols = st.columns(len(columns))
    for col_idx, col_name in enumerate(columns[:-1]):
        header_cols[col_idx].markdown(f"**{col_name}**")
    st.divider()
    
    # Display each row
    for idx, row in df.iterrows():
        # Create columns for the main row data
        cols = st.columns(len(columns))
        
        # Display each cell
        for col_idx, col_name in enumerate(columns[:-1]):
            cols[col_idx].write(row[col_name])
        
        # Get the path value (should be a list)
        path_value = row[path_column]
        
        # Check if path is a list and not empty
        if isinstance(path_value, list) and len(path_value) > 0:
            # Create an expander for nested tables
            with st.expander(f" Note Tables for {row.get('labels', f'Row {idx}')}"):
                # Get valid tables
                valid_tables = []
                for table_idx in path_value:
                    if 0 <= table_idx < len(tables_list):
                        valid_tables.append((table_idx, tables_list[table_idx]))
                
                # Display tables side by side if multiple tables
                if len(valid_tables) > 1:
                    table_cols = st.columns(len(valid_tables))
                    for col_idx, (table_idx, table_df) in enumerate(valid_tables):
                        with table_cols[col_idx]:
                            st.markdown(f"**Table {table_idx}:**")
                            st.dataframe(table_df, width='stretch')
                            
                elif len(valid_tables) == 1:
                    # Single table - use full width
                    table_idx, table_df = valid_tables[0]
                    st.markdown(f"**Table {table_idx}:**")
                    st.dataframe(table_df,width='stretch')
                    # For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.
                    # use_container_width=True
        # Add a divider between rows
        st.divider()

def display_table_with_button_dropdowns(df: pd.DataFrame, path_column: str, tables_list: List[pd.DataFrame]):
    """
    Display a dataframe with button dropdowns in the path column for nested tables.
    
    Args:
        df: Main dataframe to display
        path_column: Name of the column containing the path indices (as lists)
        tables_list: List of dataframes that can be referenced by the path indices
    
    Example:
        tables = [df1, df2, df3]  # List of nested dataframes
        display_table_with_button_dropdowns(main_df, 'path', tables)
    """
    # Get all columns
    columns = df.columns.tolist()
    path_col_idx = columns.index(path_column)
    
    # Display header
    header_cols = st.columns(len(columns))
    for col_idx, col_name in enumerate(columns):
        header_cols[col_idx].markdown(f"**{col_name}**")
    st.divider()
    
    # Display each row
    for idx, row in df.iterrows():
        cols = st.columns(len(columns))
        
        # Display each cell
        for col_idx, col_name in enumerate(columns):
            if col_name == path_column:
                # Handle the path column specially
                path_value = row[col_name]
                
                # Check if path is a list and not empty
                if isinstance(path_value, list) and len(path_value) > 0:
                    # Create a button
                    button_label = f"📋 {path_value}"
                    if cols[col_idx].button(button_label, key=f"btn_{idx}_{path_column}"):
                        # Toggle the state
                        st.session_state[f"show_table_{idx}"] = not st.session_state.get(f"show_table_{idx}", False)
                else:
                    # Display empty or non-list values normally
                    cols[col_idx].write(path_value)
            else:
                # Display other columns normally
                cols[col_idx].write(row[col_name])
        
        # Show nested tables if button was clicked
        path_value = row[path_column]
        if st.session_state.get(f"show_table_{idx}", False):
            if isinstance(path_value, list) and len(path_value) > 0:
                # Display all tables referenced in the path
                for table_idx in path_value:
                    if 0 <= table_idx < len(tables_list):
                        st.markdown(f"**Table {table_idx}:**")
                        st.dataframe(tables_list[table_idx], use_container_width=True)
                        if len(path_value) > 1:  # Add spacing if multiple tables
                            st.markdown("---")
        
        st.divider()


