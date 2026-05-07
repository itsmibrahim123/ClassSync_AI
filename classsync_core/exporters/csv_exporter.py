"""
CSV exporter for timetables.
"""

import pandas as pd
import os
from typing import Dict, Any

from classsync_core.exports import BaseExporter


class CSVExporter(BaseExporter):
    """Export timetables to CSV format."""

    def export(self, timetable_id: int, output_path: str, **kwargs) -> str:
        """
        Export timetable to CSV file.

        Args:
            timetable_id: ID of timetable to export
            output_path: Path where file should be saved
            **kwargs: Options like 'view_type' (section/teacher/room/master)

        Returns:
            Path to exported file
        """
        view_type = kwargs.get('view_type', 'master')

        # Load data
        df = self.load_timetable_data(timetable_id)

        if df.empty:
            raise ValueError(f"No data found for timetable {timetable_id}")

        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

        if view_type == 'master':
            # Sort by day and time
            day_order = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
                         'Friday': 4, 'Saturday': 5, 'Sunday': 6}
            df['Day_Order'] = df['Weekday'].map(day_order)
            df = df.sort_values(['Day_Order', 'Start_Time']).drop('Day_Order', axis=1)

            # Save to CSV
            df.to_csv(output_path, index=False)
            return output_path

        elif view_type == 'section':
            return self._export_by_group(df, 'Section', output_path)
        elif view_type == 'teacher':
            return self._export_by_group(df, 'Instructor', output_path)
        elif view_type == 'room':
            return self._export_by_group(df, 'Room', output_path)
        else:
            raise ValueError(f"Unknown view type: {view_type}")

    def _export_by_group(self, df: pd.DataFrame, group_by: str, output_path: str) -> str:
        """Export separate CSV files for each group (section/teacher/room)."""

        # Create directory for multiple files
        base_dir = os.path.splitext(output_path)[0]
        os.makedirs(base_dir, exist_ok=True)

        groups = df[group_by].unique()

        for group in sorted(groups):
            group_df = df[df[group_by] == group]

            # Sort by day and time
            day_order = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
                         'Friday': 4, 'Saturday': 5, 'Sunday': 6}
            group_df['Day_Order'] = group_df['Weekday'].map(day_order)
            group_df = group_df.sort_values(['Day_Order', 'Start_Time']).drop('Day_Order', axis=1)

            # Sanitize filename
            safe_name = str(group).replace('/', '_').replace('\\', '_').replace(' ', '_')
            file_path = os.path.join(base_dir, f"{safe_name}.csv")

            group_df.to_csv(file_path, index=False)

        return base_dir