import os
import wave
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from .engine_factory import register_tts_engine
from src.tts.base import TTSEngine

# Set up the wave file to save the output:
def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
   with wave.open(filename, "wb") as wf:
      wf.setnchannels(channels)
      wf.setsampwidth(sample_width)
      wf.setframerate(rate)
      wf.writeframes(pcm)

@register_tts_engine('gemini')
class GeminiTTSEngine(TTSEngine):
    """
    Google Cloud Text-to-Speech Engine implementation with lazy importing.
    """

    def __init__(self):
        """
        Initialize the Google Cloud TTS Engine.
        Client is created lazily when first needed.
        """
        self._client = None
        self._texttospeech = None
        self.api_key = os.environ.get('GOOGLE_API_KEY')
        self.name = self.__class__.__name__
        print(f"{self.name} Created")

    @property
    def texttospeech(self):
        """Lazy import of texttospeech module"""
        if self._texttospeech is None:
            print(f"dynamic importing genai from google")
            self._texttospeech = genai
        return self._texttospeech

    @property
    def client(self):
        """Lazy initialization of TTS client"""
        if self._client is None:
            self._client = self.texttospeech.Client(api_key=self.api_key)
        return self._client

    def call_api(self, payload):
        # Now using the lazy-loaded module

        # Build the voice request
        speaking_rate = payload['speed']

        # Split voice to get accent and voice name
        accent, voice = payload['voice'].split("-")

        response = self.client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=f"""Read the following in authentic {accent} accent with native speaker's speed:

            {payload['text']}""",
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                        )
                    )
                )
            )
        )

        return response.candidates[0].content.parts[0].inline_data.data

    def generate_audio(
            self,
            text: str,
            output_path: str,
            **kwargs
        ) -> str:
        """
        Synthesize text to speech using Google Cloud TTS.

        Args:
            text (str): Text to convert to speech
            output_path (str): Path to save audio file
            **kwargs: Additional arguments

        Returns:
            str: Path to the generated audio file
        """
        if os.path.exists(output_path):
            print(f"[{self.__class__.__name__}] Audio already exists at: {output_path}. Skipping generation.")
            return output_path

        # Prepare payload with default values
        payload = {
            'text': text,
            'speed': kwargs.get('speed', 1.0),
            'voice': kwargs.get('voice')
        }

        try:
            response = self.call_api(payload)
            wave_file(output_path, response)
            print(f"[{self.name}] Generated audio at: {output_path}")
        except Exception as e:
            raise RuntimeError(f"{self.name} generation failed: {e}")

        return output_path

    def list_available_voices(self) -> Dict[str, Any]:
        """
        List available voices from Google Cloud TTS.

        Returns:
            Dict[str, Any]: A dictionary of available voices with their details.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError(f"{self.name}")

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate the configuration for Google Cloud TTS.

        Args:
            config (Dict[str, Any]): Configuration dictionary to validate

        Returns:
            bool: True if configuration is valid, False otherwise
        """
        keys_to_check =['tts_engine','voice','text']
        for key in keys_to_check:
            if key not in config.keys():
                raise ValueError(f"Invalid configuration for TTS engine '{self.name}': lack of {key}")
        return True

    def gen_filename(self, **kwargs: Any) -> str:
        try:
            engine_name, voice, speed = kwargs['tts_engine'], kwargs['voice'], kwargs['speed']
            return super().gen_filename(**kwargs)+f"_{engine_name}_{voice}_{speed}.wav"
        except Exception as e:
            raise ValueError(f"gen_filename in {self.name} failed: {e}")
