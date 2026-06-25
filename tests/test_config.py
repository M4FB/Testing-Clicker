"""[TDD] Coherencia de la configuración del juego."""
from src import config as C


def test_generators_well_formed():
    assert len(C.GENERATORS) == 5
    ids = [g["id"] for g in C.GENERATORS]
    assert ids == ["worker", "workshop", "factory", "lab", "research"]
    for g in C.GENERATORS:
        assert {"id", "name", "pps", "cost", "unlock"} <= g.keys()
        assert g["pps"] > 0 and g["cost"] > 0


def test_click_upgrades_count_and_keys():
    assert len(C.CLICK_UPGRADES) == 15
    seen = set()
    for u in C.CLICK_UPGRADES:
        assert u["id"] not in seen, "id duplicado"
        seen.add(u["id"])
        assert u["cost"] > 0
        assert "bonus" in u or "mult" in u


def test_gen_upgrades_targets_valid():
    assert len(C.GEN_UPGRADES) == 35
    valid = {g["id"] for g in C.GENERATORS} | {"all"}
    for u in C.GEN_UPGRADES:
        assert u["target"] in valid
        assert u["mult"] > 1.0


def test_prestige_upgrades_effects_known():
    known = {"start_workers", "pps_mult", "click_mult",
             "crit_chance", "golden_freq", "boost_dur",
             "autoclick_rate", "double_crit_chance", "price_discount"}
    for u in C.PRESTIGE_UPGRADES:
        assert u["effect"] in known
        assert u["cost"] > 0


def test_thresholds_ordered():
    assert C.PRESTIGE_1_THRESHOLD < C.PRESTIGE_2_THRESHOLD < C.VICTORY_THRESHOLD


def test_demo_mode_active():
    assert C.MODE == "demo"
    assert C.BOOST == 100
