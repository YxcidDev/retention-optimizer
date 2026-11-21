# Fitness Life Retention Optimizer

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PuLP](https://img.shields.io/badge/Optimization-PuLP-blue)](https://github.com/coin-or/pulp)
[![License](https://img.shields.io/badge/license-not%20specified-lightgrey)](#licencia)

Microservicio REST que asigna acciones de retención a usuarios agrupados por riesgo de cancelación. Formula un modelo de programación lineal entera para maximizar el beneficio neto esperado, sujeto al presupuesto y a los límites de cada acción.

## Características

- Optimiza la asignación de recordatorios, promociones e invitaciones a clases.
- Considera el número de usuarios candidatos y el valor esperado de retenerlos por segmento.
- Aplica límites de presupuesto, capacidad de acciones y cobertura mínima para usuarios de riesgo alto.
- Permite resolver el modelo con variables enteras o con una relajación continua.
- Informa el estado de la solución, el costo, las asignaciones, las restricciones y el valor objetivo relajado.
- Expone un endpoint de salud y documentación interactiva de la API.

## Tecnologías

- Python 3.10 o posterior.
- FastAPI y Pydantic 2.
- PuLP y el solucionador CBC.
- Uvicorn como servidor ASGI.

> **Compatibilidad de PuLP:** el código usa `PULP_CBC_CMD`. Instala una versión PuLP 3.x compatible con esa API. PuLP 4 eliminó `PULP_CBC_CMD`; para usar esa versión habría que adaptar la inicialización del solver a `COIN_CMD`. Consulta la [guía oficial de instalación de PuLP](https://github.com/coin-or/pulp/blob/master/README.rst) y la [guía de migración a PuLP 4](https://github.com/coin-or/pulp/blob/master/doc/source/guides/how_to_migrate_to_v4.rst).

## Requisitos previos

- Python 3.10 o posterior.
- `pip`.
- Un entorno virtual de Python recomendado para aislar dependencias.
- CBC disponible para PuLP. Verifica que la versión de PuLP instalada incluya o pueda localizar CBC.

## Instalación

1. Clona este repositorio y entra en su directorio:

   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd <DIRECTORIO_DEL_REPOSITORIO>