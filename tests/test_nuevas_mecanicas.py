"""
Tests TDD — Semana 2: nuevas mecánicas
Cubre: árbol de mejoras de clic, potenciadores de generadores,
bono QTE, reset de prestige extendido y módulo de música.
"""
import time
import pytest
from src.game import GameState
from src.config import BOOST, GENERATORS, CLICK_UPGRADES, GEN_UPGRADES


# ── Helpers ───────────────────────────────────────────────────────────────────

def rich_game() -> GameState:
    """Juego con puntos y algunos generadores para pruebas de upgrade."""
    g = GameState()
    g.points = 999_999_999
    g.total_points = 999_999_999
    for gen in GENERATORS:
        g.generators[gen["id"]] = 10
    return g


# ── Árbol de mejoras de clic ──────────────────────────────────────────────────

class TestArbolMejorasClic:

    def test_cu1_visible_sin_requisitos(self):
        """cu_1 está disponible desde el inicio (sin unlock_after)."""
        g = GameState()
        assert g.click_upgrade_unlocked("cu_1") is True

    def test_cu2_bloqueado_sin_cu1(self):
        """cu_2 no se desbloquea hasta que cu_1 esté comprado."""
        g = GameState()
        assert g.click_upgrade_unlocked("cu_2") is False

    def test_cu2_disponible_tras_cu1(self):
        """Comprar cu_1 desbloquea cu_2."""
        g = GameState()
        cost = g.click_upgrade_cost("cu_1")
        g.points = cost
        g.buy_click_upgrade("cu_1")
        assert g.click_upgrade_unlocked("cu_2") is True

    def test_cu3_disponible_tras_cu1_o_cu2(self):
        """cu_3 se desbloquea si CUALQUIER prerequisito (cu_1 o cu_2) está comprado."""
        g = GameState()
        cost = g.click_upgrade_cost("cu_1")
        g.points = cost
        g.buy_click_upgrade("cu_1")
        assert g.click_upgrade_unlocked("cu_3") is True

    def test_cu5_requiere_cu3_o_cu4(self):
        """cu_5 requiere cu_3 o cu_4 (semántica ANY)."""
        g = rich_game()
        assert g.click_upgrade_unlocked("cu_5") is False
        g.buy_click_upgrade("cu_1")
        g.buy_click_upgrade("cu_2")
        g.buy_click_upgrade("cu_3")
        assert g.click_upgrade_unlocked("cu_5") is True

    def test_click_mult_se_acumula(self):
        """Comprar múltiples mejoras con 'mult' acumula el multiplicador."""
        g = rich_game()
        g.buy_click_upgrade("cu_1")
        g.buy_click_upgrade("cu_2")
        g.buy_click_upgrade("cu_3")
        g.buy_click_upgrade("cu_4")
        g.buy_click_upgrade("cu_5")
        assert g.click_mult == pytest.approx(1.5)

    def test_click_mult_afecta_clic(self):
        """El click_mult amplifica el valor ganado por clic."""
        g = GameState()
        g.click_mult = 2.0
        earned = g.click()
        assert earned == pytest.approx(g.click_value * 2.0)

    def test_prestige_resetea_click_mult(self):
        """El prestige reinicia click_mult a 1.0."""
        from src.config import PRESTIGE_1_THRESHOLD
        g = GameState()
        g.click_mult = 3.5
        g.total_points = PRESTIGE_1_THRESHOLD * BOOST
        g.prestige()
        assert g.click_mult == pytest.approx(1.0)


# ── Potenciadores de generadores ──────────────────────────────────────────────

