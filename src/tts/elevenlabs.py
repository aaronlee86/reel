import os
import requests
from typing import Dict, Any, Optional
from .engine_factory import register_tts_engine
from src.tts.base import TTSEngine
from dotenv import load_dotenv
from elevenlabs import Voice, VoiceSettings
from elevenlabs.client import ElevenLabs

load_dotenv()

@register_tts_engine('eleven')
class ElevenLabsTTSEngine(TTSEngine):
    """
    ElevenLabs Text-to-Speech Engine implementation.
    """
    def __init__(self):
        """
        Initialize the ElevenLabs TTS Engine.
        Raises:
            ValueError: If no API key is provided
        """
        self.api_key = os.environ.get('ELEVENLABS_API_KEY')
        if not self.api_key:
            raise ValueError("ElevenLabs API key not found. Set ELEVENLABS_API_KEY environment variable.")


        self.client = ElevenLabs(
            api_key= self.api_key
        )
        self.name = self.__class__.__name__

    def call_api(self, payload: Dict[str, Any]) -> requests.Response:
        """
        Call the ElevenLabs API to generate speech.

        Args:
            payload (Dict[str, Any]): Payload containing text and voice parameters

        Returns:
            requests.Response: API response
        """
        audio_generator = self.client.text_to_speech.convert(text=payload['text'], model_id="eleven_v3",
            output_format="mp3_44100_128",
            voice_settings=VoiceSettings(stability=1.0, similarity_boost=0.5, style=0.0, use_speaker_boost=True, speed=payload['speed']),
            voice_id=payload['voice']
        )
        return b"".join(audio_generator)

    def generate_audio(
            self,
            text: str,
            output_path: str,
            **kwargs
        ) -> str:
        """
        Synthesize text to speech using ElevenLabs TTS.

        Args:
            text (str): Text to convert to speech
            output_path (str): Path to save audio file
            **kwargs: Additional arguments for voice generation

        Returns:
            str: Path to the generated audio file
        """
        if os.path.exists(output_path):
            print(f"[{self.__class__.__name__}] Audio already exists at: {output_path}. Skipping generation.")
            return output_path

        # Prepare payload with default values
        payload = {
            'text': text,
            'voice': kwargs.get('voice'),
            'stability': kwargs.get('stability', 0.5),
            'similarity_boost': kwargs.get('similarity_boost', 0.5),
            'style': kwargs.get('style', 0.0),
            'speed': kwargs.get('speed', 1.0),
            'use_speaker_boost': kwargs.get('use_speaker_boost', True)
        }

        try:
            response = self.call_api(payload)

            # Write the audio content to file
            with open(output_path, 'wb') as file:
                file.write(response)

            print(f"[{self.name}] Generated audio at: {output_path}")
        except Exception as e:
            raise RuntimeError(f"{self.name} generation failed: {e}")

        return output_path

    def list_available_voices(self) -> Dict[str, Any]:
        """
        List available voices from ElevenLabs.

        Returns:
            Dict[str, Any]: A dictionary of available voices with their details.

        Raises:
            NotImplementedError: If the method is not fully implemented.
        """
        raise NotImplementedError(f"{self.name}")

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate the configuration for ElevenLabs TTS.

        Args:
            config (Dict[str, Any]): Configuration dictionary to validate

        Returns:
            bool: True if configuration is valid, False otherwise
        """
        keys_to_check = ['tts_engine', 'voice', 'text']
        for key in keys_to_check:
            if key not in config:
                raise ValueError(f"Invalid configuration for TTS engine '{self.name}': lack of {key}")

        return True

    def gen_filename(self, **kwargs: Any) -> str:
        """
        Generate a unique filename for the audio output.

        Args:
            **kwargs: Keyword arguments for filename generation

        Returns:
            str: Generated filename
        """
        try:
            engine_name, voice, speed = kwargs['tts_engine'], kwargs['voice'], kwargs['speed']
            return super().gen_filename(**kwargs)+f"_{engine_name}_{voice}_{speed}.mp3"
        except Exception as e:
            raise ValueError(f"gen_filename in {self.name} failed: {e}")