"""
tests/test_performance.py
=========================
Tests de rendimiento para validar los requisitos no funcionales del TFG:

  RNF-01 - El gemelo digital (Unity WebGL) debe reflejar los cambios de
            inventario en tiempo real, con un retardo no superior a 2 segundos
            desde que la operacion queda registrada en el backend.

  RNF-02 - El tiempo de respuesta del backend para operaciones estandar de
            consulta o actualizacion no debe superar los 2 segundos bajo
            condiciones normales de uso.

Metodologia:
  - Se ejecuta cada operacion RUNS veces con el cliente de pruebas ASGI
    (httpx.AsyncClient + ASGITransport) usando la misma infraestructura
    de fixtures que el resto de la suite (SQLite en memoria, JWT real).
  - Se reportan media, minimo y maximo en milisegundos.
  - Se valida que la MEDIA no supere THRESHOLD_MS.
  - Para RNF-01, se intercepta websocket_service.broadcast_movement_created
    y se mide el tiempo desde el inicio del POST hasta que el broadcast es
    disparado. En produccion ese instante precede la propagacion WebSocket
    al cliente Unity en < 1 ms (red de area local).

Ejecucion:
    pytest -m performance -v -s --override-ini="addopts="
"""

import statistics
import time
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.models.models import (
    InventoryItem,
    Location,
    Task,
    TaskStatus,
    TaskType,
)

# ---------------------------------------------------------------------------
# Configuracion global
# ---------------------------------------------------------------------------

THRESHOLD_MS: int = 2_000   # Limite en ms para RNF-01 y RNF-02
RUNS: int = 5               # Repeticiones por operacion medida

# Almacen de resultados a nivel de modulo -> tabla resumen final
_perf_results: dict[str, dict] = {}

# Todos los tests de este modulo llevan la marca 'performance'
pytestmark = pytest.mark.performance


# ---------------------------------------------------------------------------
# Helpers compartidos
# ---------------------------------------------------------------------------

def _auth(token: str) -> dict:
    """Devuelve la cabecera Authorization con el token JWT dado."""
    return {"Authorization": f"Bearer {token}"}


def _record_and_assert(
    label: str,
    times_ms: list[float],
    threshold: int = THRESHOLD_MS,
) -> tuple[float, float, float]:
    """
    Calcula metricas, las almacena en _perf_results, imprime el resultado
    individual y afirma que la media no supera el umbral.

    El registro en _perf_results ocurre ANTES de la asercion, de modo que
    la tabla resumen siempre incluye los datos aunque el test falle.
    """
    mean = statistics.mean(times_ms)
    max_ = max(times_ms)
    min_ = min(times_ms)
    ok   = mean < threshold

    _perf_results[label] = {
        "mean": mean,
        "max":  max_,
        "min":  min_,
        "ok":   ok,
        "runs": len(times_ms),
    }

    sep = "-" * 64
    verdict = "CUMPLE RNF" if ok else "NO CUMPLE RNF"
    print(f"\n{sep}")
    print(f"  {label}")
    print(f"  Ejecuciones : {len(times_ms)}")
    print(f"  Media       : {mean:>9.2f} ms")
    print(f"  Minimo      : {min_:>9.2f} ms")
    print(f"  Maximo      : {max_:>9.2f} ms")
    print(f"  Umbral RNF  : {threshold:>9} ms  |  {verdict}")
    print(sep)

    assert ok, (
        f"[RNF INCUMPLIDO] '{label}': "
        f"media {mean:.2f} ms > umbral {threshold} ms"
    )
    return mean, max_, min_


async def _seed_locations(
    db_session,
    level_id: uuid.UUID,
    count: int,
    offset: int = 300,
) -> list:
    """
    Inserta `count` ubicaciones nuevas en el nivel indicado y las persiste.
    Se usan numeros de posicion a partir de `offset` para evitar conflictos
    con las ubicaciones del fixture base_data (posiciones 1 y 2).
    """
    locs = [
        Location(
            id=uuid.uuid4(),
            level_id=level_id,
            position_number=offset + i,
        )
        for i in range(count)
    ]
    for loc in locs:
        db_session.add(loc)
    await db_session.commit()
    return locs


# ---------------------------------------------------------------------------
# RNF-02 - Tiempo de respuesta del backend
# ---------------------------------------------------------------------------

