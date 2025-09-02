from typing import Dict, Any, List
from .base import TextSceneStrategy

class AppendCenterModeStrategy(TextSceneStrategy):
    def calculate_text_positions(
        self,
        text_entries: List[Dict[str, Any]],
        screen_size: List[int],
        valign: str = 'error',
        halign: str = 'error',
        padding: int = 40,
        line_spacing: int = 20
    ) -> List[List[Dict[str, Any]]]:
        """
        Calculate text positions for 'append_center' mode

        Args:
            text_entries (List[Dict[str, Any]]): List of text entries
            screen_size (List[int]): Screen dimensions [width, height]
            valign (str): Vertical alignment
            halign (str): Horizontal alignment
            padding (int): Vertical padding
            line_spacing (int): Space between lines

        Returns:
            List[List[Dict[str, Any]]]: List of positioned entries for each vclip
        """
        screen_width, screen_height = screen_size

        # Will store positioning for each vclip
        all_positioned_entries = []

        # Precompute x positions for each entry
        x_positions = []
        for entry in text_entries:
            font = entry['font']
            halign = entry.get('halign', halign)

            # Calculate x based on horizontal alignment
            x, adjusted_fontsize = self._calculate_x_position(
                entry['text'],
                font['size'],
                font['file'],
                screen_width,
                halign,
                padding
            )

            entry['font']['size'] = adjusted_fontsize

            x_positions.append(x)

        # Generate positioning for each progressive set of sentences
        for num_sentences in range(1, len(text_entries) + 1):
            # Create positioned entries for this vclip
            positioned_entries = []

            for idx in range(num_sentences):
                entry = text_entries[idx]
                font_size = entry['font']['size']

                # Calculate y position
                # The latest sentence centers vertically
                # Previous sentences shift up
                latest_sentence_y = screen_height // 2
                current_y = latest_sentence_y - ((num_sentences - 1 - idx) * (font_size + line_spacing))

                positioned_entry = {
                    **entry,
                    "x": int(x_positions[idx]),
                    "y": int(current_y),
                    "font_size": entry['font']['size'],
                    "font_color": entry['font']['color'],
                    "font": entry['font']['file'],
                    "bold": False,
                    "italic": False
                }

                # Clean sentences by removing 'tts' and 'halign'
                positioned_entry = self.clean_attributes(positioned_entry)

                positioned_entries.append(positioned_entry)

            # Store positioned entries for this vclip
            all_positioned_entries.append(positioned_entries)

        return all_positioned_entries

    def convert(
        self,
        scene: Dict[str, Any],
        positioned_entries_list: List[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Convert text scene using 'append_center' mode strategy

        Args:
            scene (Dict[str, Any]): Scene configuration
            positioned_entries_list (List[List[Dict[str, Any]]]): List of positioned entries for each vclip

        Returns:
            List[Dict[str, Any]]: Generated virtual clips
        """
        # Find entries with TTS or duration
        text_entries = scene.get('text', [])

        # Prepare output vclips
        output_vclips = []

        # Generate vclips for TTS entries
        for i, txt_entry in enumerate(text_entries):
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

            # Add positioned sentences for this vclip
            vclip['sentences'] = positioned_entries_list[i]

            output_vclips.append(vclip)

        return output_vclips