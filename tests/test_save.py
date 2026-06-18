"""[TDD] Guardado/carga de partida y preferencias."""
from src.config import BOOST
from src.game import GameState
from src import save as S


def test_round_trip_preserves_progress(tmp_save):
    g = GameState()
    g.points = 4321.0
    g.total_points = 9999.0
    g.generators["worker"] = 7
    g.click_upgrades["cu_1"] = True
    g.stats["clicks"] = 42
    g.stats["history"] = [1.0, 2.0, 3.0]
    S.save_game(g, elapsed=123.0, path=tmp_save)

    loaded, meta = S.load_game(path=tmp_save)
    assert loaded is not None
    assert loaded.points == 4321.0
    assert loaded.total_points == 9999.0
    assert loaded.generators["worker"] == 7
    assert loaded.click_upgrades["cu_1"] is True
    assert loaded.stats["clicks"] == 42
    assert loaded.stats["history"] == [1.0, 2.0, 3.0]
    assert meta["elapsed"] == 123.0


def test_has_compatible_save_matches_mode(tmp_save):
    g = GameState()
    S.save_game(g, path=tmp_save)
    assert S.has_compatible_save(path=tmp_save) is True


def test_load_missing_returns_none(tmp_path):
    loaded, meta = S.load_game(path=str(tmp_path / "nope.json"))
    assert loaded is None and meta == {}


def test_load_tolerates_unknown_keys(tmp_save):
    g = GameState()
    g.generators["worker"] = 3
    S.save_game(g, path=tmp_save)
    import json
    with open(tmp_save) as fh:
        data = json.load(fh)
    data["generators"]["ghost_gen"] = 99       # clave inexistente en config
    data["stats"]["weird"] = 1
    with open(tmp_save, "w") as fh:
        json.dump(data, fh)
    loaded, _ = S.load_game(path=tmp_save)
    assert loaded is not None
    assert loaded.generators["worker"] == 3
    assert "ghost_gen" not in loaded.generators


def test_delete_save(tmp_save):
    g = GameState()
    S.save_game(g, path=tmp_save)
    S.delete_save(path=tmp_save)
    assert S.save_info(path=tmp_save) is None


def test_prefs_defaults_when_absent(tmp_prefs):
    prefs = S.load_prefs(path=tmp_prefs)
    assert prefs == S.DEFAULT_PREFS


def test_prefs_round_trip_and_clamp(tmp_prefs):
    S.save_prefs(music_vol=2.0, sfx_vol=-1.0, fullscreen=True, path=tmp_prefs)
    prefs = S.load_prefs(path=tmp_prefs)
    assert prefs["music_vol"] == 1.0       # recortado a [0,1]
    assert prefs["sfx_vol"] == 0.0
    assert prefs["fullscreen"] is True


def test_prefs_partial_merge(tmp_prefs):
    S.save_prefs(music_vol=0.5, path=tmp_prefs)
    S.save_prefs(sfx_vol=0.2, path=tmp_prefs)
    prefs = S.load_prefs(path=tmp_prefs)
    assert prefs["music_vol"] == 0.5 and prefs["sfx_vol"] == 0.2
