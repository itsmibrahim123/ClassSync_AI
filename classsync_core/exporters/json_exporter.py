"""
JSON exporter for timetables.
"""

import json
import os
from typing import Dict, Any, List

from classsync_core.exports import BaseExporter


class JSONExporter(BaseExporter):
    """Export timetables to JSON format."""

    def export(self, timetable_id: int, output_path: str, **kwargs) -> str:
        """
        Export timetable to JSON file.

        Args:
            timetable_id: ID of timetable to export
            output_path: Path where file should be saved
            **kwargs: Options like 'view_type' and 'format' (flat/structured)

        Returns:
            Path to exported file
        """
        view_type = kwargs.get('view_type', 'master')
        format_type = kwargs.get('format', 'structured')

        # Load data
        df = self.load_timetable_data(timetable_id)

        if df.empty:
            raise ValueError(f"No data found for timetable {timetable_id}")

        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

        if format_type == 'flat':
            # Simple flat array of entries
            data = df.to_dict(orient='records')
        else:
            # Structured format (grouped by day)
            data = self._create_structured_format(df)

        # Write JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return output_path

    def _create_structured_format(self, df) -> Dict[str, Any]:
        """Create structured JSON format grouped by days."""

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        result = {
            'metadata': {
                'semester': df['Semester'].iloc[0] if not df.empty else None,
                'year': int(df['Year'].iloc[0]) if not df.empty else None,
                'total_entries': len(df)
            },
            'schedule': {}
        }

        for day in days:
            day_df = df[df['Weekday'] == day].sort_values('Start_Time')

            if day_df.empty:
                continue

            result['schedule'][day] = [
                {
                    'time': f"{row['Start_Time']} - {row['End_Time']}",
                    'course': {
                        'code': row['Course_Code'],
                        'name': row['Course_Name']
                    },
                    'section': row['Section'],
                    'instructor': {
                        'name': row['Instructor'],
                        'code': row.get('Teacher_Code', 'N/A')
                    },
                    'room': {
                        'code': row['Room'],
                        'type': row['Room_Type'],
                        'building': row.get('Building', 'N/A')
                    },
                    'duration_minutes': int(row['Duration_Minutes'])
                }
                for _, row in day_df.iterrows()
            ]

        return result