class TestRNF02ResponseTime:
    """
    RNF-02: El tiempo de respuesta del backend para operaciones estandar
    no debe superar los 2 segundos bajo condiciones normales de uso.

    Se prueban los cinco endpoints mas criticos del sistema, cubriendo
    lectura, escritura y operaciones de agregacion.
    """

    # -- POST /auth/login -----------------------------------------------------

    async def test_perf_login(self, client, base_data):
        """
        POST /auth/login - autenticacion con credenciales validas.

        Incluye hash bcrypt (verify_password) y firma JWT (create_access_token).
        Es el endpoint de mayor impacto en la percepcion inicial del usuario.
        """
        times_ms: list[float] = []

        for _ in range(RUNS):
            t0 = time.perf_counter()
            r  = await client.post(
                "/auth/login",
                data={"username": "admin@test.com", "password": "admin123"},
            )
            times_ms.append((time.perf_counter() - t0) * 1_000)
            assert r.status_code == 200, f"Login devolvio {r.status_code}"

        _record_and_assert("POST /auth/login", times_ms)

    # -- GET /warehouses/{id}/full --------------------------------------------

    async def test_perf_warehouse_full(
        self, client, base_data, admin_token, db_session
    ):
        """
        GET /warehouses/{id}/full - vista completa del almacen usada por el
        gemelo digital Unity al inicializar la escena.

        La consulta recorre Almacen -> Estante -> Nivel -> Ubicacion ->
        Inventario -> Tareas activas: es la mas pesada de las lecturas.
        Se pre-carga inventario en ambas ubicaciones para que la JOIN sea real.
        """
        db_session.add(InventoryItem(
            id=uuid.uuid4(),
            location_id=base_data["location1"].id,
            product_id=base_data["product1"].id,
            quantity=4,
        ))
        db_session.add(InventoryItem(
            id=uuid.uuid4(),
            location_id=base_data["location2"].id,
            product_id=base_data["product2"].id,
            quantity=7,
        ))
        await db_session.commit()

        wid      = str(base_data["warehouse"].id)
        times_ms: list[float] = []

        for _ in range(RUNS):
            t0 = time.perf_counter()
            r  = await client.get(
                f"/warehouses/{wid}/full",
                headers=_auth(admin_token),
            )
            times_ms.append((time.perf_counter() - t0) * 1_000)
            assert r.status_code == 200, f"warehouse/full devolvio {r.status_code}"

        _record_and_assert("GET /warehouses/{id}/full", times_ms)

    # -- POST /movements -------------------------------------------------------

    async def test_perf_post_movements(
        self, client, base_data, admin_token, db_session
    ):
        """
        POST /movements (entrada) - operacion mas critica del sistema.

        Involucra: validacion Pydantic -> consulta de inventario en BD ->
        escritura de InventoryItem -> escritura de Movement -> broadcast WS.
        Se crea una ubicacion nueva por iteracion para evitar conflictos
        de ocupacion entre ejecuciones.
        """
        locs    = await _seed_locations(db_session, base_data["level"].id, RUNS, offset=300)
        product = base_data["product1"]
        times_ms: list[float] = []

        for loc in locs:
            payload = {
                "task_id":                 str(uuid.uuid4()),
                "type":                    "entrada",
                "product_id":              str(product.id),
                "destination_location_id": str(loc.id),
                "quantity":                1,
            }
            with patch("app.api.movements.websocket_service") as mock_ws:
                mock_ws.broadcast_movement_created = AsyncMock()
                t0 = time.perf_counter()
                r  = await client.post(
                    "/movements",
                    headers=_auth(admin_token),
                    json=payload,
                )
                times_ms.append((time.perf_counter() - t0) * 1_000)
            assert r.status_code == 201, (
                f"POST /movements devolvio {r.status_code}: {r.text}"
            )

        _record_and_assert("POST /movements (entrada)", times_ms)

    # -- POST /tasks -----------------------------------------------------------

    async def test_perf_post_tasks(
        self, client, base_data, admin_token, db_session
    ):
        """
        POST /tasks (entrada) - creacion de tarea con validacion completa.

        Involucra: verificacion de pertenencia del trabajador a la empresa ->
        comprobacion de ocupacion del destino -> chequeo de conflictos de
        tareas activas -> INSERT de Task -> broadcast WS.
        """
        locs    = await _seed_locations(db_session, base_data["level"].id, RUNS, offset=400)
        worker  = base_data["worker"]
        product = base_data["product1"]
        times_ms: list[float] = []

        for loc in locs:
            payload = {
                "assigned_to":             str(worker.id),
                "type":                    "entrada",
                "destination_location_id": str(loc.id),
                "product_id":              str(product.id),
                "quantity":                1,
            }
            with patch("app.api.tasks.websocket_service") as mock_ws:
                mock_ws.broadcast_task_assigned = AsyncMock()
                t0 = time.perf_counter()
                r  = await client.post(
                    "/tasks",
                    headers=_auth(admin_token),
                    json=payload,
                )
                times_ms.append((time.perf_counter() - t0) * 1_000)
            assert r.status_code == 201, (
                f"POST /tasks devolvio {r.status_code}: {r.text}"
            )

        _record_and_assert("POST /tasks (entrada)", times_ms)

    # -- GET /tasks/stats ------------------------------------------------------

    async def test_perf_get_tasks_stats(
        self, client, base_data, admin_token, db_session
    ):
        """
        GET /tasks/stats - consulta de agregacion estadistica multi-tabla.

        Agrupa tareas por trabajador calculando tasas de completitud,
        movimientos totales y el dia de mayor actividad. Es la consulta
        de mayor complejidad de la capa de analisis del sistema.
        Se insertan 10 tareas (5 completadas / 5 pendientes) para que
        la agregacion sea representativa de un uso real.
        """
        admin  = base_data["admin"]
        worker = base_data["worker"]

        for i in range(10):
            status = TaskStatus.completada if i % 2 == 0 else TaskStatus.pendiente
            db_session.add(Task(
                id=uuid.uuid4(),
                company_id=admin.company_id,
                created_by=admin.id,
                assigned_to=worker.id,
                type=TaskType.entrada,
                status=status,
                # UUID sintetico como destino: SQLite no valida FK por defecto
                destination_location_id=uuid.uuid4(),
                completed_at=datetime.utcnow() if status == TaskStatus.completada else None,
            ))
        await db_session.commit()

        times_ms: list[float] = []
        for _ in range(RUNS):
            t0 = time.perf_counter()
            r  = await client.get("/tasks/stats", headers=_auth(admin_token))
            times_ms.append((time.perf_counter() - t0) * 1_000)
            assert r.status_code == 200, f"GET /tasks/stats devolvio {r.status_code}"

        _record_and_assert("GET /tasks/stats (agregacion)", times_ms)


