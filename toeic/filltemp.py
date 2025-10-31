#!/usr/bin/env python3
"""
CSV Template Processor
Processes CSV templates with placeholders using dynamically imported classes.
Supports simple strings, nested JSON objects, and array indexing.
"""

import sys
import json
import csv
import re
import shutil
import importlib
from pathlib import Path


class TemplateProcessor:
    """Main class for processing CSV templates with dynamic variable replacement."""

    def __init__(self, config_path, output_folder):
        self.config_path = Path(config_path)
        self.output_folder = Path(output_folder)
        self.variables = {}
        self.config = None

    def load_config(self):
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)

            # Validate required fields
            required_fields = ['template_csv', 'instruction_csv', 'output_filename']
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
                        sys.exit(1)
                    
                    try:
                        # Instantiate with parameters
                        instance = cls(**kwargs)
                    except Exception as e:
                        print(f"Error: Failed to instantiate class '{classname}' at row {row_num}: {e}")
                        sys.exit(1)
                    
                    try:
                        result = instance.run()
                        # Store variable if result is not None
                        if result is not None:
                            self.variables[variable_name] = result
                    except Exception as e:
                        print(f"Error: Failed to run class '{classname}' at row {row_num}: {e}")
                        sys.exit(1)



        except FileNotFoundError:
            print(f"Error: Instruction CSV not found: {instruction_path}")
            sys.exit(1)

    def resolve_placeholder(self, var_path):
        """
        Resolve a placeholder path like 'var.key[0].subkey' to its value.

        Args:
            var_path: String like 'variable', 'var.key', 'var[0]', 'var.key[1].sub'

        Returns:
            The resolved value as a string, or None if not found
        """
        # Parse the path into tokens (keys and array indices)
        # Pattern matches: word, .word, [index]
        tokens = re.findall(r'[^\.\[]+|\[\d+\]', var_path)

        if not tokens:
            return None

        # Start with the base variable
        base_var = tokens[0]
        if base_var not in self.variables:
            return None

        current = self.variables[base_var]

        # Navigate through the path
        for token in tokens[1:]:
            if token.startswith('[') and token.endswith(']'):
                # Array index
                try:
                    index = int(token[1:-1])
                    if isinstance(current, (list, tuple)):
                        if 0 <= index < len(current):
                            current = current[index]
                        else:
                            return None
                    else:
                        return None
                except (ValueError, TypeError):
                    return None
            else:
                # Object key
                if isinstance(current, dict):
                    if token in current:
                        current = current[token]
                    else:
                        return None
                else:
                    return None

        # Convert final value to string and escape newlines
        if isinstance(current, (dict, list)):
            value = json.dumps(current)
        else:
            value = str(current)

        # Escape newlines for CSV compatibility
        value = value.replace('\n', '\\n')
        return value

    def process_template(self):
        """Process template CSV and replace placeholders."""
        template_path = Path(self.config['template_csv'])

        try:
            with open(template_path, 'r') as f:
                content = f.read()

            # Find all placeholders
            placeholders = re.findall(r'\$\(([^)]+)\)', content)

            # Replace each placeholder
            for placeholder in placeholders:
                value = self.resolve_placeholder(placeholder)
                if value is not None:
                    content = content.replace(f"$({placeholder})", value)

            # Check for unreplaced placeholders
            unreplaced = re.findall(r'\$\([^)]+\)', content)
            if unreplaced:
                print(f"Error: Unreplaced placeholders found: {', '.join(set(unreplaced))}")
                sys.exit(1)

            return content

        except FileNotFoundError:
            print(f"Error: Template CSV not found: {template_path}")
            sys.exit(1)

    def create_output(self, processed_content):
        """Create output folder and write results."""
        # Check if output folder exists
        if self.output_folder.exists():
            print(f"Error: Output folder already exists: {self.output_folder}")
            sys.exit(1)

        # Create output folder
        try:
            self.output_folder.mkdir(parents=True)
        except Exception as e:
            print(f"Error: Failed to create output folder: {e}")
            sys.exit(1)

        # Write processed CSV
        output_file = self.output_folder / self.config['output_filename']
        try:
            with open(output_file, 'w') as f:
                f.write(processed_content)
        except Exception as e:
            print(f"Error: Failed to write output file: {e}")
            sys.exit(1)

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
                    sys.exit(1)

                # Create parent directories if needed
                dst.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(src, dst)
                print(f"Copied: {src} -> {dst}")
            except Exception as e:
                print(f"Error: Failed to copy file '{src}': {e}")
                sys.exit(1)

    def run(self):
        """Execute the complete processing pipeline."""
        print("Loading configuration...")
        self.load_config()

        print("Processing instructions...")
        self.process_instructions()

        print("Processing template...")
        processed_content = self.process_template()

        print("Creating output...")
        self.create_output(processed_content)

        print(f"Success! Output created in: {self.output_folder}")


def main():
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: python filltemp.py input.json output_folder")
        sys.exit(1)

    config_path = sys.argv[1]
    output_folder = sys.argv[2]

    processor = TemplateProcessor(config_path, output_folder)
    processor.run()


if __name__ == "__main__":
    main()
