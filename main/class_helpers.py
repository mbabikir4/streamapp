import pandas as pd
from main.statement_modification_annual import adjust_header
from collections import defaultdict



def get_tables_for_page(AWSDocument1,page):
    return list(filter(lambda x: x.page==page,AWSDocument1.doc.tables))

##########################################################################################


def get_statements(AWSDocument1, statement_page):
    """
    Extract and combine tables from AWS Textractor document based on statement type.
    Assuming all statements are in one page for now, will revise later to ensure that as before works on multiple pages
    
    Args:
        aws_document: Textractor Document object
        statement_type: String identifier for the statement (e.g., 'BALANCE_SHEET', 'INCOME_STATEMENT')
    
    Returns:
        pandas DataFrame with combined statement data
    """
    statement_dfs = get_tables_for_page(AWSDocument1,statement_page)
    if AWSDocument1.main_table_page[statement_page]==AWSDocument1.main_table_page.get(statement_page+1,0):
            statement_dfs = get_tables_for_page(AWSDocument1,statement_page+1)
            
    statement_dfs = [table.to_pandas().pipe(adjust_header) for table in statement_dfs ]
    # Combine all matching statement tables
    if statement_dfs:
        combined_df = pd.concat(statement_dfs, ignore_index=True)
        return combined_df
    else:
        # print(f"No {statement_type} found in document")
        return pd.NA