#!/usr/bin/env python3
"""
GenProject - CSV Template Processor

This script processes a data CSV file to generate multiple project folders
with customized CSV and JSON files based on templates.

Usage:
    python genproject.py <data_csv_file> [--rows <row_specification>]

Examples:
    python genproject.py data.csv                    # Process all rows
    python genproject.py data.csv --rows 2           # Process only row 2
    python genproject.py data.csv --rows 2,4,6       # Process rows 2, 4, 6
    python genproject.py data.csv --rows 3-7         # Process rows 3-7
    python genproject.py data.csv --rows 2,4,8-12,15 # Mixed format

Requirements:
- Data CSV with headers: project_name, template_file, json_file, [custom_columns...]
- Template CSV files in assets/templates/ folder with $(column_name) placeholders
- JSON files in assets/templates/ folder to be copied as config.json
"""

import csv
import json
import os
import sys
import shutil
import re
import argparse
from pathlib import Path


class GenProjectProcessor:
    def __init__(self, data_csv_path, selected_rows=None):
        self.data_csv_path = data_csv_path
        self.selected_rows = selected_rows  # List of row numbers to process (1-based)
        self.data_rows = []
        self.headers = []
        self.templates_dir = Path("assets") / "templates"
        self.workspace_dir = Path("workspace")

    def validate_input_file(self, file_path, file_type):
        """Validate that input file exists and is readable"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{file_type} file not found: {file_path}")

        if not os.path.isfile(file_path):
            raise ValueError(f"{file_type} path is not a file: {file_path}")

    def validate_workspace_directory(self):
        """Validate and create workspace directory if it doesn't exist"""
        try:
            self.workspace_dir.mkdir(parents=True, exist_ok=True)
            print(f"Validated/created workspace directory: {self.workspace_dir}")
        except Exception as e:
            raise RuntimeError(f"Error creating workspace directory {self.workspace_dir}: {str(e)}")

    def validate_templates_directory(self):
        """Validate that assets/templates directory exists"""
        if not self.templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {self.templates_dir}")

        if not self.templates_dir.is_dir():
            raise ValueError(f"Templates path is not a directory: {self.templates_dir}")

    def parse_row_specification(self, row_spec):
        """Parse row specification string into list of row numbers"""
        if not row_spec:
            return None

        row_numbers = []
        parts = row_spec.split(',')

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check if it's a range (contains hyphen)
            if '-' in part:
                range_parts = part.split('-')
                if len(range_parts) != 2:
                    raise ValueError(f"Invalid range format: {part}")

                try:
                    start = int(range_parts[0])
                    end = int(range_parts[1])
                except ValueError:
                    raise ValueError(f"Non-numeric values in range: {part}")

                if start > end:
                    raise ValueError(f"Invalid range (start > end): {part}")

                if start < 2:
                    raise ValueError(f"Row numbers must start from 2: {part}")

                row_numbers.extend(range(start, end + 1))
            else:
                # Single row number
                try:
                    row_num = int(part)
                except ValueError:
                    raise ValueError(f"Non-numeric row number: {part}")

                if row_num < 2:
                    raise ValueError(f"Row numbers must start from 2: {row_num}")

                row_numbers.append(row_num)

        return sorted(list(set(row_numbers)))  # Remove duplicates and sort

    def validate_row_numbers(self):
        """Validate that selected row numbers are within range"""
        if not self.selected_rows:
            return

        max_row = len(self.data_rows) + 1  # +1 because rows start from 2
        for row_num in self.selected_rows:
            if row_num > max_row:
                raise ValueError(f"Row number {row_num} is out of range (max: {max_row})")

    def load_data_csv(self):
        """Load and validate the main data CSV file"""
        print(f"Loading data CSV: {self.data_csv_path}")

        self.validate_input_file(self.data_csv_path, "Data CSV")

        try:
            with open(self.data_csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                self.headers = next(reader)

                # Validate minimum required columns
                if len(self.headers) < 3:
                    raise ValueError("Data CSV must have at least 3 columns: project_name, template_file, json_file")

                self.data_rows = list(reader)

                if not self.data_rows:
                    raise ValueError("Data CSV contains no data rows")

        except Exception as e:
            raise RuntimeError(f"Error reading data CSV: {str(e)}")

        total_rows = len(self.data_rows)
        print(f"Loaded {total_rows} data rows with headers: {self.headers}")

        # Validate selected rows are within range
        self.validate_row_numbers()

        if self.selected_rows:
            print(f"Will process rows: {self.selected_rows}")
        else:
            print(f"Will process all rows (2-{total_rows + 1})")

    def get_template_path(self, template_filename):
        """Get full path to template file in assets/templates directory"""
        template_path = self.templates_dir / template_filename
        return template_path

    def get_json_path(self, json_filename):
        """Get full path to JSON file in assets/templates directory"""
        json_path = self.templates_dir / json_filename
        return json_path

    def process_template_csv(self, template_filename: str, replacement_values: dict[str, str]) -> list[list[str]]:
        """
        Process template CSV by replacing placeholders with actual values

        Args:
            template_filename (str): Name of the template CSV file to process
            replacement_values (dict[str, str]): Dictionary of column headers to replacement values

        Returns:
            list[list[str]]: Processed template rows with placeholders replaced
        """
        template_path = self.get_template_path(template_filename)
        print(f"  Processing template: {template_path}")

        self.validate_input_file(template_path, "Template CSV")

        # Read template content using CSV reader to handle existing escaping
        try:
            with open(template_path, 'r', newline='', encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                template_rows = list(csv_reader)
        except Exception as e:
            raise RuntimeError(f"Error reading template CSV {template_path}: {str(e)}")

        # Validate template has rows
        if not template_rows:
            raise ValueError(f"Template CSV {template_path} is empty")

        # Process rows with line break and placeholder handling
        processed_rows = []
        for row_index, row in enumerate(template_rows):
            # Check if row has placeholders
            placeholders_in_row = []
            for col_index, cell in enumerate(row):
                found_placeholders = re.findall(r'\$\(([^)]+)\)', cell)
                if found_placeholders:
                    placeholders_in_row.extend(
                        (col_index, placeholder) for placeholder in found_placeholders
                    )

            # If no placeholders, keep row as is
            if not placeholders_in_row:
                processed_rows.append(row)
                continue

            # Validate that all placeholders have corresponding headers
            for col_index, placeholder in placeholders_in_row:
                if placeholder not in self.headers:
                    raise ValueError(f"Placeholder '$(​{placeholder})' in template {template_path} has no matching column header in data CSV")

            # Prepare the processed rows for this template row
            for col_index, placeholder in placeholders_in_row:
                replacement = str(replacement_values.get(placeholder, ''))
                pattern = f'$({placeholder})'
                row[col_index] = row[col_index].replace(pattern, replacement)

            processed_rows.append(row)

        return processed_rows

    def copy_json_file(self, json_filename, output_path):
        """Copy JSON file from assets/templates to output location"""
        json_path = self.get_json_path(json_filename)
        print(f"  Copying JSON: {json_path} -> {output_path}")

        self.validate_input_file(json_path, "JSON")

        try:
            shutil.copy2(json_path, output_path)
        except Exception as e:
            raise RuntimeError(f"Error copying JSON file from {json_path} to {output_path}: {str(e)}")

    def create_output_folder(self, project_name):
        """Create output folder for project in workspace directory"""
        output_dir = self.workspace_dir / project_name

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            print(f"  Created/verified output folder: {output_dir}")
            return output_dir
        except Exception as e:
            raise RuntimeError(f"Error creating output folder {output_dir}: {str(e)}")

    def process_single_project(self, row, row_number):
        """Process a single row/project from the data CSV"""
        # Extract basic project information
        # Generate project name based on input filename and row number
        input_filename = Path(self.data_csv_path).stem
        project_name = f"{input_filename}_{row_number}"
        template_file = row[0].strip()
        json_file = row[1].strip()

        print(f"\nProcessing row {row_number}: {project_name}")

        if not project_name:
            raise ValueError(f"Project name cannot be empty (row {row_number})")

        if not template_file:
            raise ValueError(f"Template file cannot be empty for project {project_name} (row {row_number})")

        if not json_file:
            raise ValueError(f"JSON file cannot be empty for project {project_name} (row {row_number})")

        # Create replacement values dictionary
        replacement_values = {}
        for i, header in enumerate(self.headers):
            if i < len(row):
                replacement_values[header] = row[i].strip()
            else:
                replacement_values[header] = ""

        # Create output folder
        output_dir = self.create_output_folder(project_name)

        # Process template CSV (now from assets/templates folder)
        processed_rows = self.process_template_csv(template_file, replacement_values)

        # Write processed CSV with proper CSV escaping
        script_csv_path = output_dir / "script.csv"
        try:
            with open(script_csv_path, 'w', newline='', encoding='utf-8') as f:
                csv_writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                csv_writer.writerows(processed_rows)

            print(f"  Created script.csv: {script_csv_path}")
        except Exception as e:
            raise RuntimeError(f"Error writing script.csv for {project_name}: {str(e)}")

        # Copy JSON file (now from assets/templates folder)
        config_json_path = output_dir / "config.json"
        self.copy_json_file(json_file, config_json_path)

        print(f"  Successfully processed project: {project_name}")

    def get_rows_to_process(self):
        """Get list of rows to process based on selected_rows or all rows"""
        if self.selected_rows:
            # Convert from 2-based row numbering to 0-based array indexing
            rows_to_process = []
            for row_num in self.selected_rows:
                array_index = row_num - 2  # Row 2 -> index 0
                rows_to_process.append((self.data_rows[array_index], row_num))
            return rows_to_process
        else:
            # Process all rows
            rows_to_process = []
            for i, row in enumerate(self.data_rows):
                row_number = i + 2  # Convert 0-based index to 2-based row number
                rows_to_process.append((row, row_number))
            return rows_to_process

    def process_all_projects(self):
        """Process selected projects from the data CSV"""
        # Validate and create workspace directory
        self.validate_workspace_directory()

        # Validate templates directory exists before processing
        self.validate_templates_directory()
        print(f"Validated templates directory: {self.templates_dir}")

        rows_to_process = self.get_rows_to_process()
        print(f"\nStarting to process {len(rows_to_process)} projects...")

        successful_projects = 0

        for row, row_number in rows_to_process:
            try:
                if len(row) < 3:
                    raise ValueError(f"Row {row_number} has insufficient columns (minimum 3 required)")

                self.process_single_project(row, row_number)
                successful_projects += 1

            except Exception as e:
                print(f"\nError processing row {row_number}: {str(e)}")
                raise

        print(f"\nSuccessfully processed {successful_projects} projects!")

    def run(self):
        """Main execution method"""
        try:
            self.load_data_csv()
            self.process_all_projects()

        except Exception as e:
            print(f"\nFatal error: {str(e)}")
            sys.exit(1)


def main():
    """Main entry point"""
    print("GenProject - CSV Template Processor")
    print("=" * 50)

    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Process data CSV to generate project folders with customized files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python genproject.py data.csv                    # Process all rows
  python genproject.py data.csv --rows 2           # Process only row 2
  python genproject.py data.csv --rows 2,4,6       # Process rows 2, 4, 6
  python genproject.py data.csv --rows 3-7         # Process rows 3-7
  python genproject.py data.csv --rows 2,4,8-12,15 # Mixed format

Required directory structure:
  assets/
    templates/
      template1.csv
      template2.csv
      config1.json
      config2.json

Output will be created in:
  workspace/
    project1/
      script.csv
      config.json

Note: Row numbering starts from 2 (first data row after header)
        """
    )

    parser.add_argument(
        'data_csv_file',
        help='Path to the input CSV file containing project configurations'
    )

    parser.add_argument(
        '--rows',
        help='Specify which rows to process (e.g., "2,4,6" or "3-7" or "2,4,8-12,15")',
        default=None
    )

    args = parser.parse_args()

    # Parse row specification
    try:
        processor = GenProjectProcessor(args.data_csv_file)
        selected_rows = processor.parse_row_specification(args.rows)
        processor.selected_rows = selected_rows
        processor.run()

    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()