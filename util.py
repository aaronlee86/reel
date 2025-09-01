#!/usr/bin/env python3
import sys
import os
import importlib.util
import csv
import tempfile
import shutil
import traceback

class LineProcessingUtility:
    def __init__(self, input_file, module_path):
        """
        Initialize the line processing utility

        Args:
            input_file (str): Path to the input CSV file
            module_path (str): Path to the Python module with processing logic
        """
        # Validate input file paths
        self._validate_file_paths(input_file, module_path)

        self.input_file = os.path.abspath(input_file)
        self.module_path = os.path.abspath(module_path)

        # Always verbose, interactive, and skip header
        self.verbose = True
        self.interactive = True
        self.skip_header = True

        # Import the processing module dynamically
        self.processing_module = self._import_module()

        # Temporary file for safe writing
        self.temp_file = None

    def _log(self, message):
        """
        Log message (always verbose)

        Args:
            message (str): Message to log
        """
        print(message)

    def _validate_file_paths(self, input_file, module_path):
        """
        Validate the existence and accessibility of input files

        Raises:
            FileNotFoundError: If either file does not exist
            PermissionError: If files are not readable
        """
        for filepath, file_type in [(input_file, 'Input'), (module_path, 'Module')]:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"{file_type} file not found: {filepath}")

            if not os.path.isfile(filepath):
                raise ValueError(f"{file_type} path is not a file: {filepath}")

            if not os.access(filepath, os.R_OK):
                raise PermissionError(f"Cannot read {file_type.lower()} file: {filepath}")

    def _import_module(self):
        """
        Dynamically import the processing module

        Returns:
            module: Imported processing module

        Raises:
            ImportError: If module cannot be imported
        """
        try:
            # Use importlib to load module from file path
            spec = importlib.util.spec_from_file_location("processing_module", self.module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Validate required functions exist
            required_attrs = ['condition', 'transform_functions']
            for attr in required_attrs:
                if not hasattr(module, attr):
                    raise AttributeError(f"Module must define '{attr}'")

            return module
        except Exception as e:
            self._log(f"Error importing processing module: {e}")
            sys.exit(1)

    def process(self):
        """
        Process the input file with the given module's logic
        """
        processed_rows = 0
        skipped_rows = 0
        header_row = None
        processing_interrupted = False

        try:
            # Create a temporary file for safe writing
            with tempfile.NamedTemporaryFile(mode='w', delete=False, newline='') as self.temp_file:
                with open(self.input_file, 'r', newline='') as input_csv:
                    # Use csv reader and writer for robust CSV handling
                    reader = csv.reader(input_csv)
                    writer = csv.writer(self.temp_file)

                    # Handle header row
                    try:
                        header_row = next(reader)
                        writer.writerow(header_row)
                    except StopIteration:
                        # File is empty
                        self._log("Empty file")
                        return

                    # Process each row
                    for row_num, row in enumerate(reader, start=2):  # start at 2 to account for header
                        # Skip empty rows
                        if not row:
                            writer.writerow(row)
                            continue

                        try:
                            # Check condition
                            if self.processing_module.condition(row):
                                # Store original row for potential restoration
                                original_row = row.copy()
                                self._log(f"Start Processing Row {row_num}")
                                try:
                                    # Apply transformation functions in sequence
                                    for transform_func in self.processing_module.transform_functions:
                                        row = transform_func(row)
                                    processed_rows += 1
                                    self._log(f"Processed Row {row_num}: {row}")
                                except KeyboardInterrupt:
                                    # Processing interrupted
                                    processing_interrupted = True
                                    self._log("Processing interrupted by user.")
                                    # Write current row as-is and stop processing
                                    writer.writerow(original_row)
                                    # Write remaining rows as-is
                                    for remaining_row in reader:
                                        writer.writerow(remaining_row)
                                    break
                            else:
                                skipped_rows += 1

                            # Write row (processed or skipped)
                            writer.writerow(row)

                        except Exception as e:
                            # Log error but write original row
                            self._log(f"Error processing row {row_num}: {e}")
                            writer.writerow(row)

            # Replace original file with processed file
            shutil.move(self.temp_file.name, self.input_file)

            # Log processing summary
            self._log("\n--- Processing Summary ---")
            self._log(f"File processed: {self.input_file}")
            self._log(f"Total rows processed: {processed_rows}")
            self._log(f"Total rows skipped: {skipped_rows}")

            if processing_interrupted:
                self._log("WARNING: Processing was interrupted. Remaining rows were written as-is.")

        except Exception as e:
            # Cleanup temporary file if it exists
            if self.temp_file and os.path.exists(self.temp_file.name):
                os.unlink(self.temp_file.name)
            self._log(f"Error processing file: {e}")
            traceback.print_exc()
            sys.exit(1)

def main():
    """
    Main entry point for the line processing utility
    """
    # Check for correct number of arguments
    if len(sys.argv) != 3:
        print("Usage: python util.py <input_file> <python_module>")
        sys.exit(1)

    try:
        # Create and run the processor
        processor = LineProcessingUtility(sys.argv[1], sys.argv[2])
        processor.process()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()