# ---------------------------------------------------------------------------
# RNF-01 - Latencia del gemelo digital (broadcast WebSocket)
# ---------------------------------------------------------------------------

class TestRNF01WebSocketLatency:
    """
    RNF-01: El gemelo digital debe reflejar los cambios de inventario en
    tiempo real, con un retardo no superior a 2 segundos desde que la
    operacion queda registrada en el backend.

    Metodologia de medicion:
      t_inicio   -> inicio del POST /movements (o /tasks)
      t_broadcast -> instante en que websocket_service.broadcast_*
                     es invocado (capturado mediante AsyncMock con side_effect)
      latencia   = t_broadcast - t_inicio

    El broadcast ocurre de forma inline dentro del handler, antes de devolver
    la respuesta HTTP. En produccion, la propagacion posterior por TCP/WebSocket
    a los clientes Unity en la misma red local aniade < 1 ms adicional.
    """

    async def test_perf_ws_movement_broadcast_latency(
        self, client, base_data, admin_token, db_session
    ):
        """
        RNF-01: latencia desde POST /movements hasta disparo del broadcast WS.
        Mide el tiempo que tarda el backend en emitir el evento una vez recibida la peticion HTTP de registro de movimiento.
        """
        locs    = await _seed_locations(db_session, base_data["level"].id, RUNS, offset=500)
        product = base_data["product1"]
        latencies_ms: list[float] = []

        for loc in locs:
            capture: dict = {"ts": None}

            async def _capture_broadcast(*args, **kwargs):
                capture["ts"] = time.perf_counter()

            payload = {
                "task_id":                 str(uuid.uuid4()),
                "type":                    "entrada",
                "product_id":              str(product.id),
                "destination_location_id": str(loc.id),
                "quantity":                1,
            }
            with patch("app.api.movements.websocket_service") as mock_ws:
                mock_ws.broadcast_movement_created = AsyncMock(
                    side_effect=_capture_broadcast
                )
                t_inicio = time.perf_counter()
                r = await client.post(
                    "/movements",
                    headers=_auth(admin_token),
                    json=payload,
                )

            assert r.status_code == 201, (
                f"POST /movements devolvio {r.status_code}: {r.text}"
            )
            assert capture["ts"] is not None, (
                "broadcast_movement_created no fue invocado durante la peticion"
            )
            latency_ms = (capture["ts"] - t_inicio) * 1_000
            latencies_ms.append(latency_ms)

        _record_and_assert(
            "RNF-01 Latencia WS (POST /movements -> broadcast)",
            latencies_ms,
        )

    async def test_perf_ws_task_broadcast_latency(
        self, client, base_data, admin_token, db_session
    ):
        """
        RNF-01: latencia desde POST /tasks hasta disparo del broadcast WS.
        Complementa la medicion anterior: la asignacion de tareas tambien
        actualiza el gemelo digital via el evento 'task_assigned'.
        """
        locs    = await _seed_locations(db_session, base_data["level"].id, RUNS, offset=600)
        worker  = base_data["worker"]
        product = base_data["product1"]
        latencies_ms: list[float] = []

        for loc in locs:
            capture: dict = {"ts": None}

            async def _capture_task_broadcast(*args, **kwargs):
                capture["ts"] = time.perf_counter()

            payload = {
                "assigned_to":             str(worker.id),
                "type":                    "entrada",
                "destination_location_id": str(loc.id),
                "product_id":              str(product.id),
                "quantity":                1,
            }

            with patch("app.api.tasks.websocket_service") as mock_ws:
                mock_ws.broadcast_task_assigned = AsyncMock(
                    side_effect=_capture_task_broadcast
                )
                t_inicio = time.perf_counter()
                r = await client.post(
                    "/tasks",
                    headers=_auth(admin_token),
                    json=payload,
                )

            assert r.status_code == 201, (
                f"POST /tasks devolvio {r.status_code}: {r.text}"
            )
            assert capture["ts"] is not None, (
                "broadcast_task_assigned no fue invocado durante la peticion"
            )

            latency_ms = (capture["ts"] - t_inicio) * 1_000
            latencies_ms.append(latency_ms)

        _record_and_assert(
            "RNF-01 Latencia WS (POST /tasks -> broadcast)",
            latencies_ms,
        )


