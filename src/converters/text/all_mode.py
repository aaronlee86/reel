from typing import Dict, Any, List
from .base import TextSceneStrategy

class AllModeStrategy(TextSceneStrategy):
    def calculate_text_positions(
        self,
        text_entries: List[Dict[str, Any]],
        screen_size: List[int],
        valign: str = 'center',
        halign: str = 'error',
        padding: int = 40,
        line_spacing: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Calculate default text positions for 'all' mode

        Args:
            text_entries (List[Dict[str, Any]]): List of text entries
            screen_size (List[int]): Screen dimensions [width, height]
            valign (str): Vertical alignment
            halign (str): Horizontal alignment
            padding (int): Vertical padding
            line_spacing (int): Space between lines

        Returns:
            List[Dict[str, Any]]: Text entries with calculated positions
        """
        # Calculate total text height
        total_height = sum(entry['font']['size'] for entry in text_entries)
        total_height += line_spacing * (len(text_entries) - 1)

        # Get screen size from input
        screen_width, screen_height = screen_size

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
            halign = entry.get('halign', halign)
            font = entry['font']


            # Calculate x based on horizontal alignment
            x, adjusted_fontsize = self._calculate_x_position(
                entry['text'],
                font['size'],
                font['file'],
                screen_width,
                halign,
                padding
            )

            positioned_entry = {
                **entry,
                "x": int(x),
                "y": int(current_y),
                "font_size": adjusted_fontsize,
                "font_color": entry['font']['color'],
                "font": entry['font']['file'],
                "bold": False,
                "italic": False
            }

            # Clean sentences by removing 'tts' and 'halign'
            positioned_entry = self.clean_attributes(positioned_entry)

            positioned_entries.append(positioned_entry)

            # Move to next line
            current_y += font['size'] + line_spacing

        return positioned_entries

    def convert(
        self,
        scene: Dict[str, Any],
        positioned_entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert text scene using 'all' mode strategy

        Args:
            scene (Dict[str, Any]): Scene configuration
            positioned_entries (List[Dict[str, Any]]): Positioned text entries

        Returns:
            List[Dict[str, Any]]: Generated virtual clips
        """
        # Find TTS and duration-based entries
        text_entries = scene.get('text', [])

        # Prepare output vclips
        output_vclips = []

        # Generate vclips for TTS entries
        for txt_entry in text_entries:
            if not 'tts' in txt_entry and not 'duration' in txt_entry:
                raise ValueError("Each vclip must have either TTS or duration")

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

            if 'tts' in txt_entry:
                # Set TTS configuration
                vclip['tts'] = {
                    "text": txt_entry['dub'] if 'dub' in txt_entry else txt_entry['text'],
                    "tts_engine": txt_entry['tts']['tts_engine'],
                    "voice": txt_entry['tts']['voice'],
                    "speed": txt_entry['tts'].get('speed', 1.0)
                }

            if 'duration' in txt_entry:
                vclip['duration'] = txt_entry['duration']

            # Add positioned sentences
            vclip['sentences'] = positioned_entries

            output_vclips.append(vclip)

        return output_vclips