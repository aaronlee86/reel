from .base import TTSEngine
from .engine_factory import register_tts_engine
from typing import Dict, Any
import os

# Debug TTS Engine (fallback)
@register_tts_engine('dummy')
class DummyTTSEngine(TTSEngine):
    """
    Placeholder/Debug TTS Engine for testing and fallback scenarios.
    """
    def generate_audio(
        self,
        text: str,
        output_path: str,
        **kwargs
    ) -> str:
        """
        Generate a dummy audio file for debugging.

        Args:
            text (str): Text to convert to speech
            output_path (str): Path to save audio file
            **kwargs: Additional arguments

        Returns:
            str: Path to the generated (dummy) audio file
        """
        if os.path.exists(output_path):
            print(f"[{self.__class__.__name__}] Audio already exists at: {output_path}. Skipping generation.")
            return output_path

        # Create a dummy audio file or just return a path
        try:
            # Create an empty file for debugging
            with open(output_path, 'w') as f:
                f.write(f"DEBUG TTS: {text}")
            print(f"[{self.__class__.__name__}] Generated dummy audio at: {output_path}")
        except Exception as e:
            raise RuntimeError(f"{self.__class__.__name__} generation failed: {e}")

        return output_path

    def list_available_voices(self) -> Dict[str, Any]:
        pass

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return True

    def gen_filename(self, **kwargs: Any) -> str:
        # other engine should have filename like super().gen_filename(**kwars)+"_{engine_name}_{voice}_{speed}_..."
        return "dummy.mp3"