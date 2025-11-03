# on november 1st 2025

from textractor.data.constants import TextractType
from textractor.entities.document import Document
from rapidfuzz import fuzz


def exact_match(text, keywords):
    """
    Check if text exactly matches any keyword (case-insensitive)
    
    Args:
        text: String to match against keywords
        keywords: List of keyword strings to match
        
    Returns:
        bool: True if any keyword matches exactly (ignoring case)
    """
    if not text or not keywords:
        return False
    
    text_lower = text.lower().strip()
    
    for keyword in keywords:
        keyword_lower = keyword.lower().strip()
        if text_lower == keyword_lower:
            return True
    
    return False


def fuzzy_match_partial(text, keywords, threshold=95):
    """
    Check if text fuzzy matches any keyword using rapidfuzz (fast!)
    
    Args:
        text: String to match against keywords
        keywords: List of keyword strings to match
        threshold: Similarity threshold (0 to 100), default 95
        
    Returns:
        bool: True if any keyword matches above threshold
    """
    if not text or not keywords:
        return False
    
    text_lower = text.lower().strip()
    
    for keyword in keywords:
        keyword_lower = keyword.lower().strip()
        
        # Try partial_ratio (good for substring matching)
        partial_score = fuzz.partial_ratio(keyword_lower, text_lower)
        if partial_score >= threshold:
            return True
        
        # Also try token_sort_ratio (good for word order differences)
        token_score = fuzz.token_sort_ratio(keyword_lower, text_lower)
        if token_score >= threshold:
            return True
    
    return False


def fuzzy_match(text, keywords, threshold=90):
    """
    Check if text fuzzy matches any keyword using rapidfuzz (fast!)
    
    Args:
        text: String to match against keywords
        keywords: List of keyword strings to match
        threshold: Similarity threshold (0 to 100), default 95
        
    Returns:
        bool: True if any keyword matches above threshold
    """
    if not text or not keywords:
        return False
    
    text_lower = text.lower().strip()
    
    for keyword in keywords:
        keyword_lower = keyword.lower().strip()
        
        # Use ratio for full string comparison (no partial matching)
        full_score = fuzz.ratio(keyword_lower, text_lower)
        if full_score >= threshold:
            return True
        
        # Or use token_sort_ratio (handles word order but not partial matches)
        token_score = fuzz.token_sort_ratio(keyword_lower, text_lower)
        if token_score >= threshold:
            return True
    
    return False

def match_text(text, keywords, threshold=90):
    """
    Match text against keywords - tries exact match first, then fuzzy match
    
    Args:
        text: String to match against keywords
        keywords: List of keyword strings to match
        threshold: Similarity threshold for fuzzy matching (0 to 100), default 95
        
    Returns:
        bool: True if text matches (exactly or fuzzily)
    """
    # Try exact match first
    if exact_match(text, keywords):
        return True
    
    # Fall back to fuzzy match
    return fuzzy_match(text, keywords, threshold)


# Statement title patterns
BALANCE_SHEET = [
    "STATEMENT OF FINANCIAL POSITION",
    "BALANCE SHEET"
]

TITLES_OF_PROFIT = [
    "STATEMENT OF PROFIT OR LOSS",
    "INCOME STATEMENT",
    "PROFIT AND LOSS STATEMENT"
]

STATEMENT_OF_COMPREHENSIVE_INCOME = [
    "STATEMENT OF COMPREHENSIVE INCOME",
    "COMPREHENSIVE INCOME STATEMENT"
]

STATEMENT_OF_EQUITY = [
    "STATEMENT OF CHANGES IN EQUITY",
    "EQUITY STATEMENT",
    "CHANGES IN EQUITY",
    "CHANGE IN EQUITY",
]

CASH_FLOW = [
    "STATEMENT OF CASH FLOWS",
    "CASH FLOW STATEMENT"
]

