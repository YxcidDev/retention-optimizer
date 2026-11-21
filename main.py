import math
from typing import Annotated, Dict, List, Optional, Tuple

import pulp
from fastapi import FastAPI
from pydantic import BaseModel, Field, model_validator

app = FastAPI(
    title="Fitness Life - Retention Optimizer API",
    description="Asignación óptima de acciones de retención (PLE con PuLP/CBC)",
    version="1.0.0",
)

SEGMENTS = ["LOW", "MEDIUM", "HIGH"]
ACTIONS = ["REMINDER", "PROMOTION", "CLASS_INVITE"]

NonNegInt = Annotated[int, Field(ge=0)]
NonNegFloat = Annotated[float, Field(ge=0)]
Probability = Annotated[float, Field(ge=0, le=1)]


class RetentionRequest(BaseModel):
    n: List[NonNegInt] = Field(min_length=3, max_length=3, description="N_i usuarios candidatos por segmento")
    v: List[NonNegFloat] = Field(min_length=3, max_length=3, description="v_i valor esperado de retener (COP)")
    p: List[List[Probability]] = Field(description="p_ij aumento de prob. de retención (3x3)")
    c: List[NonNegFloat] = Field(min_length=3, max_length=3, description="c_j costo unitario por acción (COP)")
    budget: NonNegFloat = Field(description="B presupuesto mensual (COP)")
    classSlots: NonNegInt = Field(description="S cupos libres en clases funcionales")
    maxPromotions: NonNegInt = Field(description="D máximo de promociones")
    maxReminders: NonNegInt = Field(description="M máximo de recordatorios")
    minHighRiskCoverage: Probability = Field(description="alpha cobertura mínima del riesgo alto")
    integer: bool = Field(default=True, description="True = variables enteras; False = relajación continua")

    @model_validator(mode="after")
    def check_matrix(self):
        if len(self.p) != 3 or any(len(row) != 3 for row in self.p):
            raise ValueError("p debe ser una matriz 3x3")
        return self


def required_high_risk(req: RetentionRequest, integer: bool) -> float:
    """Lado derecho de R8. Con variables enteras se redondea hacia arriba."""
    raw = round(req.minHighRiskCoverage * req.n[2], 6)
    return float(math.ceil(raw)) if integer else raw


def build_model(req: RetentionRequest, integer: bool) -> Tuple[pulp.LpProblem, Dict[Tuple[int, int], pulp.LpVariable]]:
    cat = pulp.LpInteger if integer else pulp.LpContinuous
    prob = pulp.LpProblem("RetentionAllocation", pulp.LpMaximize)

    x = {
        (i, j): pulp.LpVariable(f"x{i + 1}{j + 1}", lowBound=0, cat=cat)
        for i in range(3)
        for j in range(3)
    }

    prob += pulp.lpSum(
        (req.v[i] * req.p[i][j] - req.c[j]) * x[(i, j)] for i in range(3) for j in range(3)
    ), "BeneficioNetoEsperado"

    for i in range(3):
        prob += pulp.lpSum(x[(i, j)] for j in range(3)) <= req.n[i], f"R{i + 1}_Disponibilidad_{SEGMENTS[i]}"
 
    prob += pulp.lpSum(req.c[j] * x[(i, j)] for i in range(3) for j in range(3)) <= req.budget, "R4_Presupuesto"

    prob += pulp.lpSum(x[(i, 2)] for i in range(3)) <= req.classSlots, "R5_CuposClases"

    prob += pulp.lpSum(x[(i, 1)] for i in range(3)) <= req.maxPromotions, "R6_Promociones"
  
    prob += pulp.lpSum(x[(i, 0)] for i in range(3)) <= req.maxReminders, "R7_Recordatorios"
  
    prob += (
        pulp.lpSum(x[(2, j)] for j in range(3)) >= required_high_risk(req, integer),
        "R8_CoberturaRiesgoAlto",
    )
    return prob, x


def precheck_feasibility(req: RetentionRequest) -> List[str]:
    """
    R8 es la única restricción que fuerza actividad. El modelo es factible si y solo si
    se pueden cubrir ceil(alpha*N3) usuarios de riesgo alto con las capacidades de cada
    acción y a costo mínimo <= B (llenando primero la acción más barata).
    """
    messages: List[str] = []
    needed = int(required_high_risk(req, True))
    caps = [req.maxReminders, req.maxPromotions, req.classSlots]

    if needed > sum(caps):
        messages.append(
            f"R8 exige atender {needed} usuarios de riesgo alto, pero la capacidad total de acciones "
            f"(recordatorios + promociones + cupos) es {sum(caps)}."
        )
        return messages

    remaining = needed
    min_cost = 0.0
    for j in sorted(range(3), key=lambda k: req.c[k]):
        take = min(remaining, caps[j])
        min_cost += take * req.c[j]
        remaining -= take
        if remaining == 0:
            break

    if min_cost > req.budget + 1e-6:
        messages.append(
            f"El costo mínimo para cumplir R8 (atender {needed} usuarios de riesgo alto) es "
            f"{min_cost:,.0f} COP y el presupuesto B es {req.budget:,.0f} COP."
        )
    return messages


