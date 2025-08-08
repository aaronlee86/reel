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

        # Validate mode values
        for i, row in enumerate(rows):
            mode = row.get('mode', '').strip()
            if mode and mode not in self.VALID_MODES:
                raise Script2SceneError(f"Invalid mode '{mode}' in row {i+1}")

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

    def get_default_tts_settings(self) -> Dict[str, Any]:
        """Get default TTS settings"""
        return {
            'tts_engine': 'edge-tts',
            'voice': 'zh-TW-HsiaoChenNeural',
            'speed': 1.0
        }

    def build_font_config(self, row: Dict[str, str], reset_to_defaults: bool = False) -> Dict[str, Any]:
        """Build font configuration from row data"""
        if reset_to_defaults:
            font_config = {
                'file': self.config['font']['ttf'],
                'size': self.config['font']['size'],
                'color': self.config['font']['color']
            }
        else:
            font_config = {}

        # Override with row-specific values
        if row.get('ttf'):
            font_config['file'] = row['ttf']
        elif 'file' not in font_config:
            font_config['file'] = self.config['font']['ttf']

        font_config['size'] = self.config['font']['size']
        font_config['color'] = self.config['font']['color']

        return font_config

    def build_tts_config(self, row: Dict[str, str], reset_to_defaults: bool = False) -> Dict[str, Any]:
        """Build TTS configuration from row data"""
        if reset_to_defaults:
            tts_config = self.get_default_tts_settings()
        else:
            tts_config = {}

        # Override with row-specific values
        if row.get('tts'):
            tts_config['tts_engine'] = row['tts']
        elif 'tts_engine' not in tts_config:
            tts_config['tts_engine'] = 'edge-tts'

        if row.get('voice'):
            tts_config['voice'] = row['voice']
        elif 'voice' not in tts_config:
            tts_config['voice'] = 'zh-TW-HsiaoChenNeural'

        if row.get('speed'):
            try:
                tts_config['speed'] = float(row['speed'])
            except ValueError:
                tts_config['speed'] = 1.0
        elif 'speed' not in tts_config:
            tts_config['speed'] = 1.0

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

        # Add text entries
        for row in rows:
            text_entry = {
                'text': row['text'],
                'font': self.build_font_config(row, reset_to_defaults=(row == first_row)),
                'halign': row.get('alignment', 'center'),
                'tts': self.build_tts_config(row, reset_to_defaults=(row == first_row))
            }
            scene['text'].append(text_entry)

        return scene

    def create_image_scene(self, rows: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create an image scene from grouped rows"""
        first_row = rows[0]

        # Parse background (becomes file)
        bg_type, bg_value = self.parse_background(first_row.get('background', ''))

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
            tts_config = self.build_tts_config(first_row, reset_to_defaults=True)
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
            'file': first_row.get('background', '')
        }

        # Add duration if available
        if first_row.get('duration'):
            try:
                scene['duration'] = float(first_row['duration'])
            except ValueError:
                scene['duration'] = 15  # Default duration

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

            # Skip rows without mode (unless continuing previous mode)
            if not mode and not current_mode:
                continue

            # Use previous mode if current row doesn't have one
            if not mode:
                mode = current_mode
                row['mode'] = mode

            # Start new group if mode changed
            if mode != current_mode:
                if current_group:
                    groups.append((current_mode, current_group))
                current_mode = mode
                current_group = [row]
            else:
                current_group.append(row)

        # Add the last group
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
        """Save scenes to JSON file"""
        output_data = {
            'scenes': self.scenes
        }

        # Add global config if available
        if 'fps' in self.config:
            output_data['fps'] = self.config['fps']

        if 'bgm' in self.config:
            output_data['bgm'] = self.config['bgm']

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