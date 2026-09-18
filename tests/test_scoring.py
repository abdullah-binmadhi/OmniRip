from harvester.analysis.scoring import is_hard_filtered, rank_candidates, score_candidate
from harvester.models import P2PCandidate


def _candidate(**kwargs) -> P2PCandidate:
    defaults = {
        "username": "peer",
        "filename": "artist - song.flac",
        "size_bytes": 26_000_000,
        "duration_s": 240.0,
        "bit_depth": 16,
        "sample_rate": 44_100,
        "queue_length": 0,
        "user_speed_kbps": 1000,
    }
    defaults.update(kwargs)
    return P2PCandidate(**defaults)


def test_hard_filter_rejects_wrong_extension() -> None:
    assert is_hard_filtered(_candidate(filename="song.mp3"), expected_duration_s=240.0)


def test_hard_filter_rejects_low_bit_depth() -> None:
    assert is_hard_filtered(_candidate(bit_depth=8), expected_duration_s=240.0)


def test_hard_filter_rejects_duration_mismatch() -> None:
    assert is_hard_filtered(_candidate(duration_s=100.0), expected_duration_s=240.0)


def test_ranking_puts_high_quality_peer_first() -> None:
    weak = _candidate(username="low", user_speed_kbps=200, queue_length=15)
    strong = _candidate(username="high", user_speed_kbps=1200, queue_length=0, bit_depth=24)

    ranked = rank_candidates([weak, strong], expected_duration_s=240.0)

    assert ranked[0].username == "high"


def test_spam_filename_is_penalized() -> None:
    clean = _candidate(username="a", user_speed_kbps=400)
    spam = _candidate(
        username="b", user_speed_kbps=600, filename="artist - song www.example.com.flac"
    )

    assert score_candidate(
        spam, expected_duration_s=240.0, expected_size_bytes=40_000_000
    ) < score_candidate(clean, expected_duration_s=240.0, expected_size_bytes=40_000_000)


def test_tie_break_is_deterministic_with_seed() -> None:
    first = rank_candidates(
        [_candidate(username="x"), _candidate(username="y")], expected_duration_s=240.0, seed=7
    )
    second = rank_candidates(
        [_candidate(username="x"), _candidate(username="y")], expected_duration_s=240.0, seed=7
    )

    assert [c.username for c in first] == [c.username for c in second]
