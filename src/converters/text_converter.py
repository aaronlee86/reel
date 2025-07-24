import os
from typing import Dict, Any, List, Optional, Union
from .base import SceneConverter

class TextSceneConverter(SceneConverter):
    def _calculate_text_positions(
        self,
        text_entries: List[Dict[str, Any]],
        screen_width: int = 1920,
        screen_height: int = 1080,
        valign: str = 'center',
        padding: int = 40,
        line_spacing: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Calculate x and y positions for text entries

        Args:
            text_entries (List[Dict[str, Any]]): List of text entries
            screen_width (int): Width of the screen
            screen_height (int): Height of the screen
            valign (str): Vertical alignment
            padding (int): Vertical padding
            line_spacing (int): Space between lines

        Returns:
            List[Dict[str, Any]]: Text entries with x, y positions
        """
        # Calculate total text height
        total_height = sum(entry['font']['size'] for entry in text_entries)
        total_height += line_spacing * (len(text_entries) - 1)

        # Determine starting y based on vertical alignment
        if valign == 'top':
            start_y = padding
        elif valign == 'bottom':
            start_y = screen_height - total_height - padding
        else:  # center
            start_y = (screen_height - total_height) // 2

        # Prepare positioned entries
        positioned_entries = []
        current_y = start_y

        for entry in text_entries:
            # Calculate x based on horizontal alignment
            halign = entry.get('halign', 'center')
            font_size = entry['font']['size']

            # Placeholder width calculation (very simplistic)
            # In real implementation, you'd use a font metrics library
            estimated_text_width = len(entry['text']) * (font_size * 0.5)

            if halign == 'left':
                x = padding
            elif halign == 'right':
                x = screen_width - estimated_text_width - padding
            else:  # center
                x = (screen_width - estimated_text_width) // 2

            positioned_entry = {
                **entry,
                "x": int(x),
                "y": int(current_y),
                "font_size": entry['font']['size'],
                "font_color": entry['font']['color'],
                "font": entry['font']['file'],
                "bold": False,
                "italic": False
            }

            positioned_entries.append(positioned_entry)

            # Move to next line
            current_y += font_size + line_spacing

        return positioned_entries

    def convert(
        self,
        scene: Dict[str, Any],
        project_name: str = 'default'
    ) -> List[Dict[str, Any]]:
        """
        Convert a text scene to virtual clips

        Args:
            scene (Dict[str, Any]): Text scene details
            project_name (str): Name of the current project

        Returns:
            List[Dict[str, Any]]: Virtual clips for the text scene

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate mode
        if scene.get('mode') != 'all':
            raise ValueError("This converter only supports 'all' mode")

        # Validate background configuration
        if 'background' in scene and 'bgcolor' in scene:
            raise ValueError("Cannot specify both 'background' and 'bgcolor'")

        # Get screen size from input
        screen_size = scene.get('screen_size', [1920, 1080])
        screen_width, screen_height = screen_size

        # Validate text configuration
        text_entries = scene.get('text', [])
        if not text_entries:
            raise ValueError("At least one text entry is required")

        # Extract scene-level configurations
        valign = scene.get('valign', 'center')
        padding = scene.get('padding', 40)
        line_spacing = scene.get('line_spacing', 20)

        # Validate text configuration
        for entry in text_entries:
            # Validate mutually exclusive duration and TTS
            if 'duration' in entry and 'tts' in entry:
                raise ValueError("Cannot specify both 'duration' and 'tts' for a text entry")

            # Validate font configuration
            if 'font' not in entry:
                raise ValueError("Font configuration is required for each text entry")

            font = entry['font']
            if 'file' not in font:
                raise ValueError("Font file is required")
            if 'size' not in font:
                raise ValueError("Font size is required")
            if 'color' not in font:
                raise ValueError("Font color is required")

        # Calculate text positions
        positioned_entries = self._calculate_text_positions(
            text_entries,
            screen_width=screen_width,
            screen_height=screen_height,
            valign=valign,
            padding=padding,
            line_spacing=line_spacing
        )

        # Find TTS and duration-based entries
        tts_entries = [entry for entry in text_entries if 'tts' in entry]
        duration_entries = [entry for entry in text_entries if 'duration' in entry]

        # Prepare output vclips
        output_vclips = []

        # Generate vclips for TTS entries
        for tts_entry in tts_entries:
            vclip = {
                "type": "text"
            }

            # Add background or bgcolor
            if 'background' in scene:
                vclip['background'] = scene['background']
            elif 'bgcolor' in scene:
                vclip['bgcolor'] = scene['bgcolor']
            else:
                vclip['bgcolor'] = '#000000'  # Default background

            # Set TTS configuration
            vclip['tts'] = {
                "text": tts_entry['text'],
                "tts_engine": tts_entry['tts']['tts_engine'],
                "voice": tts_entry['tts']['voice'],
                "speed": tts_entry['tts'].get('speed', 1.0)
            }

            # Add positioned sentences
            vclip['sentences'] = positioned_entries

            output_vclips.append(vclip)

        # Generate vclips for duration-based entries
        for duration_entry in duration_entries:
            vclip = {
                "type": "text",
                "duration": duration_entry['duration']
            }

            # Add background or bgcolor
            if 'background' in scene:
                vclip['background'] = scene['background']
            elif 'bgcolor' in scene:
                vclip['bgcolor'] = scene['bgcolor']
            else:
                vclip['bgcolor'] = '#000000'  # Default background

            # Add positioned sentences
            vclip['sentences'] = positioned_entries

            output_vclips.append(vclip)

        # If no TTS or duration entries, raise an error
        if not output_vclips:
            raise ValueError("At least one text entry must have TTS or duration")

        return output_vclips