from .base import TTSEngine
from .engine_factory import register_tts_engine
from typing import Dict, Any

# Debug TTS Engine (fallback)
@register_tts_engine('dummy')
class DummyTTSEngine(TTSEngine):
    """
    Placeholder/Debug TTS Engine for testing and fallback scenarios.
    """
    def __init__(self, **kwargs):
        """
        Initialize the debug TTS engine.

        Args:
            **kwargs: Arbitrary keyword arguments
        """
        self.config = kwargs

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
            output_path (Optional[str], optional): Path to save audio file
            **kwargs: Additional arguments

        Returns:
            str: Path to the generated (dummy) audio file
        """
        # Create a dummy audio file or just return a path
        if output_path:
            # Create an empty file for debugging
            with open(output_path, 'w') as f:
                f.write(f"DEBUG TTS: {text}")
            return output_path

        return f"debug_audio_{hash(text)}.wav"

    def list_available_voices(self) -> Dict[str, Any]:
        pass

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return True

    def gen_filename(self, **kwargs: Any) -> str:
        # other engine should have filename like super().gen_filename(**kwars)+"_{engine_name}_{voice}_{speed}_..."
        return "dummy.mp3"