import pandas as pd
import io
import pickle
import streamlit as st
import boto3
from botocore.exceptions import ClientError
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


def _parse_s3_path(s3_path):
    """Parse s3://bucket/key into bucket and key"""
    if not s3_path.startswith('s3://'):
        raise ValueError(f"Invalid S3 path: {s3_path}. Must start with 's3://'")
    
    path_parts = s3_path[5:].split('/', 1)
    bucket = path_parts[0]
    key = path_parts[1] if len(path_parts) > 1 else ''
    return bucket, key


def _get_s3_client():
    """Get S3 client with credentials from environment or AWS config"""
    return boto3.client('s3')


def _read_s3_file(s3_path, file_path):
    """Read a file from S3"""
    bucket, base_key = _parse_s3_path(s3_path)
    full_key = f"{base_key}/{file_path}".strip('/')
    
    s3_client = _get_s3_client()
    try:
        response = s3_client.get_object(Bucket=bucket, Key=full_key)
        return response['Body'].read()
    except ClientError as e:
        raise FileNotFoundError(f"File not found in S3: s3://{bucket}/{full_key}") from e


def _file_exists_s3(s3_path, file_path):
    """Check if file exists in S3"""
    bucket, base_key = _parse_s3_path(s3_path)
    full_key = f"{base_key}/{file_path}".strip('/')
    
    s3_client = _get_s3_client()
    try:
        s3_client.head_object(Bucket=bucket, Key=full_key)
        return True
    except ClientError:
        return False


def _is_s3_path(path):
    """Check if path is an S3 path"""
    return isinstance(path, str) and path.startswith('s3://')


def _read_file_local(file_path):
    """Read a file from local filesystem"""
    with open(file_path, 'rb') as f:
        return f.read()


def _file_exists_local(file_path):
    """Check if file exists locally"""
    return Path(file_path).exists()


@st.cache_data(ttl=3600)
def get_available_tickers(metadata_path='metadata.pkl'):
    """
    Get list of all available tickers from metadata file.
    
    Args:
        metadata_path: Path to metadata.pkl file
                      - Local: 'metadata.pkl' or 'path/to/metadata.pkl'
                      - S3: 's3://bucket/path/metadata.pkl'
    
    Returns:
        Sorted list of ticker symbols
    """
    try:
        if _is_s3_path(metadata_path):
            # Read from S3
            metadata_bytes = _read_s3_file(metadata_path, '')
        else:
            # Read from local filesystem
            metadata_bytes = _read_file_local(metadata_path)
        
        metadata_all = pickle.loads(metadata_bytes)
        return sorted(metadata_all.keys())
    except (FileNotFoundError, pickle.UnpicklingError):
        return []


@st.cache_data(ttl=3600)
def load_single_company(ticker, s3_data_path, metadata_path='metadata.pkl'):
    """
    Load company from S3 with local metadata file.
    
    Args:
        ticker: Company ticker symbol (e.g., 'AAPL')
        s3_data_path: S3 path to company data folder (e.g., 's3://my-bucket/company-data')
        metadata_path: Path to local metadata.pkl file (default: 'metadata.pkl')
                      Can also be S3 path if you want metadata in S3
    
    Returns:
        CompanyData object or None if not found
    
    Examples:
        # Load with local metadata
        company = load_single_company('AAPL', 's3://my-bucket/company-data', 'metadata.pkl')
        
        # Load with S3 metadata
        company = load_single_company('AAPL', 's3://my-bucket/company-data', 's3://my-bucket/metadata.pkl')
    """
    # Read metadata
    try:
        if _is_s3_path(metadata_path):
            metadata_bytes = _read_s3_file(metadata_path, '')
        else:
            metadata_bytes = _read_file_local(metadata_path)
        
        metadata_all = pickle.loads(metadata_bytes)
    except (FileNotFoundError, pickle.UnpicklingError):
        return None
    
    if ticker not in metadata_all:
        return None
    
    metadata = metadata_all[ticker]
    
    # Create company object
    company = CompanyData(
        name=metadata['name'],
        years=metadata['years'],
        all_statements=metadata['all_statements']
    )
    
    # Load the company pickle file from S3
    company_pickle_path = f'{ticker}.pkl'
    
    try:
        # Read company pickle from S3
        company_bytes = _read_s3_file(s3_data_path, company_pickle_path)
        company_obj = pickle.loads(company_bytes)
        
        # Copy all attributes from loaded object to our company object
        for attr in dir(company_obj):
            if not attr.startswith('_'):
                setattr(company, attr, getattr(company_obj, attr))
        
        return company
    
    except FileNotFoundError:
        return None


def test_s3_connection(s3_path):
    """
    Test if you can connect to S3 and access the path.
    
    Args:
        s3_path: S3 path like 's3://my-bucket/company-data'
    
    Returns:
        Tuple of (success: bool, message: str)
    
    Example:
        success, message = test_s3_connection('s3://my-bucket/company-data')
        if success:
            print("Connection successful!")
        else:
            print(f"Connection failed: {message}")
    """
    try:
        bucket, key = _parse_s3_path(s3_path)
        s3_client = _get_s3_client()
        
        # Test bucket access
        s3_client.head_bucket(Bucket=bucket)
        
        # List some files to verify access
        prefix = key.strip('/') + '/' if key else ''
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
        
        if 'Contents' not in response:
            return False, f"⚠ Can access bucket but no files found at: {s3_path}"
        
        return True, f"✓ Successfully connected to {s3_path}"
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            return False, f"✗ Bucket or path not found: {s3_path}"
        elif error_code == '403':
            return False, f"✗ Access denied. Check your AWS credentials and IAM permissions."
        else:
            return False, f"✗ Error: {str(e)}"
    
    except Exception as e:
        return False, f"✗ Error: {str(e)}"


def list_s3_companies(s3_data_path):
    """
    List all company pickle files in S3.
    Useful for debugging.
    
    Args:
        s3_data_path: S3 path to company data folder
    
    Returns:
        List of ticker symbols found in S3
    """
    try:
        bucket, key = _parse_s3_path(s3_data_path)
        s3_client = _get_s3_client()
        
        prefix = key.strip('/') + '/' if key else ''
        
        tickers = []
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    file_name = obj['Key'].split('/')[-1]
                    if file_name.endswith('.pkl') and file_name != 'metadata.pkl':
                        ticker = file_name.replace('.pkl', '')
                        tickers.append(ticker)
        
        return sorted(tickers)
    
    except Exception as e:
        print(f"Error listing companies: {e}")
        return []

