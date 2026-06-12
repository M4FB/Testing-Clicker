"""
Pruebas BDD — Behaviour Driven Development (pre-release)
Carga los escenarios Gherkin desde tests/features/*.feature
Los step definitions están en tests/conftest.py
"""
from pytest_bdd import scenarios

# Cargar todos los escenarios de cada feature nueva del pre-release
scenarios("features/compra_multiple.feature")
scenarios("features/guardado.feature")
scenarios("features/minijuegos.feature")
scenarios("features/sonido.feature")
