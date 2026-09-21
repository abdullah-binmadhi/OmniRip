"""Lane provenance: every grid row says what it is (docs/13)."""

from __future__ import annotations

from harvester.analysis.enhancement.lane_plan import (
    ORIGIN_CREDIT,
    ORIGIN_EXTRA,
    ORIGIN_MIX,
    ORIGIN_SEPARATOR,
    ORIGIN_SPLIT,
    ORIGIN_TAG,
    decode_plan,
    encode_plan,
    lane_for_credit,
    plan_lanes,
)
from harvester.services.musicbrainz import Credit


def test_lane_for_credit_maps_documented_instruments() -> None:
    assert lane_for_credit("double bass") == "bass"
    assert lane_for_credit("electric guitar") == "guitar"
    assert lane_for_credit("lead vocals") == "vocals"
    assert lane_for_credit("drum machine") == "drums"
    assert lane_for_credit("synthesizer") == "other"
    # Nothing can render these — they must stay credit-only.
    assert lane_for_credit("saxophone") is None
    assert lane_for_credit("") is None


def test_plan_marks_separator_splits_and_whole_families() -> None:
    plan = plan_lanes(
        ["vocals", "kick", "snare", "hats", "bass", "other"],
        splits={"drums": ("kick", "snare", "hats")},
        kept_whole=["bass"],
    )
    assert plan.origin_of("vocals") == ORIGIN_SEPARATOR
    assert plan.origin_of("kick") == ORIGIN_SPLIT
    assert plan.confidence_of("kick") == "medium"
    assert "drums" in plan.note_of("kick")
    assert plan.origin_of("bass") == ORIGIN_SEPARATOR
    assert "kept whole" in plan.note_of("bass")
    assert plan.rendered_lanes == ("vocals", "kick", "snare", "hats", "bass", "other")


def test_plan_marks_six_source_extras_as_low_confidence() -> None:
    plan = plan_lanes(["vocals", "other", "guitar", "piano"], extras=("guitar", "piano"))
    assert plan.origin_of("guitar") == ORIGIN_EXTRA
    assert plan.confidence_of("guitar") == "low"
    assert plan.origin_of("piano") == ORIGIN_EXTRA
    assert "2 6-source model" in plan.summary()


def test_plan_marks_the_eco_mix_lane() -> None:
    plan = plan_lanes(["vocals", "mix"])
    assert plan.origin_of("mix") == ORIGIN_MIX


def test_credits_annotate_rendered_lanes() -> None:
    credits = [
        Credit(name="double bass", artist="Mich Gerber", relation_type="instrument"),
        Credit(name="lead vocals", artist="Imogen Heap", relation_type="vocal"),
        Credit(name="vocal", artist="Richie Mills", relation_type="vocal"),
    ]
    plan = plan_lanes(
        ["vocals", "bass", "other"],
        credit_instruments=credits,
        singer_count=2,
    )
    assert "MusicBrainz credit" in plan.note_of("bass")
    assert "Mich Gerber" in plan.note_of("bass")
    assert "lead vocals" in plan.note_of("vocals")
    assert plan.singer_count == 2
    assert "2 singers" in plan.summary()


def test_credited_instrument_without_a_separator_becomes_a_row_without_audio() -> None:
    """A credited saxophone is listed, but never gets a fake audio row."""
    credits = [Credit(name="saxophone", artist="Session Player", relation_type="instrument")]
    plan = plan_lanes(["vocals", "other"], credit_instruments=credits)

    entry = plan.entry("saxophone")
    assert entry is not None
    assert entry.origin == ORIGIN_CREDIT
    assert entry.rendered is False
    assert "no separator renders it" in entry.note
    assert "saxophone" not in plan.rendered_lanes
    assert [m.name for m in plan.missing] == ["saxophone"]
    assert "credits only" in plan.summary()


def test_plan_accepts_plain_string_credits() -> None:
    plan = plan_lanes(["vocals", "bass"], credit_instruments=["double bass", "violin"])
    assert "credit" in plan.note_of("bass")
    violin = plan.entry("violin")
    assert violin is not None
    assert violin.rendered is False


def test_tag_only_labels_are_listed_without_audio() -> None:
    plan = plan_lanes(["vocals"], tag_labels=("synth pad",))
    entry = plan.entry("synth pad")
    assert entry is not None
    assert entry.rendered is False
    assert "tagger" in entry.note


def test_tags_annotate_a_rendered_lane_instead_of_duplicating_it() -> None:
    """A guitar tag annotates the guitar row; unrenderable tags become rows."""
    plan = plan_lanes(["vocals", "guitar"], extras=("guitar",), tag_labels=("guitar", "strings"))
    assert plan.origin_of("guitar") == ORIGIN_EXTRA
    assert "CLAP tag: guitar" in plan.note_of("guitar")
    assert [entry.name for entry in plan.entries].count("guitar") == 1
    strings = plan.entry("strings")
    assert strings is not None and strings.origin == ORIGIN_TAG
    assert plan.tag_labels == ("guitar", "strings")


def test_encode_decode_round_trip_keeps_provenance() -> None:
    plan = plan_lanes(
        ["vocals", "kick", "guitar"],
        splits={"drums": ("kick",)},
        extras=("guitar",),
        credit_instruments=[Credit(name="electric guitar", artist="G")],
        singer_count=3,
    )
    rows = encode_plan(plan)
    restored = decode_plan(rows, singer_count=plan.singer_count)

    assert [e.name for e in restored.entries] == [e.name for e in plan.entries]
    assert restored.origin_of("kick") == ORIGIN_SPLIT
    assert restored.origin_of("guitar") == ORIGIN_EXTRA
    assert restored.singer_count == 3
    restored_guitar = restored.entry("guitar")
    original_guitar = plan.entry("guitar")
    assert restored_guitar is not None and original_guitar is not None
    assert restored_guitar.note == original_guitar.note


def test_encode_decode_tolerates_missing_or_broken_plan() -> None:
    assert encode_plan(None) == []
    assert decode_plan(None).entries == ()
    assert decode_plan([{"nope": 1}, "junk", {"name": "vocals"}]).entries[0].name == "vocals"
