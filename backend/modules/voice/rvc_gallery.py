"""
Pre-trained RVC Voice Model Gallery.
Provides metadata for curated voice models users can install.
"""

import os
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger("rvc_gallery")


@dataclass
class GalleryVoice:
    """A voice model available from the gallery."""
    id: str
    name: str
    description: str
    category: str       # "professional", "casual", "character"
    gender: str         # "male", "female", "neutral"
    edge_voice: str     # Edge TTS base voice (used as fallback)
    f0_method: str      # Pitch extraction method
    accent: str         # "american", "british", etc.
    license_info: str


# Curated gallery of pre-trained voice profiles
# RVC .onnx model download URLs will be populated when models are hosted
GALLERY_VOICES: List[GalleryVoice] = [
    GalleryVoice(
        id="gallery_aria_pro",
        name="Aria Professional (Female)",
        description="Clear, professional female voice ideal for interview practice and business scenarios",
        category="professional",
        gender="female",
        edge_voice="en-US-AriaNeural",
        f0_method="rmvpe",
        accent="american",
        license_info="CC-BY-4.0",
    ),
    GalleryVoice(
        id="gallery_guy_pro",
        name="Guy Professional (Male)",
        description="Deep, authoritative male voice for interview scenarios and formal presentations",
        category="professional",
        gender="male",
        edge_voice="en-US-GuyNeural",
        f0_method="rmvpe",
        accent="american",
        license_info="CC-BY-4.0",
    ),
    GalleryVoice(
        id="gallery_davis_casual",
        name="Andrew Casual (Male)",
        description="Friendly, conversational male voice suited for mock interviews and practice",
        category="casual",
        gender="male",
        edge_voice="en-US-AndrewNeural",
        f0_method="rmvpe",
        accent="american",
        license_info="CC-BY-4.0",
    ),
    GalleryVoice(
        id="gallery_jenny_warm",
        name="Jenny Warm (Female)",
        description="Warm, encouraging female voice perfect for supportive interview practice",
        category="casual",
        gender="female",
        edge_voice="en-US-JennyNeural",
        f0_method="rmvpe",
        accent="american",
        license_info="CC-BY-4.0",
    ),
    GalleryVoice(
        id="gallery_sonia_uk",
        name="Sonia British (Female)",
        description="British English female voice for international interview preparation",
        category="professional",
        gender="female",
        edge_voice="en-GB-SoniaNeural",
        f0_method="rmvpe",
        accent="british",
        license_info="CC-BY-4.0",
    ),
    GalleryVoice(
        id="gallery_thomas_uk",
        name="Thomas British (Male)",
        description="British English male voice for professional UK-style interviews",
        category="professional",
        gender="male",
        edge_voice="en-GB-ThomasNeural",
        f0_method="rmvpe",
        accent="british",
        license_info="CC-BY-4.0",
    ),
]


def list_gallery(category: Optional[str] = None,
                 gender: Optional[str] = None) -> List[Dict]:
    """List available gallery voices, optionally filtered."""
    results = []
    for voice in GALLERY_VOICES:
        if category and voice.category != category:
            continue
        if gender and voice.gender != gender:
            continue
        results.append({
            "id": voice.id,
            "name": voice.name,
            "description": voice.description,
            "category": voice.category,
            "gender": voice.gender,
            "edge_voice": voice.edge_voice,
            "f0_method": voice.f0_method,
            "accent": voice.accent,
            "license_info": voice.license_info,
        })
    return results


def get_gallery_voice(gallery_id: str) -> Optional[GalleryVoice]:
    """Get a specific gallery voice by ID."""
    for voice in GALLERY_VOICES:
        if voice.id == gallery_id:
            return voice
    return None