def constraint_report(req: RetentionRequest, xv: List[List[float]], integer: bool,
                      shadow: Dict[str, float]) -> List[dict]:
    row = lambda i: sum(xv[i])
    col = lambda j: sum(xv[i][j] for i in range(3))
    cost = sum(req.c[j] * xv[i][j] for i in range(3) for j in range(3))

    items = [
        (f"R{i + 1}_Disponibilidad_{SEGMENTS[i]}", f"R{i + 1}", f"Disponibilidad segmento {SEGMENTS[i]}",
         row(i), float(req.n[i]), "<=") for i in range(3)
    ] + [
        ("R4_Presupuesto", "R4", "Presupuesto (COP)", cost, float(req.budget), "<="),
        ("R5_CuposClases", "R5", "Cupos de clases grupales", col(2), float(req.classSlots), "<="),
        ("R6_Promociones", "R6", "Promociones autorizadas", col(1), float(req.maxPromotions), "<="),
        ("R7_Recordatorios", "R7", "Capacidad de recordatorios", col(0), float(req.maxReminders), "<="),
        ("R8_CoberturaRiesgoAlto", "R8", "Cobertura mínima riesgo alto", row(2),
         required_high_risk(req, integer), ">="),
    ]

    report = []
    for key, code, name, used, limit, sense in items:
        slack = limit - used if sense == "<=" else used - limit
        report.append({
            "code": code,
            "name": name,
            "sense": sense,
            "used": round(used, 4),
            "limit": round(limit, 4),
            "slack": round(slack, 4),
            "binding": abs(slack) < 1e-6,
            "shadowPrice": round(shadow.get(key, 0.0), 6),
        })
    return report


def solve(prob: pulp.LpProblem) -> str:
    prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=20))
    return pulp.LpStatus[prob.status]


@app.get("/health")
def health():
    return {"status": "UP"}


@app.post("/optimize-retention")
def optimize_retention(req: RetentionRequest):
    pre = precheck_feasibility(req)
    if pre:
        return {
            "status": "Infeasible",
            "objectiveValue": 0.0,
            "totalCost": 0.0,
            "x": [[0, 0, 0] for _ in range(3)],
            "constraints": [],
            "relaxedObjective": None,
            "messages": pre + ["Aumente B, S, D o M, o reduzca alpha (flexibilización de parámetros)."],
        }

    prob, x = build_model(req, req.integer)
    status = solve(prob)

    if status != "Optimal":
        return {
            "status": status,
            "objectiveValue": 0.0,
            "totalCost": 0.0,
            "x": [[0, 0, 0] for _ in range(3)],
            "constraints": [],
            "relaxedObjective": None,
            "messages": [f"CBC terminó con estado {status}."],
        }

    def val(i, j):
        v = pulp.value(x[(i, j)]) or 0.0
        return int(round(v)) if req.integer else round(v, 4)

    xv = [[val(i, j) for j in range(3)] for i in range(3)]
    objective = float(pulp.value(prob.objective) or 0.0)
    total_cost = sum(req.c[j] * xv[i][j] for i in range(3) for j in range(3))

    relaxed_obj: Optional[float] = None
    shadow: Dict[str, float] = {}
    relaxed, _ = build_model(req, False)
    if solve(relaxed) == "Optimal":
        relaxed_obj = float(pulp.value(relaxed.objective) or 0.0)
        shadow = {name: (c.pi or 0.0) for name, c in relaxed.constraints.items()}

    messages: List[str] = []
    if all(xv[i][j] == 0 for i in range(3) for j in range(3)):
        messages.append("Ninguna acción tiene contribución neta positiva con los parámetros actuales.")

    return {
        "status": status,
        "objectiveValue": round(objective, 2),
        "totalCost": round(total_cost, 2),
        "x": xv,
        "constraints": constraint_report(req, xv, req.integer, shadow),
        "relaxedObjective": None if relaxed_obj is None else round(relaxed_obj, 2),
        "messages": messages,
    }