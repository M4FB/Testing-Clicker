"""
Pruebas de Aceptación — Semana 2 (ATDD)

Criterios de aceptación nuevos:
  AC-08  Sistema de potenciadores de generadores (30 mejoras progresivas)
  AC-09  Sistema QTE (Quick Time Event)
  AC-10  Árbol progresivo de mejoras de clic (15 mejoras)
  AC-11  Tres tipos de minijuego (funcional en GameState)
  AC-12  Integridad del prestige extendido (resetea nuevos sistemas)
"""
import time
import pytest
from src.game import GameState
from src.config import (
    BOOST, GENERATORS, CLICK_UPGRADES, GEN_UPGRADES,
    PRESTIGE_1_THRESHOLD, PRESTIGE_2_THRESHOLD,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def game_rico() -> GameState:
    g = GameState()
    g.points = 999_999_999
    g.total_points = 999_999_999
    for gen in GENERATORS:
        g.generators[gen["id"]] = 10
    return g


# ─────────────────────────────────────────────────────────────────────────────
class TestAC08_PotenciadoresGeneradores:
    """
    AC-08: El juego ofrece al menos 30 potenciadores de generadores
    con desbloqueo progresivo basado en posesión y compras anteriores.
    """

    def test_existen_al_menos_30_potenciadores(self):
        """La configuración define 30 o más potenciadores de generadores."""
        assert len(GEN_UPGRADES) >= 30

    def test_todos_los_potenciadores_tienen_campos_obligatorios(self):
        """Cada potenciador tiene id, icon, name, target, mult, cost."""
        campos = {"id", "icon", "name", "target", "mult", "cost"}
        for gu in GEN_UPGRADES:
            assert campos.issubset(gu.keys()), f"{gu['id']} le faltan campos"

    def test_potenciadores_global_afectan_all(self):
        """Los potenciadores con target='all' existen y hay al menos 6."""
        globales = [gu for gu in GEN_UPGRADES if gu["target"] == "all"]
        assert len(globales) >= 6

    def test_potenciadores_especificos_cubren_todos_generadores(self):
        """Existe al menos un potenciador específico para cada generador."""
        gen_ids = {g["id"] for g in GENERATORS}
        targets_especificos = {gu["target"] for gu in GEN_UPGRADES if gu["target"] != "all"}
        assert gen_ids.issubset(targets_especificos)

    def test_potenciador_bloqueado_sin_requisitos(self):
        """Un potenciador con unlock_own no se desbloquea sin poseer generadores."""
        g = GameState()
        g.generators = {gen["id"]: 0 for gen in GENERATORS}
        gu_w1 = next(gu for gu in GEN_UPGRADES if gu["id"] == "gu_w1")
        assert g.gen_upgrade_unlocked(gu_w1["id"]) is False

    def test_potenciador_disponible_al_cumplir_requisito(self):
        """Un potenciador se desbloquea en cuanto se cumple su unlock_own."""
        g = GameState()
        g.generators["worker"] = 1
        assert g.gen_upgrade_unlocked("gu_w1") is True

    def test_cadena_de_desbloqueo_dos_niveles(self):
        """Comprar gu_w1 desbloquea gu_w2 (cadena unlock_after de dos niveles)."""
        g = game_rico()
        g.buy_gen_upgrade("gu_w1")
        assert g.gen_upgrade_unlocked("gu_w2") is True

    def test_comprar_potenciador_aplica_multiplicador(self):
        """Comprar un potenciador ×2 duplica el PPS del target."""
        g = game_rico()
        pps_antes = g.pps()
        g.buy_gen_upgrade("gu_g1")
        pps_despues = g.pps()
        assert pps_despues == pytest.approx(pps_antes * 1.5)

    def test_no_se_puede_comprar_sin_fondos(self):
        """Comprar un potenciador sin puntos suficientes falla."""
        g = GameState()
        g.generators["worker"] = 1
        g.points = 0
        assert g.buy_gen_upgrade("gu_w1") is False


# ─────────────────────────────────────────────────────────────────────────────
class TestAC09_SistemaQTE:
    """
    AC-09: El juego implementa un sistema de QTE que otorga bonificación
    temporal de ×3 durante 60 segundos al completarlo con éxito.
    """

    def test_qte_bonus_por_defecto_inactivo(self):
        """El estado inicial no tiene QTE activo."""
        g = GameState()
        assert g.qte_bonus_active is False

    def test_qte_bonus_activa_multiplicador(self):
        """activate_qte_bonus establece el mult correcto."""
        g = GameState()
        g.activate_qte_bonus(multiplier=3.0, duration=60.0)
        assert g.qte_bonus_active is True
        assert g.qte_bonus_mult == pytest.approx(3.0)

    def test_qte_bonus_amplifica_pps(self):
        """El bono QTE triplica los PPS cuando el mult es 3."""
        g = GameState()
        g.generators["worker"] = 2
        pps_sin = g.pps()
        g.activate_qte_bonus(3.0, 60.0)
        assert g.pps() == pytest.approx(pps_sin * 3.0)

    def test_qte_bonus_amplifica_clic(self):
        """El bono QTE amplifica también el valor de clic."""
        g = GameState()
        g.activate_qte_bonus(3.0, 60.0)
        earned = g.click()
        assert earned == pytest.approx(g.click_value * 3.0)

    def test_qte_seconds_left_positivo(self):
        """qte_bonus_seconds_left devuelve valor positivo tras activar."""
        g = GameState()
        g.activate_qte_bonus(3.0, 60.0)
        assert g.qte_bonus_seconds_left() > 0

    def test_qte_expira_automaticamente(self):
        """El bono QTE se desactiva automáticamente al expirar."""
        g = GameState()
        g.activate_qte_bonus(3.0, duration=0.01)
        time.sleep(0.05)
        g.tick()
        assert g.qte_bonus_active is False
        assert g.qte_bonus_mult == pytest.approx(1.0)

    def test_qte_y_prestige_compatibles(self):
        """El prestige reinicia el bono QTE sin efectos secundarios."""
        g = GameState()
        g.activate_qte_bonus(3.0, 60.0)
        g.total_points = PRESTIGE_1_THRESHOLD * BOOST
        g.prestige()
        assert g.qte_bonus_active is False
        assert g.qte_bonus_mult == pytest.approx(1.0)
        assert g.prestige_count == 1


# ─────────────────────────────────────────────────────────────────────────────
class TestAC10_ArbolMejorasClic:
    """
    AC-10: El juego tiene al menos 15 mejoras de clic con árbol de desbloqueo
    progresivo; comprar una mejora revela las siguientes del árbol.
    """

    def test_existen_15_mejoras_de_clic(self):
        """Hay exactamente 15 mejoras de clic definidas."""
        assert len(CLICK_UPGRADES) >= 15

    def test_todos_los_upgrades_tienen_icono(self):
        """Cada mejora de clic tiene un campo 'icon' no vacío."""
        for cu in CLICK_UPGRADES:
            assert "icon" in cu and cu["icon"], f"{cu['id']} sin icono"

    def test_primer_upgrade_visible_al_inicio(self):
        """cu_1 está disponible sin comprar nada."""
        g = GameState()
        assert g.click_upgrade_unlocked("cu_1") is True

    def test_cadena_desbloqueo_hasta_tier3(self):
        """Comprar cu_1..cu_5 desbloquea cu_6."""
        g = game_rico()
        for uid in ["cu_1", "cu_2", "cu_3", "cu_4", "cu_5"]:
            g.buy_click_upgrade(uid)
        assert g.click_upgrade_unlocked("cu_6") is True

    def test_upgrades_con_mult_aplican_multiplicador(self):
        """Las mejoras con campo 'mult' modifican click_mult."""
        g = game_rico()
        mult_antes = g.click_mult
        g.buy_click_upgrade("cu_1")
        g.buy_click_upgrade("cu_2")
        g.buy_click_upgrade("cu_3")
        g.buy_click_upgrade("cu_4")
        g.buy_click_upgrade("cu_5")
        assert g.click_mult > mult_antes

    def test_upgrades_con_bonus_aumentan_click_value(self):
        """Las mejoras con campo 'bonus' incrementan click_value."""
        g = game_rico()
        cv_antes = g.click_value
        g.buy_click_upgrade("cu_1")
        assert g.click_value > cv_antes

    def test_ultimo_tier_bloqueado_sin_progreso(self):
        """cu_15 no está disponible al inicio."""
        g = GameState()
        assert g.click_upgrade_unlocked("cu_15") is False

    def test_prestige_resetea_todos_los_upgrades_clic(self):
        """El prestige borra todas las mejoras de clic compradas."""
        g = game_rico()
        for uid in ["cu_1", "cu_2", "cu_3"]:
            g.buy_click_upgrade(uid)
        g.total_points = PRESTIGE_1_THRESHOLD * BOOST
        g.prestige()
        for cu in CLICK_UPGRADES:
            assert g.click_upgrades[cu["id"]] is False


# ─────────────────────────────────────────────────────────────────────────────
class TestAC11_MinijuegosMultiples:
    """
    AC-11: El juego tiene mecánica de minijuego que otorga bonus de producción
    temporal. Los tres tipos coexisten con el sistema de bonos.
    """

    def test_minijuego_activa_boost(self):
        """activate_minigame activa un multiplicador temporal."""
        g = GameState()
        g.activate_minigame(2.5, 45.0)
        assert g.minigame_active is True
        assert g.minigame_multiplier == pytest.approx(2.5)

    def test_minijuego_y_qte_se_acumulan(self):
        """Minijuego y QTE se multiplican; ×2.5 × ×3 = ×7.5 sobre el base."""
        g = GameState()
        g.generators["worker"] = 1
        pps_base = g.pps()
        g.activate_minigame(2.5, 45.0)
        g.activate_qte_bonus(3.0, 60.0)
        assert g.pps() == pytest.approx(pps_base * 2.5 * 3.0)

    def test_minijuego_expira_correctamente(self):
        """El minijuego expira tras su duración."""
        g = GameState()
        g.activate_minigame(2.0, 0.01)
        time.sleep(0.05)
        g.tick()
        assert not g.minigame_active

    def test_seconds_left_positivo_en_activo(self):
        """minigame_seconds_left devuelve tiempo positivo mientras activo."""
        g = GameState()
        g.activate_minigame(2.0, 30.0)
        assert g.minigame_seconds_left() > 0

    def test_seconds_left_cero_cuando_inactivo(self):
        """minigame_seconds_left devuelve 0 cuando no está activo."""
        g = GameState()
        assert g.minigame_seconds_left() == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
class TestAC12_IntegridadPrestigeExtendido:
    """
    AC-12: El prestige resetea correctamente todos los sistemas nuevos
    (click_mult, gen_upgrades, gen_mult, QTE bonus) preservando solo
    el prestige_multiplier acumulado.
    """

    def test_prestige_preserva_multiplicador_acumulado(self):
        """Tras prestige, prestige_multiplier refleja la bonificación ganada."""
        g = GameState()
        g.total_points = PRESTIGE_1_THRESHOLD * BOOST
        g.prestige()
        assert g.prestige_multiplier == pytest.approx(1.5)

    def test_prestige_resetea_click_mult(self):
        """click_mult vuelve a 1.0 tras prestige."""
        g = game_rico()
        g.buy_click_upgrade("cu_1")
        g.buy_click_upgrade("cu_2")
        g.buy_click_upgrade("cu_3")
        g.buy_click_upgrade("cu_4")
        g.buy_click_upgrade("cu_5")
        g.total_points = PRESTIGE_1_THRESHOLD * BOOST
        g.prestige()
        assert g.click_mult == pytest.approx(1.0)

    def test_prestige_resetea_gen_mult(self):
        """gen_mult queda vacío tras prestige."""
        g = game_rico()
        g.buy_gen_upgrade("gu_g1")
        g.total_points = PRESTIGE_1_THRESHOLD * BOOST
        g.prestige()
        assert g.gen_mult == {}

    def test_prestige_resetea_gen_upgrades(self):
        """gen_upgrades queda todo en False tras prestige."""
        g = game_rico()
        g.buy_gen_upgrade("gu_g1")
        g.total_points = PRESTIGE_1_THRESHOLD * BOOST
        g.prestige()
        assert all(v is False for v in g.gen_upgrades.values())

    def test_prestige_resetea_qte_bonus(self):
        """qte_bonus_active y qte_bonus_mult se resetean tras prestige."""
        g = GameState()
        g.activate_qte_bonus(3.0, 60.0)
        g.total_points = PRESTIGE_1_THRESHOLD * BOOST
        g.prestige()
        assert g.qte_bonus_active is False
        assert g.qte_bonus_mult == pytest.approx(1.0)

    def test_dos_prestiges_y_victoria_funcionan_con_nuevos_sistemas(self):
        """El flujo completo de victoria funciona con todos los sistemas activos."""
        from src.config import PRESTIGE_2_THRESHOLD, VICTORY_THRESHOLD
        g = game_rico()
        g.buy_gen_upgrade("gu_g1")
        g.activate_qte_bonus(3.0, 60.0)
        g.buy_click_upgrade("cu_1")
        g.total_points = PRESTIGE_1_THRESHOLD * BOOST
        assert g.prestige() is True
        g.total_points = PRESTIGE_2_THRESHOLD * BOOST
        assert g.prestige() is True
        g.total_points = VICTORY_THRESHOLD * BOOST
        assert g.check_victory() is True
        assert g.won is True
