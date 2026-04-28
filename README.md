# Multi-lingual Transcription using Whisper

This is a simple web application that allows users to transcribe audio files into text using the [Whisper Automatic Speech Recognition (ASR) model](https://github.com/openai/whisper). The application is built using Streamlit and leverages OpenAI's Whisper to perform transcriptions.

## How to Use

* **Upload Audio**: Drag and drop (or browse) an audio file in WAV, MP3, M4A, AAC, FLAC, or OGG format.
  ![alt text](https://github.com/fizamusthafa/whisper-app/blob/master/overview.png "Drag or Upload")
* **Transcribe Audio**: Once the audio file is uploaded, click on the "Transcribe audio" button. The application will start transcribing the audio using the Whisper model.
* **Supported Languages**: The Whisper model supports multiple languages. The application will automatically detect the language of the uploaded audio and provide accurate transcriptions for a wide range of languages. This includes *Afrikaans, Arabic, Armenian, Azerbaijani, Belarusian, Bosnian, Bulgarian, Catalan, Chinese, Croatian, Czech, Danish, Dutch, English, Estonian, Finnish, French, Galician, German, Greek, Hebrew, Hindi, Hungarian, Icelandic, Indonesian, Italian, Japanese, Kannada, Kazakh, Korean, Latvian, Lithuanian, Macedonian, Malay, Marathi, Maori, Nepali, Norwegian, Persian, Polish, Portuguese, Romanian, Russian, Serbian, Slovak, Slovenian, Spanish, Swahili, Swedish, Tagalog, Tamil, Thai, Turkish, Ukrainian, Urdu, Vietnamese, and Welsh.*
* **Clean-up**: After the transcription is complete, the temporary audio file will be removed to ensure your data privacy.

## Requirements

To run this application locally, install the dependencies:
```
pip install -r requirements.txt
```

## How to Run

* Clone this repository to your local machine.
* Open a terminal or command prompt and navigate to the repository's directory.
* Run the Streamlit application: `streamlit run whisper-app.py`
* The application will open in your web browser, and you can start transcribing audio files right away.

## Deploy on Railway

1. Create a new Railway project and connect this repository.
2. Set the Start Command:
  `streamlit run whisper-app.py --server.port $PORT --server.address 0.0.0.0`
3. Ensure `ffmpeg` is available:
  - Add an environment variable `NIXPACKS_PKGS=ffmpeg` if you use Nixpacks.
  - Or install ffmpeg in a Dockerfile if you deploy with Docker.

## Deploy on Railway (Docker + Redis)

1. Create a new Railway project and connect this repository.
2. Add a Redis service to the project.
3. Set environment variables on the app service:
  - `REDIS_URL` from the Redis service.
  - Optional: `REDIS_TTL_SECONDS` (default is 604800).
4. Railway will detect the Dockerfile and build automatically.
  - No Start Command is required when using Docker.

