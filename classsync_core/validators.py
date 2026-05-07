"""
Dataset validation logic for uploaded files.
"""

import pandas as pd
from typing import List, Dict, Any, Tuple
from classsync_api.schemas import (
    DatasetValidationError, DatasetValidationResult,
    CourseDataRow, TeacherDataRow, RoomDataRow, SectionDataRow
)
from pydantic import ValidationError


class DatasetValidator:
    """Validates uploaded dataset files."""

    # Required columns for each dataset type (normalized - lowercase with underscores)
    REQUIRED_COLUMNS = {
        'courses': ['course_name', 'instructor', 'section', 'program', 'type', 'hours_per_week'],
        'teachers': ['teacher_code', 'teacher_name'],
        'rooms': ['rooms', 'type'],
        'sections': ['section_code', 'course_code', 'semester', 'year']
    }

    # Pydantic models for validation
    ROW_MODELS = {
        'courses': CourseDataRow,
        'teachers': TeacherDataRow,
        'rooms': RoomDataRow,
        'sections': SectionDataRow
    }

    def __init__(self, dataset_type: str):
        """
        Initialize validator for specific dataset type.

        Args:
            dataset_type: One of 'courses', 'teachers', 'rooms', 'sections'
        """
        if dataset_type not in self.REQUIRED_COLUMNS:
            raise ValueError(f"Invalid dataset_type: {dataset_type}")

        self.dataset_type = dataset_type
        self.required_columns = self.REQUIRED_COLUMNS[dataset_type]
        self.row_model = self.ROW_MODELS[dataset_type]

    def validate_file(self, file_path: str) -> DatasetValidationResult:
        """
        Validate a CSV/XLSX file.

        Args:
            file_path: Path to the file to validate

        Returns:
            DatasetValidationResult with validation status and errors
        """
        errors: List[DatasetValidationError] = []
        warnings: List[str] = []

        try:
            # Read file based on extension
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                return DatasetValidationResult(
                    is_valid=False,
                    total_rows=0,
                    valid_rows=0,
                    invalid_rows=0,
                    errors=[DatasetValidationError(
                        error_type="invalid_format",
                        message="File must be CSV or XLSX format"
                    )]
                )

            # Normalize column names (strip whitespace, lowercase)
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

            total_rows = len(df)

            # Check if file is empty
            if total_rows == 0:
                errors.append(DatasetValidationError(
                    error_type="empty_file",
                    message="File contains no data rows"
                ))
                return DatasetValidationResult(
                    is_valid=False,
                    total_rows=0,
                    valid_rows=0,
                    invalid_rows=0,
                    errors=errors
                )

            # Validate column structure
            missing_columns = self._check_missing_columns(df)
            if missing_columns:
                errors.append(DatasetValidationError(
                    error_type="missing_columns",
                    message=f"Missing required columns: {', '.join(missing_columns)}",
                    suggestion=f"Add these columns to your file: {', '.join(missing_columns)}"
                ))

            # Check for extra columns (warning only)
            extra_columns = self._check_extra_columns(df)
            if extra_columns:
                warnings.append(f"Extra columns found (will be ignored): {', '.join(extra_columns)}")

            # If critical structural errors, stop here
            if missing_columns:
                return DatasetValidationResult(
                    is_valid=False,
                    total_rows=total_rows,
                    valid_rows=0,
                    invalid_rows=total_rows,
                    errors=errors,
                    warnings=warnings
                )

            # Validate each row
            row_errors = self._validate_rows(df)
            errors.extend(row_errors)

            # Check for duplicates
            duplicate_errors = self._check_duplicates(df)
            errors.extend(duplicate_errors)

            # Calculate valid/invalid rows
            invalid_row_numbers = set(err.row for err in errors if err.row is not None)
            invalid_rows = len(invalid_row_numbers)
            valid_rows = total_rows - invalid_rows

            is_valid = len(errors) == 0

            return DatasetValidationResult(
                is_valid=is_valid,
                total_rows=total_rows,
                valid_rows=valid_rows,
                invalid_rows=invalid_rows,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            return DatasetValidationResult(
                is_valid=False,
                total_rows=0,
                valid_rows=0,
                invalid_rows=0,
                errors=[DatasetValidationError(
                    error_type="file_read_error",
                    message=f"Failed to read file: {str(e)}"
                )]
            )

    def _check_missing_columns(self, df: pd.DataFrame) -> List[str]:
        """Check for missing required columns."""
        df_columns = set(df.columns)
        required = set(self.required_columns)
        missing = required - df_columns
        return list(missing)

    def _check_extra_columns(self, df: pd.DataFrame) -> List[str]:
        """Check for extra columns (not required, just FYI)."""
        df_columns = set(df.columns)
        # Get all possible columns from the Pydantic model
        model_fields = set(self.row_model.model_fields.keys())
        extra = df_columns - model_fields
        return list(extra)

    def _validate_rows(self, df: pd.DataFrame) -> List[DatasetValidationError]:
        """Validate each row against Pydantic model."""
        errors = []

        for idx, row in df.iterrows():
            row_num = idx + 2  # +2 because: pandas is 0-indexed, and we skip header row
            row_dict = row.to_dict()

            # Remove NaN values (pandas uses NaN for missing values)
            row_dict = {k: v for k, v in row_dict.items() if pd.notna(v)}

            try:
                # Validate using Pydantic model
                self.row_model(**row_dict)
            except ValidationError as e:
                for error in e.errors():
                    field = error['loc'][0] if error['loc'] else 'unknown'
                    errors.append(DatasetValidationError(
                        row=row_num,
                        column=str(field),
                        error_type="validation_error",
                        message=error['msg'],
                        suggestion=self._get_suggestion(field, error['type'])
                    ))
            except Exception as e:
                errors.append(DatasetValidationError(
                    row=row_num,
                    error_type="validation_error",
                    message=f"Row validation failed: {str(e)}"
                ))

        return errors

    def _check_duplicates(self, df: pd.DataFrame) -> List[DatasetValidationError]:
        """Check for duplicate codes."""
        errors = []

        # Define primary key column for each dataset type
        primary_key_map = {
            'courses': 'course_code',
            'teachers': 'teacher_code',
            'rooms': 'room_code',
            'sections': 'section_code'
        }

        primary_key = primary_key_map.get(self.dataset_type)
        if not primary_key or primary_key not in df.columns:
            return errors

        # Find duplicates
        duplicates = df[df.duplicated(subset=[primary_key], keep=False)]

        if not duplicates.empty:
            duplicate_codes = duplicates[primary_key].unique()
            for code in duplicate_codes:
                duplicate_rows = df[df[primary_key] == code].index + 2  # +2 for row numbers
                errors.append(DatasetValidationError(
                    column=primary_key,
                    error_type="duplicate",
                    message=f"Duplicate {primary_key}: '{code}' found in rows: {list(duplicate_rows)}",
                    suggestion=f"Each {primary_key} must be unique. Please remove or rename duplicates."
                ))

        return errors

    def _get_suggestion(self, field: str, error_type: str) -> str:
        """Generate helpful suggestion based on error type."""
        suggestions = {
            'missing': f"The '{field}' field is required and cannot be empty.",
            'type_error': f"The '{field}' field has an invalid data type.",
            'value_error': f"The '{field}' field contains an invalid value.",
        }

        for key, msg in suggestions.items():
            if key in error_type:
                return msg

        return "Please check the value and format for this field."