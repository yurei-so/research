"""Conversation prosody metadata primitives."""

from conversation_prosody_pipeline.audio_file import WavInfo, ingest_wav_file, read_wav_info
from conversation_prosody_pipeline.audio_stream import (
    AudioChunk,
    StreamingFeatureAccumulator,
    ingest_wav_stream,
    iter_wav_chunks,
)
from conversation_prosody_pipeline.baseline import ProsodyBaseline
from conversation_prosody_pipeline.extractors import (
    FeatureExtractor,
    MockFeatureExtractor,
    TimingExtractor,
)
from conversation_prosody_pipeline.pipeline import ProsodyPipeline
from conversation_prosody_pipeline.types import (
    ProsodyDeltas,
    RawTurn,
    TurnFeatures,
    TurnMetadata,
    TurnTiming,
)

__all__ = [
    "FeatureExtractor",
    "MockFeatureExtractor",
    "ProsodyBaseline",
    "ProsodyDeltas",
    "ProsodyPipeline",
    "RawTurn",
    "AudioChunk",
    "StreamingFeatureAccumulator",
    "TimingExtractor",
    "TurnFeatures",
    "TurnMetadata",
    "TurnTiming",
    "WavInfo",
    "ingest_wav_file",
    "ingest_wav_stream",
    "iter_wav_chunks",
    "read_wav_info",
]
