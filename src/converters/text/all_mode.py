from typing import Dict, Any, List
from .base import TextSceneStrategy

class AllModeStrategy(TextSceneStrategy):
    def calculate_text_positions(
        self,
        text_entries: List[Dict[str, Any]],
        screen_size: List[int],
        valign: str,
        halign: str,
        v_padding: int,
        h_padding: int,
        para_spacing: int,
        line_spacing: int
    ) -> List[Dict[str, Any]]:
        """
        Calculate default text positions for 'all' mode

        Args:
            text_entries (List[Dict[str, Any]]): List of text entries
            screen_size (List[int]): Screen dimensions [width, height]
            valign (str): Vertical alignment
            halign (str): Horizontal alignment
            v_padding (int): Vertical padding
            h_padding (int): Horizontal padding
            para_spacing (int): Space between paragraphs
            line_spacing (int): Space between lines

        Returns:
            List[Dict[str, Any]]: Text entries with calculated positions
        """
        # Get screen size from input
        screen_width, screen_height = screen_size

        # First pass: handle wrapping, calculate heights and prepare positioning information
        positioned_calculations = [
            self._prepare_text_entry(entry, halign, screen_width, h_padding)
            for entry in text_entries
        ]

        total_height = sum(calc['height'] for calc in positioned_calculations)

        # Add paragraph spacing between entries
        total_height += para_spacing * (len(text_entries) - 1)

        # Determine starting y based on vertical alignment
        if valign == 'top':
            start_y = v_padding
        elif valign == 'bottom':
            start_y = screen_height - total_height - v_padding
        else:  # center
            start_y = (screen_height - total_height) // 2

        # Prepare positioned entries
        positioned_entries = []
        current_y = start_y

        for calc in positioned_calculations:
            entry = calc['entry']

            positioned_entry = {
                **entry,
                "x": int(calc['x']),
                "y": int(current_y),
                "font_size": calc['adjusted_fontsize'],
                "font_color": entry['font']['color'],
                "font": entry['font']['file'],
                "bold": False,
                "italic": False
            }

            # Clean sentences by removing 'tts' and 'halign'
            positioned_entry = self.clean_attributes(positioned_entry)

            # Add line_spacing if not specified in row
            if "line_spacing" not in positioned_entry:
                positioned_entry["line_spacing"] = line_spacing

            positioned_entries.append(positioned_entry)

            # Move to next line using the actual height of this entry
            current_y += calc['height'] + para_spacing

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
                    "text": self.remove_special_char_for_tts(txt_entry['dub'] if 'dub' in txt_entry else txt_entry['text']),
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