NOTES_STATEMENT = [
    "Notes to the Financial Statements",
    "Notes to the Consolidated Financial Statements",
    "Notes to the Accounts",
    "Financial Statement Notes",
    "Notes to the Annual Financial Statements",
    "Schedule of Notes to the Financial Statements",
    "Explanatory Notes",
    "Notes and Disclosures",
    "Accounting Policies and Notes",
    "Notes to Financial Statements Detail",
    "Supplementary Notes"
]

# Keyword matching patterns
balance_sheet_keywords = [
    "current assets", "cash and cash equivalents", "accounts receivable", "inventory",
    "current liabilities", "accounts payable", "short-term debt",
    "shareholder equity", "retained earnings", "common stock"
]

income_statement_keywords = [
    "sales revenue", "service revenue", 
    "cost of goods sold", "operating expenses", "administrative expenses",
    "gross profit", "operating income", "net income"
]

comprehensive_income_keywords = [
    "net income", "other comprehensive income",
    "foreign currency translation adjustments", "unrealized gains", "unrealized losses",
    "total comprehensive income"
]

changes_in_equity_keywords = [
    "opening balance", "total comprehensive income", 
    "dividends paid", "share issuances", "share repurchases",
    "closing balance"
]

cash_flow_keywords = [
    "operating activities", "cash received from customers", "cash paid to suppliers",
    "investing activities", "purchase of fixed assets", "sales of investments",
    "financing activities", "proceeds from issuing debt", "payments of dividends"
]


def has_table_on_page(page):
    """
    Check if a page contains any tables
    
    Args:
        page: Textractor Page object
        
    Returns:
        bool: True if page has tables, False otherwise
    """
    return len(page.tables) > 0


def match_statement_by_line(document):
    """
    Match financial statements by analyzing line text at the top of pages with tables
    Uses exact matching first, then fuzzy matching to handle typos and variations
    
    Args:
        document: Textractor Document object
        
    Returns:
        dict: Dictionary mapping page numbers to statement types
    """
    listOfMents = {}
    
    for page in document.pages:
        page_num = page.page_num
        
        # Check if page has tables
        if not has_table_on_page(page):
            continue
        
        # Iterate through lines on the page
        for line in page.lines:
            # Check if line is in the top 15% of the page
            # bbox returns a BoundingBox object with x, y, width, height
            if line.bbox.y < 0.15:
                text = line.text
                
                # Match against statement patterns using exact match first, then fuzzy matching
                # Use elif to prevent multiple matches on same page
                if match_text(text, BALANCE_SHEET):
                    listOfMents[page_num] = "BALANCE_SHEET"
                elif match_text(text, TITLES_OF_PROFIT):
                    # print(f'matched on this text {text} for this page {page_num}')
                    listOfMents[page_num] = "INCOME_STATEMENT"
                elif match_text(text, STATEMENT_OF_COMPREHENSIVE_INCOME):
                    listOfMents[page_num] = "COMPREHENSIVE_INCOME_STATEMENT"
                elif match_text(text, STATEMENT_OF_EQUITY):
                    listOfMents[page_num] = "EQUITY"
                elif match_text(text, CASH_FLOW):
                    listOfMents[page_num] = "CASH_FLOW"
    
    return listOfMents


def get_notes_start_page(document):
    """
    Find the page where notes to financial statements begin
    
    Args:
        document: Textractor Document object
        
    Returns:
        int: Page number where notes start, or 0 if not found
    """
    for page in document.pages:
        for line in page.lines:
            # Check if line is in the top 10% of the page and contains "notes"
            # bbox.y represents the top position
            if line.bbox.y < 0.1 and "notes" in line.text.lower():
                return page.page_num
    
    return 0


def get_reporting_date(page):
    
    for line in page.lines:
        if line.bbox.y < 0.4:  # Added 'if'
            if 'december' in line.text.lower():  # Changed to 'in'
                return True
    return False
    

