import json
import csv
import sys
import re
import shutil
import importlib
import sqlite3
import os
import argparse
from pathlib import Path
from datetime import datetime

def csv_escape_value(value):
        """
        Escape and quote CSV values:
        - Escape existing quotes by doubling them
        - Convert to string
        """
        # Convert to string
        str_value = str(value)

        # Check if value contains comma, quote, or newline
        if '"' in str_value:
            # Escape quotes by doubling them
            escaped_value = str_value.replace('"', '""')
            # Wrap in quotes
            return f'{escaped_value}'

        return str_value

class TemplateProcessor:
    """Main class for processing CSV templates with dynamic variable replacement."""

    def __init__(self, config_path, output_folder, overwrite=False):
        self.config_path = Path(config_path)
        self.output_folder = Path(output_folder)
        self.overwrite = overwrite
        self.variables = {}
        self.config = None
        self.created_output_folder = False
        self.created_files = []
        self.backup_files = []  # Track backed up files for rollback
        self.db_backup = None  # In-memory database backup
        self.db_path = None  # Original database path

    def rollback(self):
        """Rollback any changes made during processing."""
        print("Rolling back changes...")

        # Restore database from memory backup if available
        if self.db_backup and self.db_path:
            try:
                print(f"Restoring database from memory backup: {self.db_path}")

                # Connect to the original database
                disk_conn = sqlite3.connect(self.db_path)

                # Restore from memory backup
                self.db_backup.backup(disk_conn)

                disk_conn.close()
                self.db_backup.close()

                print(f"Database restored: {self.db_path}")
            except Exception as e:
                print(f"Warning: Failed to restore database: {e}")

        # Restore backed up files
        for backup_path, original_path in reversed(self.backup_files):
            try:
                if backup_path.exists():
                    shutil.move(str(backup_path), str(original_path))
                    print(f"Restored backup: {original_path}")
            except Exception as e:
                print(f"Warning: Failed to restore backup {backup_path}: {e}")

        # Remove created files
        for file_path in reversed(self.created_files):
            try:
                if file_path.exists():
                    file_path.unlink()
                    print(f"Removed file: {file_path}")
            except Exception as e:
                print(f"Warning: Failed to remove file {file_path}: {e}")

        # Remove output folder if we created it
        if self.created_output_folder and self.output_folder.exists():
            try:
                shutil.rmtree(self.output_folder)
                print(f"Removed output folder: {self.output_folder}")
            except Exception as e:
                print(f"Warning: Failed to remove output folder: {e}")

        print("Rollback complete.")

    def backup(self):
        """Create backup of SQLite database to memory before processing."""
        print("Creating database backup...")

        # Get database path from config
        db_path = self.config.get('database_path')

        if not db_path:
            print("No database path specified in config. Skipping backup.")
            return

        self.db_path = Path(db_path)

        # Check if database file exists
        if not self.db_path.exists():
            print(f"Warning: Database file not found: {self.db_path}")
            print("Skipping backup.")
            return

        try:
            # Connect to the disk database
            print(f"Backing up database: {self.db_path}")
            disk_conn = sqlite3.connect(str(self.db_path))

            # Create an in-memory database
            self.db_backup = sqlite3.connect(':memory:')

            # Backup disk database to memory
            disk_conn.backup(self.db_backup)

            # Close disk connection (keep memory connection open)
            disk_conn.close()

            print(f"Database backed up to memory successfully.")

        except Exception as e:
            print(f"Error: Failed to backup database: {e}")
            raise

    def backup_file(self, file_path):
        """
        Create a timestamped backup of a file.

        Args:
            file_path: Path to the file to backup

        Returns:
            Path to the backup file
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return None

        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create backup filename with timestamp
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = file_path.parent / backup_name

        try:
            shutil.copy2(file_path, backup_path)
            print(f"Backed up: {file_path} -> {backup_path}")
            self.backup_files.append((backup_path, file_path))
            return backup_path
        except Exception as e:
            print(f"Warning: Failed to backup file {file_path}: {e}")
            raise

    def load_config(self):
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)

            # Validate required fields
            required_fields = ['template_csv', 'instruction_csv', 'output_filename', 'database_path']
            for field in required_fields:
                if field not in self.config:
                    raise ValueError(f"Missing required field in config: {field}")

        except FileNotFoundError:
            print(f"Error: Config file not found: {self.config_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config file: {e}")
            sys.exit(1)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    def process_instructions(self):
        """Process instruction CSV to generate variables."""
        instruction_path = Path(self.config['instruction_csv'])

        try:
            with open(instruction_path, 'r') as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header row

                for row_num, row in enumerate(reader, start=2):  # Start from row 2
                    if not row or len(row) < 2:
                        continue

                    variable_name = row[0].strip()
                    classname = row[1].strip()
                    params = [param.strip() for param in row[2:]] if len(row) > 2 else []
                    print(f"Processing var '{variable_name}'")

                    # Parse params into kwargs
                    kwargs = {}
                    for param in params:
                        if '=' in param:
                            key, value = param.split('=', 1)
                            kwargs[key.strip()] = value.strip()

                    # Dynamic import and instantiation
                    try:
                        module_name, class_name = classname.rsplit('.', 1)
                        module = importlib.import_module(module_name)
                        cls = getattr(module, class_name)
                    except (ValueError, ImportError, AttributeError) as e:
                        print(f"Error: Failed to import class '{classname}' at row {row_num}: {e}")
                        raise

                    try:
                        # get qno (question number) parameter from variable name if exists
                        qno = int(variable_name[1:])
                    except ValueError:
                        qno = None

                    try:
                        # Instantiate with parameters
                        instance = cls(dbPath=self.db_path, xid=os.path.basename(self.output_folder), qno=qno, **kwargs)
                    except Exception as e:
                        print(f"Error: Failed to instantiate class '{classname}' at row {row_num}: {e}")
                        raise

                    try:
                        result = instance.run()
                        # Store variable if result is not None
                        if result is not None:
                            self.variables[variable_name] = result
                    except Exception as e:
                        print(f"Error: Failed to run class '{classname}' at row {row_num}: {e}")
                        raise

        except FileNotFoundError:
            print(f"Error: Instruction CSV not found: {instruction_path}")
            raise

    def resolve_placeholder(self, var_path):
        """
        Resolve complex nested placeholders with flexible path traversal.

        Supported path formats:
        - Simple variable: 'variable_name'
        - Dictionary key: 'dict_var.key'
        - List/array index: 'list_var[0]'
        - Nested dictionary: 'dict_var.nested_key'
        - Deeply nested: 'dict_var.list_key[2].sub_key'
        - Array expansion: 'list_var[]'

        Path traversal rules:
        - Supports unlimited nesting depth
        - Handles mixed access types (dict, list, nested)
        - Returns entire list/dict for array expansion
        - Returns specific index/key value for direct access
        - Converts complex types to JSON string
        - Handles type conversion and escaping

        Examples:
        - 'users' → entire users list/dict
        - 'users[0]' → first user
        - 'users[0].name' → name of first user
        - 'config.database.host' → database hostname
        - 'array[]' → entire array as JSON string

        Args:
            var_path (str): Dot and bracket notation path to resolve

        Returns:
            Resolved value as string, or None if path is invalid
        """
        # Tokenize path, handling nested structures
        tokens = re.findall(r'[^\.\[]+|\[\d*\]', var_path)

        if not tokens:
            return None

        # Start with base variables dictionary
        current = self.variables

        # Navigate through tokens
        for i, token in enumerate(tokens):
            if token.startswith('[') and token.endswith(']'):
                # Handle array index or expansion
                index = token[1:-1]

                # If empty brackets, entire array
                if index == '':
                    if isinstance(current, (list, dict)):
                        # Return entire array as JSON string
                        return json.dumps(current)
                    return None

                # Numeric index
                try:
                    index = int(index)
                    if isinstance(current, (list, tuple)):
                        current = current[index]
                    elif isinstance(current, dict):
                        # If it's a dict, treat index as key
                        keys = list(current.keys())
                        if 0 <= index < len(keys):
                            current = current[keys[index]]
                        else:
                            return None
                    else:
                        return None
                except (ValueError, TypeError, IndexError):
                    return None
            else:
                # Nested key access
                if isinstance(current, dict):
                    if token in current:
                        current = current[token]
                    else:
                        return None
                else:
                    return None

        # Final conversion
        if current is None:
            return None

        # Ensure string conversion
        if isinstance(current, (dict, list)):
            # Convert complex types to JSON string
            return json.dumps(current)
        elif isinstance(current, bytes):
            # Handle byte strings
            return current.decode('utf-8')

        # Convert to string
        value = str(current)
        return value.replace('\n', '\\n')

    def process_template(self):
        """Process template CSV and replace placeholders with multiple array expansions."""
        template_path = Path(self.config['template_csv'])

        try:
            with open(template_path, 'r') as f:
                content = f.read()

                # Tracks final content after processing
                final_content_lines = []

                # Process each line
                for line in content.splitlines():
                    # Find all placeholders
                    line_placeholders = re.findall(r'\$\(([^)]+)\)', line)

                    # Identify array expansion placeholders
                    array_expansions = [p for p in line_placeholders if p.endswith('[]')]

                    if array_expansions:
                        # Determine max expansion length
                        expansion_lengths = []
                        for array_ph in array_expansions:
                            base_ph = array_ph[:-2]  # Remove '[]'
                            array_value = self.resolve_placeholder(base_ph)

                            # Try to parse the array value
                            try:
                                parsed_array = json.loads(array_value) if isinstance(array_value, str) else array_value
                            except json.JSONDecodeError:
                                parsed_array = array_value

                            if isinstance(parsed_array, (list, tuple)):
                                expansion_lengths.append(len(parsed_array))
                            else:
                                expansion_lengths.append(0)

                        # Ensure all arrays are expanded to the same length
                        max_length = max(expansion_lengths)

                        # Generate expanded lines
                        expanded_lines = []
                        for i in range(max_length):
                            # Create a copy of the original line
                            expanded_line = line

                            # Replace all array expansion placeholders
                            for array_ph in array_expansions:
                                base_ph = array_ph[:-2]  # Remove '[]'

                                # Resolve and replace the specific index
                                replacement = csv_escape_value(
                                    self.resolve_placeholder(f"{base_ph}[{i}]")
                                    if i < expansion_lengths[array_expansions.index(array_ph)]
                                    else ''
                                )

                                expanded_line = expanded_line.replace(
                                    f"$({array_ph})",
                                    replacement
                                )

                            # Replace any remaining non-array placeholders
                            for ph in line_placeholders:
                                if not ph.endswith('[]'):
                                    ph_value = self.resolve_placeholder(ph)
                                    if ph_value is not None:
                                        expanded_line = expanded_line.replace(
                                            f"$({ph})",
                                            csv_escape_value(ph_value)
                                        )

                            expanded_lines.append(expanded_line)

                        final_content_lines.extend(expanded_lines)
                    else:
                        # Process line normally if no array expansions
                        for ph in line_placeholders:
                            ph_value = self.resolve_placeholder(ph)
                            if ph_value is not None:
                                line = line.replace(
                                    f"$({ph})",
                                    csv_escape_value(ph_value)
                                )
                        final_content_lines.append(line)

                # Check for unreplaced placeholders
                unreplaced = re.findall(r'\$\([^)]+\)', '\n'.join(final_content_lines))
                if unreplaced:
                    print(f"Error: Unreplaced placeholders found: {', '.join(set(unreplaced))}")
                    print("Hint: Check variable names and structure")
                    raise ValueError(f"Unreplaced placeholders: {', '.join(set(unreplaced))}")

                return '\n'.join(final_content_lines)

        except FileNotFoundError:
            print(f"Error: Template CSV not found: {template_path}")
            raise

    def create_output(self, processed_content):
        """Create output folder and write results."""
        # Check if output folder exists
        if self.output_folder.exists():
            if not self.overwrite:
                print(f"Error: Output folder already exists: {self.output_folder}")
                raise FileExistsError(f"Output folder already exists: {self.output_folder}")
            else:
                print(f"Warning: Output folder exists, will overwrite files: {self.output_folder}")
        else:
            # Create output folder
            try:
                self.output_folder.mkdir(parents=True)
                self.created_output_folder = True
            except Exception as e:
                print(f"Error: Failed to create output folder: {e}")
                raise

        # Write processed CSV (with backup if overwriting)
        output_file = self.output_folder / self.config['output_filename']
        try:
            # Backup existing file if it exists and we're overwriting
            if output_file.exists() and self.overwrite:
                self.backup_file(output_file)

            with open(output_file, 'w') as f:
                f.write(processed_content)
            self.created_files.append(output_file)
            print(f"Written: {output_file}")
        except Exception as e:
            print(f"Error: Failed to write output file: {e}")
            raise

        # Copy additional files
        files_to_copy = self.config.get('files_to_copy', [])
        for file_path in files_to_copy:
            src = Path(file_path)

            # Preserve directory structure or just filename
            if src.is_absolute():
                dst = self.output_folder / src.name
            else:
                # For relative paths, preserve the structure
                dst = self.output_folder / src

            try:
                if not src.exists():
                    print(f"Error: File to copy not found: {src}")
                    raise FileNotFoundError(f"File to copy not found: {src}")

                # Create parent directories if needed
                dst.parent.mkdir(parents=True, exist_ok=True)

                # Backup existing file if it exists and we're overwriting
                if dst.exists() and self.overwrite:
                    self.backup_file(dst)

                shutil.copy2(src, dst)
                self.created_files.append(dst)
                print(f"Copied: {src} -> {dst}")
            except Exception as e:
                print(f"Error: Failed to copy file '{src}': {e}")
                raise

    def run(self):
        """Execute the complete processing pipeline with rollback on error."""
        try:
            print("Loading configuration...")
            self.load_config()

            print("Creating backup...")
            self.backup()

            print("Processing instructions...")
            self.process_instructions()

            print("Processing template...")
            processed_content = self.process_template()

            print("Creating output...")
            self.create_output(processed_content)

            print(f"Success! Output created in: {self.output_folder}")

        except Exception as e:
            # Rollback on any error
            self.rollback()
            print(f"\nFatal error: {e}")
            sys.exit(1)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Process CSV templates with dynamic variable replacement.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('config_path',
                        help='Path to the JSON configuration file')
    parser.add_argument('output_folder',
                        help='Path to the output folder')
    parser.add_argument('--overwrite',
                        action='store_true',
                        help='Overwrite existing files (creates timestamped backups)')

    args = parser.parse_args()

    processor = TemplateProcessor(args.config_path, args.output_folder, overwrite=args.overwrite)
    processor.run()


if __name__ == "__main__":
    main()