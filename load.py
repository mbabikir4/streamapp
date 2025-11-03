import os
import pickle
import pandas as pd
import streamlit as st
from pathlib import Path


class CompanyData:
    """Class that mimics your original Company class functionality"""
    def __init__(self, name, years, all_statements):
        self.name = name
        self.years = years
        self.all_statements = all_statements
        self.documents = None  # Dict of {year: AWSDocument}
    
    def get_statement_by_year(self, statement, year):
        """Get a specific statement for a specific year from AWSDocument"""
        if self.documents and year in self.documents:
            doc = self.documents[year]
            if hasattr(doc, statement):
                return getattr(doc, statement)
        return None
    
    def get_available_years(self, statement):
        """Get all years where a specific statement is available"""
        if not self.documents:
            return []
        
        available_years = []
        for year in self.years:
            if self.get_statement_by_year(statement, year) is not None:
                available_years.append(year)
        return available_years
    
    def get_notes_tables(self, year):
        """Get notes tables for a specific year"""
        if self.documents and year in self.documents:
            doc = self.documents[year]
            if hasattr(doc, 'notes_tables'):
                return doc.notes_tables
        return []


def save_company_dict_to_files(company_dict, base_dir='company_data'):
    """
    Save each company as an individual pickle file for fast loading.
    
    Args:
        company_dict: Dictionary of {ticker: Company object}
        base_dir: Directory to save all company files
    
    Returns:
        Path to the base directory
    """
    base_path = Path(base_dir)
    base_path.mkdir(exist_ok=True)
    
    metadata_all = {}
    
    for ticker, company_obj in company_dict.items():
        print(f"Saving {ticker}...")
        
        # Save entire company object as pickle
        company_file = base_path / f"{ticker}.pkl"
        with open(company_file, 'wb') as f:
            pickle.dump(company_obj, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Store metadata for quick reference
        metadata_all[ticker] = {
            'name': company_obj.name,
            'years': company_obj.years,
            'all_statements': company_obj.all_statements
        }
    
    # Save metadata index
    metadata_file = base_path / 'metadata.pkl'
    with open(metadata_file, 'wb') as f:
        pickle.dump(metadata_all, f, protocol=pickle.HIGHEST_PROTOCOL)
    
    # Calculate total size
    total_size = sum(f.stat().st_size for f in base_path.glob('*.pkl')) / (1024**2)
    print(f"✓ Saved {len(company_dict)} companies to {base_dir}/ ({total_size:.2f} MB)")
    
    return str(base_path)


@st.cache_data
def get_available_tickers(base_dir='company_data'):
    """
    Get list of all available tickers.
    Much faster than zip version since we only read metadata.
    """
    metadata_file = Path(base_dir) / 'metadata.pkl'
    
    if not metadata_file.exists():
        return []
    
    with open(metadata_file, 'rb') as f:
        metadata_all = pickle.load(f)
    
    return sorted(metadata_all.keys())


@st.cache_data
def load_single_company(ticker, base_dir='company_data'):
    """
    Load a single company from its pickle file.
    This is MUCH faster than zip extraction.
    
    Args:
        ticker: Company ticker symbol
        base_dir: Directory containing company files
    
    Returns:
        CompanyData object with all functionality intact
    """
    company_file = Path(base_dir) / f"{ticker}.pkl"
    
    if not company_file.exists():
        return None
    
    with open(company_file, 'rb') as f:
        company = pickle.load(f)
    
    return company


def load_multiple_companies(tickers, base_dir='company_data'):
    """
    Load multiple companies at once.
    Useful if you need to load several companies.
    
    Args:
        tickers: List of ticker symbols
        base_dir: Directory containing company files
    
    Returns:
        Dictionary of {ticker: CompanyData object}
    """
    companies = {}
    
    for ticker in tickers:
        company = load_single_company(ticker, base_dir)
        if company:
            companies[ticker] = company
    
    return companies


def get_company_metadata(ticker, base_dir='company_data'):
    """
    Get just the metadata for a company without loading the full object.
    Useful for quick lookups.
    
    Args:
        ticker: Company ticker symbol
        base_dir: Directory containing company files
    
    Returns:
        Dictionary with name, years, and all_statements
    """
    metadata_file = Path(base_dir) / 'metadata.pkl'
    
    if not metadata_file.exists():
        return None
    
    with open(metadata_file, 'rb') as f:
        metadata_all = pickle.load(f)
    
    return metadata_all.get(ticker)

