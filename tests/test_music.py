"""[TDD] Generación procedural de música y el MusicManager."""
import numpy as np

from src import music as M


def test_loops_shape_and_dtype():
    for gen, secs in ((M.generate_loop, 12.0),
                      (M.generate_menu_loop, 16.0),
                      (M.generate_config_loop, 14.0)):
        arr = gen(secs)
        assert arr.dtype == np.int16
        assert arr.ndim == 2 and arr.shape[1] == 2          # estéreo
        assert arr.shape[0] == int(44100 * secs)
        assert np.abs(arr).max() > 0                          # no es silencio


def test_tracks_are_distinct():
    g = M.generate_loop()
    me = M.generate_menu_loop()
    cf = M.generate_config_loop()
    # distintas longitudes y/o contenido → pistas diferentes
    assert not (g.shape == me.shape and np.array_equal(g, me))
    assert not (me.shape == cf.shape and np.array_equal(me, cf))


def test_seed_is_deterministic():
    a = M.generate_loop(seed=42)
    b = M.generate_loop(seed=42)
    assert np.array_equal(a, b)


def test_seed_introduces_variation():
    # La variación es discreta (varias variantes melódicas); sobre un abanico
    # de semillas deben aparecer al menos dos resultados distintos.
    sigs = {M.generate_loop(seed=s).tobytes() for s in range(8)}
    assert len(sigs) >= 2


def test_session_seed_sets_all_tracks():
    M.set_session_seed(123)
    assert set(M._seeds) == {"game", "menu", "config"}
    # reproducible
    M.set_session_seed(123)
    s1 = dict(M._seeds)
    M.set_session_seed(123)
    assert s1 == M._seeds


def test_get_sound_caches():
    M._reset_cache()
    s1 = M.get_sound("menu")
    s2 = M.get_sound("menu")
    assert s1 is s2


def test_prepare_async_populates_cache():
    M._reset_cache()
    th = M.prepare_async(("config",))
    th.join(30)
    assert "config" in M._arr_cache


def test_manager_volume_and_duck():
    mgr = M.MusicManager(volume=0.5)
    assert mgr.get_volume() == 0.5
    mgr.set_volume(0.8)
    assert mgr.get_volume() == 0.8
    mgr.duck(0.25)
    assert abs(mgr._applied() - 0.8 * 0.25) < 1e-9
    mgr.unduck()
    assert mgr._applied() == 0.8


def test_manager_play_switches_current():
    mgr = M.MusicManager()
    mgr.play("menu")
    assert mgr.current == "menu"
    mgr.play("game")
    assert mgr.current == "game"
    mgr.stop()
    assert mgr.current is None
