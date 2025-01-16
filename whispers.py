import torch
from transformers import pipeline
from transformers.pipelines.audio_utils import ffmpeg_read

# Инициализация конвейера (pipeline) глобально для эффективности
MODEL_NAME = "openai/whisper-large-v3-turbo"
DEVICE = -1  # -1 означает использование CPU

whisper_pipe = pipeline(
    task="automatic-speech-recognition",
    model=MODEL_NAME,
    chunk_length_s=30,
    device=DEVICE,
)

def whisper(audio_data: bytes, task: str = "transcribe") -> str:
    """
    Распознаёт текст из аудио данных с помощью модели Whisper Large V3 Turbo.

    Args:
        audio_data (bytes): Аудио данные в виде байтов.
        task (str): Тип задачи - "transcribe" для транскрипции или "translate" для перевода.

    Returns:
        str: Распознанный текст.
    """
    # Чтение аудио данных и преобразование их в массив NumPy
    audio_array = ffmpeg_read(audio_data, whisper_pipe.feature_extractor.sampling_rate)
    inputs = {
        "array": audio_array,
        "sampling_rate": whisper_pipe.feature_extractor.sampling_rate
    }

    # Выполнение распознавания
    result = whisper_pipe(
        inputs,
        generate_kwargs={"task": task},
        return_timestamps=False
    )

    return result["text"]
