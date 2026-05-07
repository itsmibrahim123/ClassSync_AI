"""
Base importer class with common functionality.
"""

import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from sqlalchemy.orm import Session


class ImportResult:
    """Result of an import operation."""

    def __init__(self):
        self.created_count = 0
        self.updated_count = 0
        self.skipped_count = 0
        self.errors: List[str] = []
        self.created_ids: List[int] = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'created': self.created_count,
            'updated': self.updated_count,
            'skipped': self.skipped_count,
            'total_processed': self.created_count + self.updated_count + self.skipped_count,
            'errors': self.errors,
            'created_ids': self.created_ids
        }

    @property
    def success(self) -> bool:
        """Check if import was successful."""
        return len(self.errors) == 0


class BaseImporter(ABC):
    """Base class for all importers."""

    def __init__(self, db: Session, institution_id: int = 1):
        """
        Initialize importer.

        Args:
            db: Database session
            institution_id: Institution ID for multi-tenancy
        """
        self.db = db
        self.institution_id = institution_id
        self.result = ImportResult()

    @abstractmethod
    def import_from_dataframe(self, df: pd.DataFrame) -> ImportResult:
        """
        Import data from pandas DataFrame.

        Args:
            df: DataFrame with validated data

        Returns:
            ImportResult with statistics
        """
        pass

    def normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize DataFrame columns (lowercase, strip, replace spaces)."""
        df = df.copy()
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

        # Remove NaN values
        df = df.fillna('')

        return df

    def log_error(self, row_num: int, message: str):
        """Log an error for a specific row."""
        self.result.errors.append(f"Row {row_num}: {message}")

    def commit(self):
        """Commit transaction."""
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            self.result.errors.append(f"Commit failed: {str(e)}")
            raise

    def rollback(self):
        """Rollback transaction."""
        self.db.rollback()