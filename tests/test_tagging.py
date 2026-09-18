from pathlib import Path

import numpy as np
import soundfile as sf
from mutagen.flac import FLAC
from mutagen.id3 import ID3

from harvester.models import CanonicalMetadata
from harvester.services.tagging import MetadataTagger, metadata_from_probe


def _write_flac(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.zeros((44100, 2), dtype=np.int16)
    sf.write(path, data, 44100, format="FLAC", subtype="PCM_16")


def test_metadata_from_probe_uses_title_separator_and_uploader() -> None:
    metadata = metadata_from_probe({"title": "Artist - Song", "uploader": "Channel"})

    assert metadata.title == "Song"
    assert metadata.artist == "Channel"
    assert metadata.source == "probe"


def test_mp3_tagging_writes_id3v23_provenance_and_art(tmp_path: Path) -> None:
    path = tmp_path / "song.mp3"
    ID3().save(path, v2_version=3)
    MetadataTagger().tag_mp3(
        path,
        CanonicalMetadata(title="Song", artists=("Artist",), album="Album", year=2024),
        cover_bytes=b"JPEGDATA",
    )

    tags = ID3(path)
    assert tags.get("TIT2").text == ["Song"]
    assert tags.get("TXXX:SOURCE_ORIGIN").text == ["youtube_opus_transcoded_mp3"]
    assert tags.get("APIC:").data == b"JPEGDATA"
    assert tags.get("COMM::eng").text


def test_flac_tagging_writes_vorbis_picture_and_provenance(tmp_path: Path) -> None:
    path = tmp_path / "track.flac"
    _write_flac(path)
    MetadataTagger().tag_flac(
        path,
        CanonicalMetadata(
            title="Track",
            artists=("Artist",),
            album="Album",
            year=1999,
            mb_recording_id="rec-1",
            mb_release_id="rel-1",
            source="acoustid",
        ),
        cover_bytes=b"JPEGDATA",
    )

    audio = FLAC(path)
    assert audio["title"] == ["Track"]
    assert audio["artist"] == ["Artist"]
    assert audio["date"] == ["1999"]
    assert audio["SOURCE_ORIGIN"] == ["p2p_flac"]
    assert audio["TAG_ORIGIN"] == ["acoustid"]
    pictures = list(audio.pictures)
    assert len(pictures) == 1
    assert pictures[0].data == b"JPEGDATA"
    assert pictures[0].type == 3
