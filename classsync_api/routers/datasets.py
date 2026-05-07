"""
Dataset upload and management endpoints.
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Any
import tempfile
import os

from classsync_api.database import get_db
from classsync_api.dependencies import get_institution_id, get_current_user
from classsync_api.schemas import (
    DatasetUploadResponse, DatasetListItem, MessageResponse,
    DatasetValidationResult, DatasetTypeSchema, DatasetStatusSchema, DatasetImportStats, DatasetUploadWithImportResponse,
    DatasetPreviewResponse
)
from classsync_core.models import Dataset, User
from classsync_core.storage import s3_service
from classsync_core.validators import DatasetValidator
from classsync_core.models import DatasetStatus
from classsync_core.importers import CourseImporter, RoomImporter

router = APIRouter(
    prefix="/datasets",
    tags=["Datasets"]
)

@router.post("/upload", response_model=DatasetUploadWithImportResponse)
async def upload_dataset(
        file: UploadFile = File(...),
        dataset_type: DatasetTypeSchema = Query(...,
                                                description="Type of dataset: courses, teachers, rooms, or sections"),
        db: Session = Depends(get_db),
        institution_id: str = Depends(get_institution_id),
        current_user: dict = Depends(get_current_user)
):
    """
    Upload a dataset file (CSV or XLSX).

    Steps:
    1. Validate file type
    2. Save temporarily
    3. Validate file structure and content
    4. Upload to S3
    5. Save metadata to database
    """

    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_ext = file.filename.lower().split('.')[-1]
    if file_ext not in ['csv', 'xlsx', 'xls']:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only CSV and XLSX files are accepted."
        )

    # Get file extension for database
    file_extension = os.path.splitext(file.filename)[1].lower()

    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    # Save to temporary file for validation
    temp_file_path = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        # Validate file
        validator = DatasetValidator(dataset_type.value)
        validation_result = validator.validate_file(temp_file_path)

        # Determine status based on validation - USE LOWERCASE STRING DIRECTLY
        status_value = "VALIDATED" if validation_result.is_valid else "INVALID"

        # Generate S3 key
        s3_key = s3_service.generate_s3_key(
            institution_id=1,  # Hardcoded for now
            filename=file.filename,
            dataset_type=dataset_type.value
        )

        # Upload to S3
        content_type = 'text/csv' if file_ext == 'csv' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        upload_success = s3_service.upload_file(
            file_content=file_content,
            s3_key=s3_key,
            content_type=content_type
        )

        if not upload_success:
            raise HTTPException(status_code=500, detail="Failed to upload file to storage")

        # Save metadata to database
        dataset = Dataset(
            institution_id=1,
            filename=file.filename,
            file_type=file_extension,
            s3_key=s3_key,
            status="VALIDATED" if validation_result.is_valid else "INVALID",
            validation_errors=validation_result.model_dump_json() if not validation_result.is_valid else None,
            row_count=validation_result.total_rows,
            uploaded_by=1
        )

        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        # Import to database if validation passed
        import_result = None
        if validation_result.is_valid:
            import_result = _import_dataset_to_db(
                temp_file_path, dataset_type, db
            )
            
            # Check if import actually succeeded
            if not import_result.success:
                db.rollback() # Ensure rollback of data import
                
                # Mark dataset as invalid since import failed
                dataset.status = "invalid"
                dataset.validation_errors = {"import_errors": import_result.errors}
                db.commit()
                
                raise HTTPException(
                    status_code=422, 
                    detail={
                        "message": "Dataset validation passed but import failed",
                        "errors": import_result.errors,
                        "created": import_result.created_count
                    }
                )

        return DatasetUploadWithImportResponse(
            id=dataset.id,
            filename=dataset.filename,
            file_type=dataset.file_type,
            status=DatasetStatusSchema(dataset.status),
            s3_key=dataset.s3_key,
            row_count=dataset.row_count,
            created_at=dataset.created_at,
            message="Dataset uploaded and imported successfully" if validation_result.is_valid else "Dataset validation failed",
            validation={
                "is_valid": validation_result.is_valid,
                "total_rows": validation_result.total_rows,
                "valid_rows": validation_result.valid_rows,
                "invalid_rows": validation_result.invalid_rows,
                "errors": [error.model_dump() for error in validation_result.errors],
                "warnings": validation_result.warnings
            },
            import_stats=DatasetImportStats(**import_result.to_dict()) if import_result else None
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass


@router.get("/", response_model=List[DatasetListItem])
async def list_datasets(
    dataset_type: Optional[DatasetTypeSchema] = Query(None, description="Filter by dataset type"),
    status: Optional[DatasetStatusSchema] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """
    List all datasets for the institution.

    Optional filters:
    - dataset_type: courses, teachers, rooms, sections
    - status: pending, validated, invalid, processing
    """

    # Build query
    query = db.query(Dataset).filter(
        Dataset.institution_id == 1  # TODO: Use actual institution_id in Phase 9
    )

    # Apply filters
    # Note: We don't have dataset_type column yet, will add in future if needed

    if status:
        query = query.filter(Dataset.status == status.value)

    # Order by most recent first
    query = query.order_by(Dataset.created_at.desc())

    # Limit results
    datasets = query.limit(limit).all()

    return [
        DatasetListItem(
            id=ds.id,
            filename=ds.filename,
            file_type=ds.file_type,
            status=DatasetStatusSchema(ds.status),
            row_count=ds.row_count,
            created_at=ds.created_at,
            uploaded_by=ds.uploaded_by
        )
        for ds in datasets
    ]


@router.get("/{dataset_id}", response_model=DatasetUploadResponse)
async def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """Get details of a specific dataset."""

    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.institution_id == 1  # TODO: Use actual institution_id in Phase 9
    ).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return DatasetUploadResponse(
        id=dataset.id,
        filename=dataset.filename,
        file_type=dataset.file_type,
        status=DatasetStatusSchema(dataset.status),
        s3_key=dataset.s3_key,
        row_count=dataset.row_count,
        validation_errors=dataset.validation_errors,
        created_at=dataset.created_at
    )


@router.delete("/{dataset_id}", response_model=MessageResponse)
async def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """Delete a dataset (removes from database and S3)."""

    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.institution_id == 1  # TODO: Use actual institution_id in Phase 9
    ).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Delete from S3
    s3_success = s3_service.delete_file(dataset.s3_key)
    if not s3_success:
        # Log warning but continue with database deletion
        pass

    # Clear derived data (Single Source of Truth enforcement)
    # Infer type from S3 key: uploads/{id}/{type}/{timestamp}_{filename}
    dataset_type = 'unknown'
    try:
        parts = dataset.s3_key.split('/')
        if len(parts) >= 3:
            dataset_type = parts[2]
    except Exception:
        pass

    try:
        # If it's a course dataset (or unknown/legacy), clear course data
        if dataset_type in ['courses', 'unknown', 'sections', 'teachers']:
            course_importer = CourseImporter(db, institution_id=1)
            course_importer.clear_data()
            print(f"Cleared course/teacher/section data for deleted dataset: {dataset.filename}")
        
        # If it's a room dataset (or unknown), clear room data
        if dataset_type in ['rooms', 'unknown']:
            room_importer = RoomImporter(db, institution_id=1)
            room_importer.clear_data()
            print(f"Cleared room data for deleted dataset: {dataset.filename}")

    except Exception as e:
        print(f"Warning: Failed to clear derived data: {e}")

    # Delete from database
    db.delete(dataset)
    db.commit()

    return MessageResponse(
        message="Dataset deleted successfully",
        details={"dataset_id": dataset_id, "filename": dataset.filename}
    )


@router.get("/{dataset_id}/download")
async def download_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """
    Generate a presigned URL for downloading the dataset file.
    """

    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.institution_id == 1  # TODO: Use actual institution_id in Phase 9
    ).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Generate presigned URL (valid for 1 hour)
    download_url = s3_service.get_file_url(dataset.s3_key, expiration=3600)

    if not download_url:
        raise HTTPException(status_code=500, detail="Failed to generate download URL")

    return {
        "dataset_id": dataset_id,
        "filename": dataset.filename,
        "download_url": download_url,
        "expires_in_seconds": 3600
    }


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
async def preview_dataset(
    dataset_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """
    Preview dataset content with pagination.
    """
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.institution_id == 1  # TODO: Use actual institution_id
    ).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Download file content
    content = s3_service.download_file(dataset.s3_key)
    if not content:
        raise HTTPException(status_code=500, detail="Failed to download file content")

    try:
        import pandas as pd
        import io

        # Read file into DataFrame
        if dataset.filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
            
        # Handle NaN values - replace with None so they become null in JSON
        df = df.where(pd.notnull(df), None)

        total_rows = len(df)
        columns = df.columns.tolist()

        # Apply pagination
        df_page = df.iloc[offset : offset + limit]
        
        # Convert to list of dicts
        rows = df_page.to_dict(orient='records')

        return DatasetPreviewResponse(
            columns=columns,
            rows=rows,
            total_rows=total_rows,
            offset=offset,
            limit=limit
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse dataset: {str(e)}")


def _import_dataset_to_db(file_path: str, dataset_type: DatasetTypeSchema, db: Session) -> Any:
    """
    Import validated dataset into database.

    Args:
        file_path: Path to the validated CSV file
        dataset_type: Type of dataset (courses, rooms, etc.)
        db: Database session

    Returns:
        ImportResult with statistics
    """
    import pandas as pd

    # Read the file
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    # Select appropriate importer - use .value to get string from enum
    if dataset_type.value == 'courses':
        importer = CourseImporter(db, institution_id=1)
        return importer.import_from_dataframe(df)
    elif dataset_type.value == 'rooms':
        importer = RoomImporter(db, institution_id=1)
        return importer.import_from_dataframe(df)
    else:
        # For other types, return empty result for now
        from classsync_core.importers.base_importer import ImportResult
        result = ImportResult()
        result.errors.append(f"Import not implemented for {dataset_type.value}")
        return result