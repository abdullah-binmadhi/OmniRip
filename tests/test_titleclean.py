from harvester.analysis.titleclean import build_queries, clean_title, fold_unicode


def test_fold_unicode_normalizes_diacritics() -> None:
    assert fold_unicode("Café naïve") == "Cafe naive"


def test_clean_title_strips_noise_and_track_prefixes() -> None:
    assert clean_title("01 - Artist - Song (Official Video)") == "Artist - Song"
    assert clean_title("Song [HD]") == "Song"
    assert clean_title("Track (1987)") == "Track"


def test_feat_is_kept_in_first_query_and_stripped_in_second() -> None:
    queries = build_queries("Artist", "Song (feat. Guest)")

    assert queries[0] == "Artist - Song (feat. Guest)"
    assert queries[1] == "Artist Song"
    assert len(queries) <= 3


def test_clean_is_idempotent() -> None:
    cleaned = clean_title("  Héllo   Wörld (Lyrics)  ")
    assert clean_title(cleaned) == cleaned


def test_build_queries_without_artist_falls_back_to_title() -> None:
    assert build_queries("", "Plain Title - The Sequel") == ("Plain Title - The Sequel",)
