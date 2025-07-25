from typing import Dict, Any, List
from .all_mode import AllModeStrategy

class AllWithHighlightModeStrategy(AllModeStrategy):
    def convert(
        self,
        scene: Dict[str, Any],
        positioned_entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert text scene using 'all_with_highlight' mode strategy

        Args:
            scene (Dict[str, Any]): Scene configuration
            positioned_entries (List[Dict[str, Any]]): Positioned text entries

        Returns:
            List[Dict[str, Any]]: Generated virtual clips
        """
        # Validate highlight style
        if 'highlight_style' not in scene:
            raise ValueError("'highlight_style' is required for 'all_with_highlight' mode")

        highlight_style = scene['highlight_style']
        text_entries = scene.get('text', [])

        # Prepare output vclips
        output_vclips = []

        # Generate a vclip for each sentence
        for highlight_index, _ in enumerate(text_entries):
            # Create a copy of positioned entries to modify
            modified_entries = []

            for idx, entry in enumerate(positioned_entries):
                # Apply highlight style to the current sentence
                if idx == highlight_index:
                    highlighted_entry = {
                        **entry,
                        "font": highlight_style.get('font', entry['font']),
                        "font_color": highlight_style.get('font_color', entry['font_color']),
                        "bold": highlight_style.get('bold', False),
                        "italic": highlight_style.get('italic', False)
                    }
                    modified_entries.append(highlighted_entry)
                else:
                    modified_entries.append(entry)

            # Find the entry with TTS or duration for this vclip
            tts_entry = None
            duration = None

            if highlight_index < len(text_entries):
                current_entry = text_entries[highlight_index]
                if 'tts' in current_entry:
                    tts_entry = current_entry
                elif 'duration' in current_entry:
                    duration = current_entry['duration']

            # Create vclip
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

            # Add TTS or duration
            if tts_entry:
                vclip['tts'] = {
                    "text": tts_entry['text'],
                    "tts_engine": tts_entry['tts']['tts_engine'],
                    "voice": tts_entry['tts']['voice'],
                    "speed": tts_entry['tts'].get('speed', 1.0)
                }
            elif duration is not None:
                vclip['duration'] = duration
            else:
                raise ValueError("Each vclip must have either TTS or duration")

            # Add modified sentences
            vclip['sentences'] = modified_entries

            output_vclips.append(vclip)

        # If no TTS or duration entries, raise an error
        if not output_vclips:
            raise ValueError("At least one text entry must have TTS or duration")

        return output_vclips