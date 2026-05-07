"""
Room importer - creates Room records from validated CSV data.
"""

import pandas as pd
from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from classsync_core.importers.base_importer import BaseImporter, ImportResult
from classsync_core.models import Room, RoomType


class RoomImporter(BaseImporter):
    """Import rooms from validated dataset."""

    def import_from_dataframe(self, df: pd.DataFrame) -> ImportResult:
        """
        Import rooms from DataFrame.

        Args:
            df: DataFrame with columns: rooms, type, capacity (optional)

        Returns:
            ImportResult with statistics
        """
        df = self.normalize_dataframe(df)

        # Validate required columns
        required = ['rooms', 'type']
        missing = [col for col in required if col not in df.columns]
        if missing:
            self.result.errors.append(f"Missing columns: {missing}")
            return self.result

        try:
            # Step 0: Clear existing rooms (Single Source of Truth)
            self.clear_data()
            
            # Process each row
            for idx, row in df.iterrows():
                row_num = idx + 2  # Account for header and 0-indexing

                try:
                    self._import_room(row, row_num)
                except Exception as e:
                    self.log_error(row_num, f"Failed to import: {str(e)}")

            # Commit if no errors
            if self.result.success:
                try:
                    self.commit()
                except Exception as e:
                    self.result.errors.append(f"Commit failed: {str(e)}")
            else:
                self.rollback()
        except Exception as e:
            self.rollback()
            self.result.errors.append(f"Import process failed: {str(e)}")

        return self.result

    def clear_data(self):
        """Soft delete all existing rooms for this institution."""
        now = datetime.utcnow()
        self.db.query(Room).filter(
            Room.institution_id == self.institution_id,
            Room.is_deleted == False
        ).update({Room.is_deleted: True, Room.deleted_at: now})
        self.db.flush()

    def _import_room(self, row: pd.Series, row_num: int):
        """Import a single room."""
        room_code = str(row['rooms']).strip()
        room_type_str = str(row['type']).strip().lower()
        capacity = int(row.get('capacity', 50))

        # Validate room code
        if not room_code:
            self.log_error(row_num, "Room code is empty")
            return

        # Map room type
        room_type_map = {
            'lab': RoomType.LAB,
            'theory': RoomType.LECTURE_HALL,
            'lecture': RoomType.LECTURE_HALL,
            'lecture hall': RoomType.LECTURE_HALL,
            'tutorial': RoomType.TUTORIAL_ROOM,
            'seminar': RoomType.SEMINAR_ROOM
        }

        room_type = room_type_map.get(room_type_str)
        if not room_type:
            self.log_error(row_num, f"Invalid room type: {room_type_str}")
            return

        # Check if room already exists
        existing = self.db.query(Room).filter(
            Room.code == room_code,
            Room.institution_id == self.institution_id,
            Room.is_deleted == False
        ).first()

        if existing:
            # Update existing room
            existing.name = room_code
            existing.room_type = room_type
            existing.capacity = capacity
            self.result.updated_count += 1
        else:
            # Create new room
            room = Room(
                institution_id=self.institution_id,
                code=room_code,
                name=room_code,
                room_type=room_type,
                capacity=capacity,
                is_available=True
            )
            self.db.add(room)
            self.db.flush()  # Get ID without committing

            self.result.created_count += 1
            self.result.created_ids.append(room.id)