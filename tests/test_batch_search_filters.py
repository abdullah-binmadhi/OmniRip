"""Tests for Soulseek search filters and multi-item batch URL ingestion."""

from __future__ import annotations

from harvester.services.slskd import (
    SearchResponse,
    SlskdFile,
    filter_search_responses,
)


def test_filter_search_responses_lossless_only():
    responses = [
        SearchResponse(
            user="audiophile",
            speed_kbps=1500,
            queue_length=0,
            files=(
                SlskdFile(filename="track1.flac", bitrate=1000),
                SlskdFile(filename="track2.mp3", bitrate=320),
            ),
        ),
        SearchResponse(
            user="mp3collector",
            speed_kbps=800,
            queue_length=1,
            files=(
                SlskdFile(filename="track3.mp3", bitrate=320),
                SlskdFile(filename="track4.aac", bitrate=256),
            ),
        ),
    ]

    # Filter lossless only
    lossless = filter_search_responses(responses, lossless_only=True)
    assert len(lossless) == 1
    assert lossless[0].user == "audiophile"
    assert len(lossless[0].files) == 1
    assert lossless[0].files[0].filename == "track1.flac"


def test_filter_search_responses_speed_and_queue():
    responses = [
        SearchResponse(
            user="fast_peer",
            speed_kbps=2500,
            queue_length=1,
            files=(SlskdFile(filename="track.flac", bitrate=900),),
        ),
        SearchResponse(
            user="slow_peer",
            speed_kbps=150,
            queue_length=0,
            files=(SlskdFile(filename="track.flac", bitrate=900),),
        ),
        SearchResponse(
            user="busy_peer",
            speed_kbps=3000,
            queue_length=15,
            files=(SlskdFile(filename="track.flac", bitrate=900),),
        ),
    ]

    filtered = filter_search_responses(
        responses,
        min_speed_kbps=500,
        max_queue_depth=5,
    )
    assert len(filtered) == 1
    assert filtered[0].user == "fast_peer"


def test_filter_search_responses_min_bitrate():
    responses = [
        SearchResponse(
            user="dj_pool",
            speed_kbps=1000,
            queue_length=0,
            files=(
                SlskdFile(filename="high.mp3", bitrate=320),
                SlskdFile(filename="medium.mp3", bitrate=192),
                SlskdFile(filename="low.mp3", bitrate=128),
            ),
        )
    ]

    filtered = filter_search_responses(responses, min_bitrate=320)
    assert len(filtered) == 1
    assert len(filtered[0].files) == 1
    assert filtered[0].files[0].filename == "high.mp3"
