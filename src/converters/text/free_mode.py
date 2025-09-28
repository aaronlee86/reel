from typing import Dict, Any, List
from .all_mode import AllModeStrategy

class FreeModeStrategy(AllModeStrategy):
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
            vclips = self._create_vclips(txt_entry, scene, positioned_entries)
            for one_vclip in vclips:
                one_vclip['image'] = scene.get('image',[])
                output_vclips.append(one_vclip)

        return output_vclips