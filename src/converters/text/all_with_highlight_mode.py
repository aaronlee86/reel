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

            current_entry = text_entries[highlight_index]
            vclip = self._create_vclip(current_entry, scene, positioned_entries)

            output_vclips.append(vclip)

        return output_vclips