# ---------------------------------------------------------------------------
# Tabla resumen final
# ---------------------------------------------------------------------------

def test_performance_summary():
    """
    Imprime la tabla resumen con todos los resultados de rendimiento.

    Al estar definida despues de las clases, pytest la ejecuta en ultimo
    lugar y _perf_results ya contiene los datos de todas las operaciones
    medidas anteriormente.
    """
    if not _perf_results:
        pytest.skip(
            "Sin datos de rendimiento. "
            'Ejecuta: pytest -m performance -v -s --override-ini="addopts="'
        )

    col_label = 52
    col_val   =  9
    total_w   = col_label + col_val * 3 + 14

    border = "=" * total_w
    thin   = "-" * total_w

    print(f"\n\n{border}")
    print("  TABLA RESUMEN - Validacion de Requisitos No Funcionales")
    print(
        f"  Umbral RNF-01 / RNF-02 : {THRESHOLD_MS} ms  |  "
        f"Ejecuciones por operacion: {RUNS}"
    )
    print(border)
    print(
        f"  {'Operacion':<{col_label}}"
        f"{'Media':>{col_val}}"
        f"{'Max':>{col_val}}"
        f"{'Min':>{col_val}}"
        f"  {'Cumple RNF?'}"
    )
    print(f"  {thin}")

    all_pass = True
    for label, data in _perf_results.items():
        ok_str = "[SI]" if data["ok"] else "[NO]"
        if not data["ok"]:
            all_pass = False
        print(
            f"  {label:<{col_label}}"
            f"{data['mean']:>{col_val - 2}.1f} ms"
            f"{data['max']:>{col_val - 2}.1f} ms"
            f"{data['min']:>{col_val - 2}.1f} ms"
            f"  {ok_str}"
        )

    print(border)
    result_str = "TODOS LOS RNF CUMPLIDOS" if all_pass else "ALGUN RNF INCUMPLIDO"
    print(f"  Resultado global: {result_str}")
    print(border + "\n")
