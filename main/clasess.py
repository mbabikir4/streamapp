
import pandas as pd
from textractor import Textractor
from textractor.parsers import response_parser
import json 
# from main.matching_textractor import match_statement_by_line,get_notes_start_page,get_reporting_date
from main.matching_try import match_statement_by_line,get_notes_start_page,get_reporting_date
from main.class_helpers import get_statements
from main.merging import concat_sts
# from main.merging_old import concat_sts
from main.notes import get_notes,numify


class AWSDocument:
    def __init__(self, path):
        self.path = path
        self._get_year()
        self._load_and_parse_document()
        self._identify_statement_pages()
        self._set_statement_start_pages()
        self._extract_statements()
        self._check_december_reporting()
        self._get_table_notes()
        self._match_all_statement_notes()
        
        
        self._finalize_attributes()
        
    def _load_and_parse_document(self):
        """Load JSON response from file and parse the document."""
        with open(self.path, 'r') as file:
            response = json.load(file)
        self.doc = response_parser.parse(response)
    
    def _get_year(self):
        # for now assume same input format but need to change in future
        self.year = self.path.split('_')[-1].split('.')[0]  
        
    def _identify_statement_pages(self):
        """Identify which pages contain which financial statements."""
        self.main_table_page = match_statement_by_line(self.doc)
        # Get unique statement types, filter to max page ~20
        self.all_statements = list(set(self.main_table_page.values()))
        self.notes_start_page = get_notes_start_page(self.doc)
    
    def _set_statement_start_pages(self):
        """Set the starting page number for each statement type."""
        for page_num, statement_type in self.main_table_page.items():
            start_page_attr = f'{statement_type}_START_PAGE'
            if not hasattr(self, start_page_attr):
                setattr(self, start_page_attr, page_num)
    
    def _extract_statements(self):
        """Extract statement data for each identified statement type."""
        for statement_type in self.all_statements:
            start_page_attr = f'{statement_type}_START_PAGE'
            statement_start_page = getattr(self, start_page_attr, None)
            
            if statement_start_page:
                statement_data = get_statements(self, statement_start_page)
                
                ## hardwire dates:
                values_cols = list(filter(lambda x : str(x).isdigit(),statement_data.columns.tolist()))
                year_int = int(self.year)
                if not all(year in values_cols for year in [str(year_int), str(year_int-1)]):
                    if len(values_cols) % 2 == 0:
                        statement_data = statement_data.rename(columns=dict(zip(values_cols, [str(year_int), str(year_int-1), f'{year_int}_r1', f'{year_int-1}_r1'])))
                        
                setattr(self, statement_type, statement_data)
    
    def _finalize_attributes(self):
        """Get list of all public attributes (must be called last in init)."""
        self.attributes = [
            attr for attr in dir(self) 
            if not attr.startswith('__')
        ]
    
    def _check_december_reporting(self):
        """Check if any statement page has December as reporting date."""
        self.december = any(
            get_reporting_date(self.doc.pages[page]) 
            for page in self.main_table_page.keys()
        )
        
    def _get_table_notes(self):
        all_tables = self.doc.tables
        if self.notes_start_page:
            self.notes_tables = list(filter(lambda x: x.page >= self.notes_start_page,all_tables))
        elif self.main_table_page:
            max_statement_page = max(self.main_table_page) 
            threshold = max_statement_page + 2 # assuming no important table in first 2 pages 
            # the threshold is added to ensure that i do not catch a main statement 
            self.notes_tables = list(filter(lambda x: x.page >= threshold,all_tables))
        else:
            self.notes_tables = []

    def _match_all_statement_notes(self):
        """
        Apply note matching to all financial statement tables in the document.
        
        Args:
            year: String year to match against (e.g., '2023')
        
        Returns:
            Dictionary mapping statement types to their DataFrames with matched notes
        """
        results = {}
        self.max_value_col = {}
        self.values_col = {}
        # Iterate through all identified statement types
        for statement_type in self.all_statements:
            # print(f'executing matching notes for {statement_type}')

            if statement_type=='EQUITY':
                continue
            # Get the statement DataFrame
            if hasattr(self, statement_type):
                statement_df = getattr(self, statement_type).copy()
                values_cols = list(filter(lambda x : str(x).isdigit(),statement_df.columns.tolist()))
                # print(statement_df.columns.tolist(),values_cols,statement_type)
                # display(statement_df)
                year = None
                if values_cols:
                    year = max(values_cols, key=int)  # returns max  
                    self.values_col[statement_type] =values_cols
                    self.max_value_col[statement_type] = year 
                else:
                    continue
                statement_df[values_cols] = statement_df[values_cols].map(numify)
                # Check if the statement has a 'notes' column
                if 'notes' in statement_df.columns:
                    # Apply get_notes function
                    statement_df_with_paths = get_notes(self, statement_df, year)
                    # Update the statement attribute with matched paths
                    setattr(self, statement_type, statement_df_with_paths)
                    # Store in results dictionary
                    results[statement_type] = statement_df_with_paths
                   
        self.tables_with_notes_ref = results
    

class Company:
    def __init__(self, name, aws_documents):
        """
        Initialize a Company with multiple years of financial statements.
        
        Args:
            name: Company name/identifier
            aws_documents: Dictionary of {year: AWSDocument}
        """
        self.name = name
        self.documents = aws_documents
        self.years = sorted(aws_documents.keys(),reverse=True)
        
        # Get all unique statement types across all documents
        self.all_statements = self._get_all_statement_types()
        
        # Create merged statements for each statement type
        for statement in self.all_statements:
            try:
                merged_df = self._merge_statement_across_years(statement)
                setattr(self, statement, merged_df)
            except Exception as e:
                print(e)
                print(f"erorr in this statement {statement}")
            
        # Store attributes (exclude private and magic attributes)
        self.attributes = list(filter(lambda x: not x.startswith('__'), dir(self)))
    
    def _get_all_statement_types(self):
        """Get all unique statement types across all documents."""
        all_statements = set()
        for doc in self.documents.values():
            if hasattr(doc, 'all_statements'):
                all_statements.update(doc.all_statements)
        return list(all_statements)
    
    def _merge_statement_across_years(self, statement):
        """
        Merge a specific statement type across all years.
        
        Args:
            statement: Statement type (e.g., 'BALANCE_SHEET')
        
        Returns:
            Merged pandas DataFrame
        """
        sheets_by_year = {}
        
        for year in self.years:
            doc = self.documents[year]
            if hasattr(doc, statement):
                df = getattr(doc, statement)
                if df is not None and not df.empty:
                    sheets_by_year[year] = df
        
        if sheets_by_year:
            # Use the new concat_sts function
            merged = concat_sts(sheets_by_year)
            return merged
        else:
            print(f"No data found for {statement} across all years")
            return pd.DataFrame()
    
    def get_statement_by_year(self, statement, year):
        """
        Get a specific statement for a specific year.
        
        Args:
            statement: Statement type
            year: Year identifier
        
        Returns:
            pandas DataFrame for that year
        """
        if year in self.documents:
            doc = self.documents[year]
            if hasattr(doc, statement):
                return getattr(doc, statement)
        return None
    
    def get_available_years(self, statement):
        """Get all years where a specific statement is available."""
        available_years = []
        for year in self.years:
            if self.get_statement_by_year(statement, year) is not None:
                available_years.append(year)
        return available_years
    
    def __repr__(self):
        return f"Company(name='{self.name}', years={self.years}, statements={self.all_statements})"
    
    