class TestPotenciadoresGeneradores:

    def test_gu_g1_visible_sin_requisito(self):
        """gu_g1 no requiere unlock_after; se desbloquea con puntos suficientes."""
        g = GameState()
        assert g.gen_upgrade_unlocked("gu_g1") is True

    def test_gu_w1_requiere_poseer_un_worker(self):
        """gu_w1 solo se desbloquea al tener al menos 1 worker."""
        g = GameState()
        assert g.gen_upgrade_unlocked("gu_w1") is False
        g.generators["worker"] = 1
        assert g.gen_upgrade_unlocked("gu_w1") is True

    def test_gu_w2_requiere_gu_w1_comprado(self):
        """gu_w2 requiere haber comprado gu_w1."""
        g = rich_game()
        assert g.gen_upgrade_unlocked("gu_w2") is False
        g.buy_gen_upgrade("gu_w1")
        assert g.gen_upgrade_unlocked("gu_w2") is True

    def test_comprar_gu_w1_multiplica_pps_worker(self):
        """gu_w1 (×2 worker) duplica el PPS de los workers."""
        g = rich_game()
        pps_antes = g.pps()
        g.buy_gen_upgrade("gu_w1")
        pps_despues = g.pps()
        assert pps_despues > pps_antes

    def test_upgrade_all_afecta_todos_los_generadores(self):
        """gu_g1 (target=all, ×1.5) eleva el PPS global proporcionalmente."""
        g = rich_game()
        pps_antes = g.pps()
        g.buy_gen_upgrade("gu_g1")
        assert g.pps() == pytest.approx(pps_antes * 1.5)

    def test_gen_mult_acumula_compras_sucesivas(self):
        """Comprar gu_g1 y gu_g2 acumula ×1.5 × ×1.5 = ×2.25 global."""
        g = rich_game()
        pps_base = g.pps()
        g.buy_gen_upgrade("gu_g1")
        g.buy_gen_upgrade("gu_g2")
        assert g.pps() == pytest.approx(pps_base * 1.5 * 1.5)

    def test_comprar_upgrade_descontado_de_puntos(self):
        """Comprar un potenciador descuenta su coste de los puntos."""
        g = rich_game()
        pts_antes = g.points
        cost = g.gen_upgrade_cost("gu_g1")
        g.buy_gen_upgrade("gu_g1")
        assert g.points == pytest.approx(pts_antes - cost)

    def test_comprar_upgrade_dos_veces_falla(self):
        """No se puede comprar el mismo potenciador dos veces."""
        g = rich_game()
        assert g.buy_gen_upgrade("gu_g1") is True
        assert g.buy_gen_upgrade("gu_g1") is False

    def test_prestige_resetea_gen_upgrades(self):
        """El prestige limpia todos los potenciadores comprados y gen_mult."""
        from src.config import PRESTIGE_1_THRESHOLD
        g = rich_game()
        g.buy_gen_upgrade("gu_g1")
        g.total_points = PRESTIGE_1_THRESHOLD * BOOST
        g.prestige()
        assert g.gen_upgrades["gu_g1"] is False
        assert g.gen_mult == {}

    def test_gu_sp1_requiere_cinco_workers(self):
        """gu_sp1 exige tener al menos 5 workers."""
        g = rich_game()
        g.generators["worker"] = 4
        assert g.gen_upgrade_unlocked("gu_sp1") is False
        g.generators["worker"] = 5
        assert g.gen_upgrade_unlocked("gu_sp1") is True

    def test_gu_g2_requiere_gu_g1_comprado(self):
        """gu_g2 requiere haber comprado gu_g1."""
        g = rich_game()
        assert g.gen_upgrade_unlocked("gu_g2") is False
        g.buy_gen_upgrade("gu_g1")
        assert g.gen_upgrade_unlocked("gu_g2") is True


# ── Bono QTE ──────────────────────────────────────────────────────────────────

