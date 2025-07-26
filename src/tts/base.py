from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Union
import hashlib

class TTSEngine(ABC):
    """
    Abstract base class for Text-to-Speech (TTS) engines.

    This class defines the interface for TTS engine implementations,
    ensuring a consistent approach to generating audio from text.
    """

    @abstractmethod
    def generate_audio(
        self,
        text: str,
        voice: str,
        speed: Optional[float] = 1.0,
        **kwargs: Any
    ) -> str:
        """
        Generate an audio file from the given text.

        Args:
            text (str): The text to be converted to speech.
            voice (str): Specific voice identifier.
            speed (Optional[float], optional): Speech rate multiplier.
                1.0 represents normal speed. Defaults to 1.0.
            **kwargs: Additional engine-specific parameters.

        Returns:
            str: Path to the generated audio file.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
            ValueError: For invalid input parameters.
        """
        pass

    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate the configuration for the TTS engine.

        Args:
            config (Dict[str, Any]): Configuration dictionary specific to the TTS engine.

        Returns:
            bool: True if configuration is valid, False otherwise.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        pass

    @abstractmethod
    def list_available_voices(self) -> Dict[str, Any]:
        """
        List available voices for the TTS engine.

        Returns:
            Dict[str, Any]: A dictionary of available voices with their details.
                            The exact structure depends on the specific engine.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        pass

    @abstractmethod
    def gen_filename(self, **kwargs: Any) -> str:
        return f"tts_{self.text_to_hash(kwargs.get('text'))}"

    def text_to_hash(self, text: str, length: int = 24) -> str:
        """
        Generate a fixed-length hash string from the input text.

        Args:
        text (str): The input text to hash.
        length (int): The desired length of the hash string (default 8).

        Returns:
        str: A hexadecimal hash string of the specified length.
        """
        # Create SHA-1 hash of the text (more than enough for uniqueness)
        sha1 = hashlib.sha1(text.encode('utf-8')).hexdigest()
        # Return the first `length` characters
        return sha1[:length]
