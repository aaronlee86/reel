from typing import Dict, Any, List
from .base import TextSceneStrategy

class AppendCenterModeStrategy(TextSceneStrategy):
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
    ) -> List[List[Dict[str, Any]]]:
        """
        Calculate text positions for 'append_center' mode
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
            List[List[Dict[str, Any]]]: List of positioned entries for each vclip
        """
        screen_width, screen_height = screen_size
        # Will store positioning for each vclip
        all_positioned_entries = []

        # First pass: handle wrapping, calculate heights and prepare positioning information
        positioned_calculations = [
            self._prepare_text_entry(entry, halign, screen_width, h_padding)
            for entry in text_entries
        ]

        # Generate positioning for each progressive set of sentences
        for num_sentences in range(1, len(text_entries) + 1):
            # Create positioned entries for this vclip
            positioned_entries = []
            total_content_height = 0

            # First, calculate total content height for this subset of sentences
            for idx in range(num_sentences):
                total_content_height += positioned_calculations[idx]['height']

            # Add paragraph spacing between sentences
            total_content_height += para_spacing * (num_sentences - 1)

            # Calculate starting Y position
            latest_sentence_y = screen_height // 2
            current_y = latest_sentence_y - (total_content_height // 2)

            for idx in range(num_sentences):
                calc = positioned_calculations[idx]
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
            vclip = self._create_vclip(txt_entry, scene, positioned_entries_list[i])
            output_vclips.append(vclip)

        return output_vclips