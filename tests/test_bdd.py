"""Pruebas BDD (Behaviour Driven Development) — pytest-bdd.
Carga los escenarios Gherkin de tests/features/*.feature; los step
"""
from pytest_bdd import scenarios

scenarios("features/mecanica_clic.feature")
scenarios("features/generadores.feature")
scenarios("features/prestige.feature")
scenarios("features/victoria.feature")
scenarios("features/guardado.feature")
scenarios("features/audio.feature")
scenarios("features/new_features.feature")