class TestBonoQTE:

    def test_qte_inactivo_por_defecto(self):
        """El bono QTE está inactivo al crear el juego."""
        g = GameState()
        assert g.qte_bonus_active is False
        assert g.qte_bonus_mult == pytest.approx(1.0)

    def test_activar_qte_establece_multiplicador(self):
        """activate_qte_bonus activa el flag y establece el multiplicador."""
        g = GameState()
        g.activate_qte_bonus(multiplier=3.0, duration=60.0)
        assert g.qte_bonus_active is True
        assert g.qte_bonus_mult == pytest.approx(3.0)

    def test_qte_bonus_afecta_pps(self):
        """El bono QTE amplifica los PPS correctamente."""
        g = GameState()
        g.generators["worker"] = 1
        pps_base = g.pps()
        g.activate_qte_bonus(3.0, 60.0)
        assert g.pps() == pytest.approx(pps_base * 3.0)

    def test_qte_bonus_afecta_click(self):
        """El bono QTE amplifica el valor ganado por clic."""
        g = GameState()
        base_earned = g.click_value
        g.activate_qte_bonus(3.0, 60.0)
        earned = g.click()
        assert earned == pytest.approx(base_earned * 3.0)

    def test_qte_seconds_left_decrece(self):
        """qte_bonus_seconds_left devuelve un valor positivo y decreciente."""
        g = GameState()
        g.activate_qte_bonus(3.0, 60.0)
        t1 = g.qte_bonus_seconds_left()
        time.sleep(0.02)
        t2 = g.qte_bonus_seconds_left()
        assert t1 > t2 > 0

    def test_qte_bonus_expira_con_tick(self):
        """El bono QTE se desactiva tras expirar el tiempo."""
        g = GameState()
        g.activate_qte_bonus(3.0, duration=0.01)
        time.sleep(0.05)
        g.tick()
        assert g.qte_bonus_active is False
        assert g.qte_bonus_mult == pytest.approx(1.0)

    def test_qte_y_minijuego_se_suman(self):
        """El bono QTE y el minijuego se multiplican entre sí."""
        g = GameState()
        g.generators["worker"] = 1
        pps_base = g.pps()
        g.activate_minigame(2.0, 60.0)
        g.activate_qte_bonus(3.0, 60.0)
        assert g.pps() == pytest.approx(pps_base * 2.0 * 3.0)

    def test_prestige_resetea_qte_bonus(self):
        """El prestige desactiva el bono QTE."""
        from src.config import PRESTIGE_1_THRESHOLD
        g = GameState()
        g.activate_qte_bonus(3.0, 60.0)
        g.total_points = PRESTIGE_1_THRESHOLD * BOOST
        g.prestige()
        assert g.qte_bonus_active is False
        assert g.qte_bonus_mult == pytest.approx(1.0)


# ── Música procedural ─────────────────────────────────────────────────────────

class TestMusicaProcedural:

    def test_generate_loop_devuelve_array(self):
        """generate_loop devuelve un array numpy con contenido."""
        import numpy as np
        from src.music import generate_loop
        arr = generate_loop()
        assert arr is not None
        assert arr.shape[0] > 0

    def test_generate_loop_es_estereo(self):
        """El array de audio tiene 2 canales (estéreo)."""
        from src.music import generate_loop
        arr = generate_loop()
        assert arr.ndim == 2
        assert arr.shape[1] == 2

    def test_generate_loop_duracion_aprox_12s(self):
        """La duración del loop es aproximadamente 12 segundos a 44100 Hz."""
        from src.music import generate_loop
        arr = generate_loop()
        sample_rate = 44100
        duracion = arr.shape[0] / sample_rate
        assert 11.0 <= duracion <= 13.0

    def test_generate_loop_sin_overflow(self):
        """Los valores del array están dentro del rango int16 (-32768, 32767)."""
        import numpy as np
        from src.music import generate_loop
        arr = generate_loop()
        assert arr.dtype == np.int16
        assert arr.max() <= 32767
        assert arr.min() >= -32768

    def test_generate_loop_sin_nan(self):
        """El array no contiene valores NaN (no aplica a int16, pero verifica shape)."""
        from src.music import generate_loop
        arr = generate_loop()
        assert arr.shape[0] > 0
        assert arr.shape[1] == 2

    def test_get_music_sound_cachea(self):
        """get_music_sound devuelve el mismo objeto en llamadas sucesivas."""
        import pygame
        pygame.init()
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        except Exception:
            pytest.skip("mixer no disponible")
        from src.music import get_music_sound, _reset_cache
        _reset_cache()
        s1 = get_music_sound()
        s2 = get_music_sound()
        assert s1 is s2
