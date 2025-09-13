#!/usr/bin/env python3
import argparse
import asyncio
import csv
import importlib
import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Callable
from asyncDict import AsyncDictionaryManager, Status

class CSVProcessor:
    def __init__(self, config_path: str):
        """
        Initialize the CSV processor with the given configuration.

        :param config_path: Path to the JSON configuration file
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = self._load_config()
        self.filename = self.config['filename']
        self.trigger_columns = self.config['trigger_column']
        self.data_instructions = self.config['data']
        self.function_map: Dict[str, AsyncDictionaryManager] = {}
        self._load_function_map()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load and validate the JSON configuration.

        :return: Parsed configuration dictionary
        :raises ValueError: If configuration is invalid
        """
        try:
            with open(self.config_path, 'r') as config_file:
                config = json.load(config_file)

            # Validate critical configuration keys
            if 'filename' not in config:
                raise ValueError("Missing 'filename' in configuration")
            if 'trigger_column' not in config:
                raise ValueError("Missing 'trigger_column' in configuration")
            if 'data' not in config:
                raise ValueError("Missing 'data' in configuration")

            # Validate file existence
            if not os.path.exists(config['filename']):
                raise FileNotFoundError(f"CSV file not found: {config['filename']}")

            return config
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON configuration: {e}")
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Configuration file not found: {e}")

    def _load_function_map(self):
        for instruction in self.data_instructions:
            function_name = instruction['function']

            # Import and call function
            func = self._load_refill_func(function_name)
            self.function_map[function_name] = AsyncDictionaryManager(
                refill_func=func,
                threshold=2
            )

    def _load_refill_func(self, refill_func: str) -> Callable[[str], Any]:
        """
        Load refill function dynamically if a string path is provided

        :param refill_func: Function or string path to the function
        :return: Callable refill function
        """

        try:
            # Split the string into module path and function name
            module_path, func_name = refill_func.rsplit('.', 1)

            # Import the module
            module = importlib.import_module(module_path)

            # Get the function from the module
            func = getattr(module, func_name)

            return func
        except (ImportError, AttributeError, ValueError) as e:
            raise ValueError(f"Could not load refill function {refill_func}: {e}")

    async def process_csv(self):
        """
        Process the CSV file based on configuration.

        :raises Exception: For various processing errors
        """
        # Create a temporary file for safe writing
        with tempfile.NamedTemporaryFile(mode='w', delete=False, newline='') as temp_file:
            try:
                # Read the original CSV
                with open(self.filename, 'r', newline='') as csvfile:
                    reader = csv.reader(csvfile)
                    writer = csv.writer(temp_file)

                    # Write header (first row) to temp file
                    header = next(reader)
                    writer.writerow(header)

                    # Process rows
                    for row in reader:
                        # Check if trigger columns are populated
                        if self._check_trigger_columns(row):
                            row = await self._process_row(row)
                        writer.writerow(row)

                # Flush and close the temp file
                temp_file.flush()
                os.fsync(temp_file.fileno())

            except Exception as e:
                # Clean up temp file in case of error
                os.unlink(temp_file.name)
                raise

        # Atomically replace the original file
        os.replace(temp_file.name, self.filename)


    def _check_trigger_columns(self, row: List[str]) -> bool:
        """
        Check if all trigger columns are populated.

        :param row: Current row being processed
        :return: True if trigger columns are populated, False otherwise
        """
        return all(
            row[col].strip() != ''
            for col in self.trigger_columns
            if col < len(row)
        )

    async def _process_row(self, row: List[str]) -> List[str]:
        """
        Process a single row based on data instructions.

        :param row: Current row being processed
        :return: Processed row
        """
        for instruction in self.data_instructions:
            # Check if target columns are empty
            if all(
                row[col].strip() == '' or row[col] == Status.LOADING
                for col in instruction['cols']
                if col < len(row)
            ):
                # Prepare parameters
                params = (
                    row[param]
                    for param in instruction['parameter']
                    if param < len(row)
                )

                func = self.function_map[instruction['function']]
                result = await func.get(*params)

                # Store result in target columns
                for i, col in enumerate(instruction['cols']):
                    if col < len(row):
                        if result["status"] == Status.LOADING:
                            row[col] = Status.LOADING
                        else:
                            row[col] = str(result['value'][i]) if isinstance(result['value'], (list, tuple)) else str(result['value'])

        return row

async def main():
    """
    Async main entry point for the script.
    """
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='Process CSV file based on JSON configuration')
    parser.add_argument('config_json', help='Path to the JSON configuration file')

    # Parse arguments
    args = parser.parse_args()

    try:
        # Create processor and run
        processor = CSVProcessor(args.config_json)

        while True:
            await processor.process_csv()
            await asyncio.sleep(0.1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())