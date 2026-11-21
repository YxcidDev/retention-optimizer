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
   ```

2. Crea y activa un entorno virtual:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   En Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. Instala las dependencias:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install fastapi "uvicorn[standard]" "pulp<4"
   ```

4. Si el archivo de la aplicación se llama `main.py`, inicia el servicio en modo desarrollo:

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   Si el archivo tiene otro nombre, sustituye `main` por el nombre del módulo Python, sin la extensión `.py`. Por ejemplo, para `optimizer.py`, usa `uvicorn optimizer:app`.

El servicio no requiere variables de entorno para la configuración mostrada en el código. El puerto y la dirección de escucha se configuran mediante los argumentos de Uvicorn.

## Ejecución

Para iniciar el servicio localmente:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

- Comprobación de salud: [http://localhost:8000/health](http://localhost:8000/health)
- Documentación interactiva: [http://localhost:8000/docs](http://localhost:8000/docs)
- Esquema OpenAPI: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

En producción, ejecuta Uvicorn sin `--reload` y configura el proceso de acuerdo con el entorno de despliegue. Reemplaza `main` si el módulo tiene otro nombre.

## API

### `GET /health`

Comprueba que el servicio está disponible.

```bash
curl http://localhost:8000/health
```

Respuesta:

```json
{
  "status": "UP"
}
```

### `POST /optimize-retention`

Resuelve el modelo de optimización. Envía el cuerpo como JSON.

```bash
curl -X POST http://localhost:8000/optimize-retention \
  -H "Content-Type: application/json" \
  -d '{
    "n": [100, 80, 50],
    "v": [100000, 120000, 150000],
    "p": [
      [0.02, 0.05, 0.04],
      [0.05, 0.12, 0.10],
      [0.08, 0.20, 0.15]
    ],
    "c": [500, 2000, 3000],
    "budget": 100000,
    "classSlots": 10,
    "maxPromotions": 15,
    "maxReminders": 100,
    "minHighRiskCoverage": 0.8,
    "integer": true
  }'
```

#### Parámetros de la solicitud

| Campo                 | Tipo                    | Descripción                                                                                  |
| --------------------- | ----------------------- | -------------------------------------------------------------------------------------------- |
| `n`                   | Arreglo de 3 enteros    | Usuarios candidatos por segmento: bajo, medio y alto riesgo.                                |
| `v`                   | Arreglo de 3 números    | Valor esperado de retener un usuario por segmento, en COP.                                  |
| `p`                   | Matriz de 3 × 3 números | Aumento de probabilidad de retención por segmento y acción, entre `0` y `1`.                |
| `c`                   | Arreglo de 3 números    | Costo unitario de cada acción, en COP.                                                       |
| `budget`              | Número                  | Presupuesto total, en COP.                                                                   |
| `classSlots`          | Entero                  | Máximo de cupos disponibles para invitaciones a clases.                                      |
| `maxPromotions`       | Entero                  | Máximo de promociones autorizadas.                                                           |
| `maxReminders`        | Entero                  | Máximo de recordatorios permitidos.                                                          |
| `minHighRiskCoverage` | Número                  | Cobertura mínima requerida para el segmento de alto riesgo, entre `0` y `1`.                |
| `integer`             | Booleano                | `true` para asignaciones enteras; `false` para usar variables continuas. Por defecto es `true`. |

El orden de los segmentos es `LOW`, `MEDIUM`, `HIGH`. En la matriz `p` y el arreglo `c`, el orden de las acciones es `REMINDER`, `PROMOTION`, `CLASS_INVITE`.

#### Respuesta

La respuesta incluye:

- `status`: estado del solucionador, por ejemplo `Optimal` o `Infeasible`.
- `objectiveValue`: beneficio neto esperado de la asignación.
- `totalCost`: costo total de las acciones asignadas.
- `x`: cantidades asignadas por segmento y acción, en el mismo orden de la solicitud.
- `constraints`: uso, límite, holgura y precio sombra de las restricciones.
- `relaxedObjective`: valor objetivo al resolver la relajación continua, si se obtuvo.
- `messages`: mensajes informativos o de factibilidad.

Las solicitudes que no cumplen la validación del esquema reciben una respuesta HTTP `422`. Un modelo que no puede satisfacer las restricciones devuelve el estado `Infeasible` en el cuerpo de la respuesta.

## Modelo de optimización

El objetivo maximiza el beneficio neto esperado de las asignaciones:

```text
beneficio neto = suma de ((valor esperado de retención × aumento de probabilidad) − costo de acción)
```

El modelo limita la cantidad de usuarios atendidos por segmento, el presupuesto, los cupos de clase, las promociones y los recordatorios. También exige que la cobertura de usuarios de alto riesgo cumpla el mínimo solicitado. Cuando las variables son enteras, ese mínimo se redondea hacia arriba.

## Integración

La aplicación Fitness Life consume `POST /optimize-retention`. Configura en la aplicación cliente la URL completa del endpoint; por ejemplo:

```text
http://localhost:8000/optimize-retention
```

El valor `8000` corresponde al ejemplo local de Uvicorn. En otros entornos, usa el host y puerto publicados para este microservicio.
