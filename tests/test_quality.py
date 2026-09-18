from harvester.analysis.quality import (
    QualityEvidence,
    ReplacementDecision,
    assess_replacement,
    quality_score,
)


def test_lossless_candidate_can_replace_matching_lossy_source() -> None:
    current = QualityEvidence(codec="mp3", bitrate_kbps=128, cutoff_hz=16_000)
    candidate = QualityEvidence(
        codec="flac",
        sample_rate_hz=44_100,
        cutoff_hz=21_000,
        identity_match=True,
    )

    assessment = assess_replacement(current, candidate)

    assert assessment.decision is ReplacementDecision.REPLACE
    assert assessment.candidate_score > assessment.current_score
    assert "lossless" in assessment.reasons[0]


def test_higher_nominal_bitrate_is_not_automatic_replacement() -> None:
    current = QualityEvidence(codec="mp3", bitrate_kbps=128, cutoff_hz=16_000)
    candidate = QualityEvidence(
        codec="mp3",
        bitrate_kbps=320,
        cutoff_hz=16_000,
        identity_match=True,
    )

    assessment = assess_replacement(current, candidate)

    assert assessment.decision is ReplacementDecision.PREVIEW
    assert "materially better" in assessment.reasons[-1]


def test_synthetic_high_band_requires_explicit_review() -> None:
    current = QualityEvidence(codec="mp3", bitrate_kbps=128, cutoff_hz=16_000)
    candidate = QualityEvidence(
        codec="flac",
        cutoff_hz=21_000,
        identity_match=True,
        synthetic_high_band=True,
    )

    assessment = assess_replacement(current, candidate)

    assert assessment.decision is ReplacementDecision.PREVIEW
    assert assessment.reasons == ("synthetic band requires review",)


def test_quality_score_does_not_reward_synthetic_band() -> None:
    natural = QualityEvidence(codec="opus", bitrate_kbps=160, cutoff_hz=20_000)
    synthetic = QualityEvidence(
        codec="opus",
        bitrate_kbps=160,
        cutoff_hz=20_000,
        synthetic_high_band=True,
    )

    assert quality_score(natural) == quality_score(synthetic)
