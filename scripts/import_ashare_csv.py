"""
Import A-share stock information from ashare.csv into PostgreSQL
Reads ashare.csv and creates records in ashare_stock_info table
"""
import os
import sys
import pandas as pd
from tqdm import tqdm
from typing import Dict

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.models.base import Base, engine, SessionLocal
from database.models.models import AShareStockInfo


# Exchange name to suffix mapping
EXCHANGE_MAPPING: Dict[str, str] = {
    'Shanghai Stock Exchange': 'SH',
    'SSE': 'SH',
    'Shenzhen Stock Exchange': 'SZ',
    'SZSE': 'SZ',
    'Beijing Stock Exchange': 'BJ',
}


def map_exchange_to_suffix(exchange_name: str) -> str:
    """Map exchange name to suffix (SH/SZ/BJ)"""
    return EXCHANGE_MAPPING.get(exchange_name, '')


def format_symbol(stock_code: str, exchange_suffix: str) -> str:
    """Format stock code as symbol with suffix (e.g., 002788.SZ)"""
    # Remove quotes if present
    code = str(stock_code).strip().strip('"').strip("'")

    # Pad with leading zeros if needed (6 digits for standard codes)
    if code.isdigit() and len(code) <= 6:
        code = code.zfill(6)

    # Combine with suffix
    return f"{code}.{exchange_suffix}" if exchange_suffix else code


def clean_csv_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate CSV data"""
    # Remove leading/trailing whitespace and quotes
    df['exchange_name'] = df['exchange_name'].str.strip().str.strip('"').str.strip("'")
    df['zh_company_abbr'] = df['zh_company_abbr'].str.strip().str.strip('"').str.strip("'")
    df['stock_code'] = df['stock_code'].astype(str).str.strip().str.strip('"').str.strip("'")

    # Remove rows with missing critical data
    df = df.dropna(subset=['exchange_name', 'stock_code'])

    # Remove duplicates based on stock_code
    df = df.drop_duplicates(subset=['stock_code'], keep='first')

    return df


def import_ashare_csv(csv_path: str = 'ashare.csv', batch_size: int = 50):
    """
    Import A-share stock information from CSV file

    Args:
        csv_path: Path to ashare.csv file
        batch_size: Number of records to process per batch
    """
    # Check if file exists
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return

    print(f"Reading CSV file: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"Total records in CSV: {len(df)}")

    # Clean data
    df = clean_csv_data(df)
    print(f"Records after cleaning: {len(df)}")

    # Map exchange names to suffixes
    df['exchange_suffix'] = df['exchange_name'].apply(map_exchange_to_suffix)

    # Remove rows with invalid exchange names
    df = df[df['exchange_suffix'] != '']
    print(f"Records with valid exchanges: {len(df)}")

    # Format symbols
    df['symbol'] = df.apply(
        lambda row: format_symbol(row['stock_code'], row['exchange_suffix']),
        axis=1
    )

    # Create database session
    session = SessionLocal()

    try:
        # Create table if not exists
        Base.metadata.create_all(engine)
        print("Database table ready")

        # Import records in batches
        total_imported = 0
        total_updated = 0
        total_failed = 0

        for idx in tqdm(range(0, len(df), batch_size), desc="Importing batches"):
            batch_df = df.iloc[idx:idx + batch_size]

            for _, row in batch_df.iterrows():
                try:
                    # Check if record exists
                    existing = session.query(AShareStockInfo).filter_by(
                        symbol=row['symbol']
                    ).first()

                    if existing:
                        # Update existing record
                        existing.stock_code = row['stock_code']
                        existing.zh_company_abbr = row['zh_company_abbr']
                        existing.exchange_name = row['exchange_name']
                        existing.exchange_suffix = row['exchange_suffix']
                        total_updated += 1
                    else:
                        # Create new record
                        record = AShareStockInfo(
                            symbol=row['symbol'],
                            stock_code=row['stock_code'],
                            zh_company_abbr=row['zh_company_abbr'],
                            exchange_name=row['exchange_name'],
                            exchange_suffix=row['exchange_suffix']
                        )
                        session.add(record)
                        total_imported += 1

                except Exception as e:
                    print(f"Error processing symbol {row['symbol']}: {e}")
                    total_failed += 1
                    continue

            # Commit batch
            session.commit()

        print(f"\nImport Summary:")
        print(f"  Total records processed: {len(df)}")
        print(f"  New records imported: {total_imported}")
        print(f"  Existing records updated: {total_updated}")
        print(f"  Failed: {total_failed}")
        print(f"  Success rate: {((len(df) - total_failed) / len(df) * 100):.2f}%")

        # Verify import
        total_count = session.query(AShareStockInfo).count()
        print(f"\nTotal records in database: {total_count}")

    except Exception as e:
        session.rollback()
        print(f"Error during import: {e}")
        raise
    finally:
        session.close()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Import A-share stock info from CSV')
    parser.add_argument(
        '--csv',
        type=str,
        default='ashare.csv',
        help='Path to ashare.csv file (default: ashare.csv)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Batch size for processing (default: 50)'
    )

    args = parser.parse_args()

    import_ashare_csv(args.csv, args.batch_size)


if __name__ == '__main__':
    main()
