#!/usr/bin/env python3
"""
Script2Scene - Convert CSV and config files to structured scenes.json
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class Script2SceneError(Exception):
    """Custom exception for Script2Scene errors"""
    pass

def ensure_workspace_directory(project_name: str) -> str:
    """
    Ensure the workspace directory for the project exists.

    Args:
        project_name (str): Name of the project

    Returns:
        str: Path to the project workspace directory

    Raises:
        ValueError: If the workspace directory does not exist or is not a directory
    """
    workspace_dir = os.path.join('workspace', project_name)

    # Check if the directory exists
    if not os.path.exists(workspace_dir):
        raise ValueError(f"Workspace directory does not exist: {workspace_dir}")

    # Check if it's actually a directory
    if not os.path.isdir(workspace_dir):
        raise ValueError(f"Workspace path is not a directory: {workspace_dir}")

    return workspace_dir


class Script2Scene:
    """Main class for converting CSV and config to scenes.json"""

    REQUIRED_CSV_COLUMNS = {'text', 'mode'}
    VALID_MODES = {
        'append_center', 'append_top', 'all', 'all_with_highlight',
        'video', 'image'
    }
    TEXT_MODES = {'append_center', 'append_top', 'all', 'all_with_highlight'}
    VALID_VALIGN = {'top', 'center', 'bottom'}

    def __init__(self, project_name: str, input_csv: str, config_file: str, output_file: str):
        self.project_name = project_name
        self.input_csv = input_csv
        self.config_file = config_file
        self.output_file = output_file
        self.config = {}
        self.scenes = []

    def load_config(self) -> None:
        """Load and validate config.json"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            raise Script2SceneError(f"Config file not found: {self.config_file}")
        except json.JSONDecodeError as e:
            raise Script2SceneError(f"Invalid JSON in config file: {e}")

        # Validate required fields
        if 'screen_size' not in self.config:
            raise Script2SceneError("Config missing required field: screen_size")
        if 'font' not in self.config:
            raise Script2SceneError("Config missing required field: font")
        if 'ttf' not in self.config['font']:
            raise Script2SceneError("Config font missing required field: ttf")
        if 'size' not in self.config['font']:
            raise Script2SceneError("Config font missing required field: size")
        if 'color' not in self.config['font']:
            raise Script2SceneError("Config font missing required field: color")
        if 'line_spacing' not in self.config:
            raise Script2SceneError("Config missing required field: line_spacing")

        # Validate required TTS section
        if 'tts' not in self.config:
            raise Script2SceneError("Config missing required field: tts")
        if 'tts_engine' not in self.config['tts']:
            raise Script2SceneError("Config tts missing required field: tts_engine")
        if 'voice' not in self.config['tts']:
            raise Script2SceneError("Config tts missing required field: voice")

        # Validate optional fields if present
        if 'valign' in self.config:
            if self.config['valign'] not in self.VALID_VALIGN:
                raise Script2SceneError(f"Invalid valign in config: {self.config['valign']}. Must be one of {self.VALID_VALIGN}")

        if 'padding' in self.config:
            try:
                int(self.config['padding'])
            except (ValueError, TypeError):
                raise Script2SceneError(f"Invalid padding value in config: {self.config['padding']}. Must be an integer")

    def validate_highlight_mode(self, first_row: Dict[str, str]) -> None:
        """
        Validate that rows for 'all_with_highlight' mode have required highlight fields

        Args:
            rows (List[Dict[str, str]]): Rows to validate

        Raises:
            Script2SceneError: If required highlight fields are missing
        """

        # Check if any of the highlight fields are missing
        highlight_fields = ['highlight_color', 'highlight_bold', 'highlight_italic']
        missing_fields = [
            field for field in highlight_fields
            if not first_row.get(field, '').strip()
        ]

        if missing_fields:
            raise Script2SceneError(
                f"For 'all_with_highlight' mode, these highlight fields are required: {', '.join(missing_fields)}"
            )

    def load_csv(self) -> List[Dict[str, str]]:
        """Load and validate CSV file"""
        try:
            with open(self.input_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except FileNotFoundError:
            raise Script2SceneError(f"CSV file not found: {self.input_csv}")
        except Exception as e:
            raise Script2SceneError(f"Error reading CSV file: {e}")

        if not rows:
            raise Script2SceneError("CSV file is empty")

        # Validate required columns
        headers = set(rows[0].keys())
        missing_columns = self.REQUIRED_CSV_COLUMNS - headers
        if missing_columns:
            raise Script2SceneError(f"CSV missing required columns: {missing_columns}")

        # Validate mode values and valign values if present
        for i, row in enumerate(rows):
            mode = row.get('mode', '').strip()
            if mode and mode not in self.VALID_MODES:
                raise Script2SceneError(f"Invalid mode '{mode}' in row {i+1}")

            # Validate valign if present
            valign = row.get('valign', '').strip()
            if valign and valign not in self.VALID_VALIGN:
                raise Script2SceneError(f"Invalid valign '{valign}' in row {i+1}. Must be one of {self.VALID_VALIGN}")

        return rows

    def parse_background(self, background: str) -> Tuple[str, str]:
        """Parse background field into type and value"""
        if not background:
            return '', ''

        background = background.strip()
        if background.startswith('#'):
            return 'bgcolor', background
        else:
            return 'background', background

    def build_font_config(self, row: Dict[str, str], inherit_from: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Build font configuration from row data.

        Args:
            row: CSV row data
            inherit_from: Base config to inherit from (can be config defaults or scene config)

        Returns:
            Font configuration dictionary
        """
        if inherit_from:
            # Start with inherited config (either config defaults or scene config)
            font_config = {
                'file': inherit_from.get('ttf', inherit_from.get('file', self.config['font']['ttf'])),
                'size': inherit_from.get('size', self.config['font']['size']),
                'color': inherit_from.get('color', self.config['font']['color'])
            }
        else:
            # Fallback to config defaults if no inheritance specified
            font_config = {
                'file': self.config['font']['ttf'],
                'size': self.config['font']['size'],
                'color': self.config['font']['color']
            }

        # Override with row-specific values if specified
        if row.get('ttf', ''):
            font_config['file'] = row['ttf']
        if row.get('font_size', ''):
            try:
                font_config['size'] = int(row['font_size'])
            except ValueError as e:
                raise ValueError(f"invalide font_size format: {e}")
        if row.get('font_color', ''):
            font_config['color'] = row['font_color']

        return font_config

    def build_tts_config(self, row: Dict[str, str], inherit_from: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Build TTS configuration from row data.

        Args:
            row: CSV row data
            inherit_from: Base config to inherit from (can be config defaults or scene config)

        Returns:
            TTS configuration dictionary
        """
        if inherit_from:
            # Start with inherited config (either config defaults or scene config)
            tts_config = {
                'tts_engine': inherit_from.get('tts_engine', self.config['tts']['tts_engine']),
                'voice': inherit_from.get('voice', self.config['tts']['voice']),
                'speed': inherit_from.get('speed', 1.0)
            }
        else:
            # Fallback to config defaults if no inheritance specified
            tts_config = {
                'tts_engine': self.config['tts']['tts_engine'],
                'voice': self.config['tts']['voice'],
                'speed': 1.0
            }

        # Override with row-specific values if specified
        if row.get('tts', '').strip():
            tts_config['tts_engine'] = row['tts']

        if row.get('voice', '').strip():
            tts_config['voice'] = row['voice']

        if row.get('speed', '').strip():
            try:
                tts_config['speed'] = float(row['speed'])
            except ValueError:
                pass  # Keep inherited/default value

        return tts_config

    def create_text_scene(self, mode: str, rows: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create a text scene from grouped rows"""
        first_row = rows[0]

        # Parse background
        bg_type, bg_value = self.parse_background(first_row.get('background', ''))
        scene = {
            'type': 'text',
            'mode': mode,
            'text': []
        }

        if bg_type and bg_value:
            scene[bg_type] = bg_value

        # Add line_spacing handling
        # Priority: Row-specific line_spacing > Config line_spacing > Default
        line_spacing = first_row.get('line_spacing', '').strip()
        if line_spacing:
            try:
                scene['line_spacing'] = int(line_spacing)
            except ValueError:
                # If conversion fails, use config's line_spacing
                raise Script2SceneError(f"Invalid line_spacing value: {line_spacing}. Must be an integer")
        elif 'line_spacing' in self.config:
            scene['line_spacing'] = self.config['line_spacing']

        # Add padding handling
        # Priority: Row-specific padding > Config padding (no default fallback)
        padding = first_row.get('padding', '').strip()
        if padding:
            try:
                scene['padding'] = int(padding)
            except ValueError:
                raise Script2SceneError(f"Invalid padding value: {padding}. Must be an integer")
        elif 'padding' in self.config:
            scene['padding'] = self.config['padding']

        # Add valign handling
        # Priority: Row-specific valign > Config valign (no default fallback)
        valign = first_row.get('valign', '').strip()
        if valign:
            scene['valign'] = valign
        elif 'valign' in self.config:
            scene['valign'] = self.config['valign']

        # Add highlight_style for all_with_highlight mode
        if mode == 'all_with_highlight':
            self.validate_highlight_mode(first_row)

            highlight_style = {}
            highlight_style['font_color'] = first_row['highlight_color']
            # Convert string to boolean
            highlight_style['bold'] = first_row['highlight_bold'].lower() in ('true', '1', 'yes')
            # Convert string to boolean
            highlight_style['italic'] = first_row['highlight_italic'].lower() in ('true', '1', 'yes')

            scene['highlight_style'] = highlight_style

        # Build scene-level font/TTS config from first row (using config defaults as base)
        scene_font_config = self.build_font_config(first_row)
        scene_tts_config = self.build_tts_config(first_row)

        # Add text entries
        for i, row in enumerate(rows):
            if i == 0:
                # First row uses the scene-level config
                text_entry = {
                    'text': row['text'],
                    'font': scene_font_config,
                    'tts': scene_tts_config
                }
            else:
                # Subsequent rows inherit from scene config but can override individual fields
                text_entry = {
                    'text': row['text'],
                    'font': self.build_font_config(row, inherit_from=scene_font_config),
                    'tts': self.build_tts_config(row, inherit_from=scene_tts_config)
                }

            # Only add halign if it's not empty
            if row.get('alignment', '').strip():
                text_entry['halign'] = row.get('alignment')

            # Add dub if specified in the row
            if row.get('dub', '').strip():
                text_entry['dub'] = row['dub']

            scene['text'].append(text_entry)

        return scene

    def create_image_scene(self, rows: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create an image scene from grouped rows"""
        first_row = rows[0]

        # Parse background (becomes file)
        bg_type, bg_value = self.parse_background(first_row.get('background'))

        scene = {'type': 'image'}

        if bg_type == 'bgcolor':
            scene['bgcolor'] = bg_value
        elif bg_type == 'background':
            scene['file'] = bg_value

        # Duration is required for image scenes
        if first_row.get('duration'):
            try:
                scene['duration'] = float(first_row['duration'])
            except ValueError:
                raise Script2SceneError(f"Invalid duration value: {first_row['duration']}")

        # Add TTS audio if text is provided
        if first_row.get('text', '').strip():
            tts_config = self.build_tts_config(first_row)
            scene['audio'] = {
                'tts': {
                    'text': first_row['text'],
                    **tts_config
                }
            }

        return scene

    def create_video_scene(self, rows: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create a video scene from grouped rows"""
        first_row = rows[0]

        scene = {
            'type': 'video',
            'file': first_row.get('background')  # Using background field as specified
        }

        # Add duration if available
        if first_row.get('duration'):
            scene['duration'] = float(first_row['duration'])

        return scene

    def group_rows_by_mode(self, rows: List[Dict[str, str]]) -> List[Tuple[str, List[Dict[str, str]]]]:
        """Group consecutive rows by mode"""
        if not rows:
            return []

        groups = []
        current_mode = None
        current_group = []

        for row in rows:
            mode = row.get('mode', '').strip()

            # Rule 1: If mode is specified, start a new scene
            if mode:
                # Save the previous group if it exists
                if current_group:
                    groups.append((current_mode, current_group))

                # Start new group with this row
                current_mode = mode
                current_group = [row]

            # Rule 2: If no mode specified, inherit and group with previous
            else:
                # Skip if we don't have a current mode to inherit from
                if current_mode is None:
                    continue

                # Inherit the mode and add to current group
                row['mode'] = current_mode
                current_group.append(row)

        # Add the final group
        if current_group:
            groups.append((current_mode, current_group))

        return groups

    def convert_to_scenes(self) -> None:
        """Main conversion logic"""
        rows = self.load_csv()
        grouped_rows = self.group_rows_by_mode(rows)

        self.scenes = []

        for mode, group_rows in grouped_rows:
            if mode in self.TEXT_MODES:
                scene = self.create_text_scene(mode, group_rows)
            elif mode == 'image':
                scene = self.create_image_scene(group_rows)
            elif mode == 'video':
                scene = self.create_video_scene(group_rows)
            else:
                raise Script2SceneError(f"Unsupported mode: {mode}")

            self.scenes.append(scene)

    def save_scenes(self) -> None:
        """Save scenes to JSON file with default fps handling"""
        # Add global config if available
        output_data = {
            'screen_size': self.config.get('screen_size')  # Always include screen_size
        }

        # Always set fps, defaulting to 30 if not specified in config
        output_data['fps'] = self.config.get('fps', 30)

        if 'bgm' in self.config:
            output_data['bgm'] = self.config['bgm']

        output_data['scenes'] = self.scenes

        # Create output directory if needed
        output_dir = os.path.dirname(self.output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Script2SceneError(f"Error writing output file: {e}")

    def run(self) -> None:
        """Run the complete conversion process"""
        self.load_config()
        self.convert_to_scenes()
        self.save_scenes()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Convert CSV and config to scenes.json')
    parser.add_argument('project', help='Project name')
    parser.add_argument('--input-csv', help='Input CSV file path')
    parser.add_argument('--config', help='Config JSON file path')
    parser.add_argument('--output', help='Output scenes.json file path')

    args = parser.parse_args()

    try:
        # Always validate workspace directory exists
        workspace_dir = ensure_workspace_directory(args.project)

        # Set paths - all relative to workspace directory
        input_csv = os.path.join(workspace_dir, args.input_csv or 'script.csv')
        config_file = os.path.join(workspace_dir, args.config or 'config.json')
        output_file = os.path.join(workspace_dir, args.output or 'scenes.json')

        converter = Script2Scene(args.project, input_csv, config_file, output_file)
        converter.run()
        print(f"Successfully converted to {output_file}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Script2SceneError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()