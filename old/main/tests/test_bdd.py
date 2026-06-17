"""
Pruebas BDD — Behaviour Driven Development
Carga los escenarios Gherkin desde tests/features/*.feature
Los step definitions están en tests/conftest.py
"""
from pytest_bdd import scenarios

# Cargar todos los escenarios de cada feature
scenarios("features/mecanica_clic.feature")
scenarios("features/generadores.feature")
scenarios("features/prestige.feature")
scenarios("features/victoria.feature")
