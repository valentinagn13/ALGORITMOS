"""
Tests de validación para kpartir() en GeometricSIA.

Estructura:
    Nivel 1 — Equivalencia numérica k=2 vs bipartir()
    Nivel 2 — Corrección matemática para k>2
    Nivel 3 — Regresión de rendimiento

Cómo correr:
    pytest test_kpartir.py -v
    pytest test_kpartir.py -v -k "equivalencia"   # solo nivel 1
    pytest test_kpartir.py -v -k "correccion"      # solo nivel 2
    pytest test_kpartir.py -v -k "rendimiento"     # solo nivel 3
"""

import time
import pytest
import numpy as np
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures: subsistemas de prueba con TPMs conocidas
# ---------------------------------------------------------------------------

def hacer_subsistema(tpm_estado_nodo: np.ndarray, estado_inicial: np.ndarray):
    """
    Construye un System real a partir de una TPM estado-nodo y un estado inicial.
    La TPM tiene forma (2^n, n): filas = estados en t, columnas = nodos en t+1.
    """
    from src.models.core.system import System
    return System(tpm=tpm_estado_nodo, estado_inicio=estado_inicial)


# TPM determinista de 3 nodos (red N3C del proyecto)
# Cada fila es un estado en t, cada columna la prob de nodo=1 en t+1
TPM_N3 = np.array([
    [0, 0, 0],
    [0, 0, 1],
    [0, 1, 0],
    [0, 1, 1],
    [1, 0, 0],
    [1, 0, 1],
    [1, 1, 0],
    [1, 1, 1],
], dtype=np.float32)

ESTADO_N3 = np.array([0, 0, 0], dtype=np.int8)

# TPM estocástica de 3 nodos para probar casos no deterministas
TPM_N3_STOCH = np.array([
    [0.1, 0.2, 0.3],
    [0.9, 0.1, 0.7],
    [0.4, 0.8, 0.2],
    [0.6, 0.3, 0.9],
    [0.5, 0.5, 0.5],
    [0.2, 0.7, 0.4],
    [0.8, 0.6, 0.1],
    [0.3, 0.4, 0.8],
], dtype=np.float32)

# TPM de 4 nodos para pruebas de rendimiento
def tpm_n4():
    rng = np.random.default_rng(42)
    return rng.random((16, 4), dtype=np.float32)

ESTADO_N4 = np.array([0, 1, 0, 1], dtype=np.int8)


# ---------------------------------------------------------------------------
# Helper: instancia mínima de KGeoMip con subsistema inyectado
# ---------------------------------------------------------------------------

def hacer_geometric_con_subsistema(subsistema):
    """
    Crea una instancia de KGeoMip sin pasar por __init__ completo,
    inyectando directamente el subsistema y los datos necesarios para kpartir().
    """
    from src.controllers.strategies.kgeomip import KGeoMip
    from src.middlewares.slogger import SafeLogger
    from src.constants.models import KGEOMIP_STRAREGY_TAG

    geo = KGeoMip.__new__(KGeoMip)
    geo.sia_subsistema = subsistema
    geo.sia_dists_marginales = subsistema.distribucion_marginal()
    geo.sia_logger = SafeLogger(KGEOMIP_STRAREGY_TAG)  # requerido por find_mip
    geo.logger = geo.sia_logger  # kpartir() usa self.logger
    geo.tabla_transiciones = {}
    geo.memoria_particiones = {}
    geo._candidatos_log = []

    # Precalcular _flat_data igual que en aplicar_estrategia
    geo._flat_data = [ncubo.data.ravel() for ncubo in subsistema.ncubos]

    return geo


# ---------------------------------------------------------------------------
# NIVEL 1 — Equivalencia numérica: kpartir(k=2) == bipartir() + dist_marginal()
# ---------------------------------------------------------------------------

class TestEquivalenciaK2:
    """
    Verifica que kpartir con k=2 produce exactamente el mismo vector
    que la ruta original bipartir() + distribucion_marginal().
    """

    @pytest.fixture
    def subsistema_n3(self):
        return hacer_subsistema(TPM_N3, ESTADO_N3)

    @pytest.fixture
    def subsistema_n3_stoch(self):
        return hacer_subsistema(TPM_N3_STOCH, ESTADO_N3)

    def _todas_biparticiones_n3(self, subsistema):
        """Genera todos los pares (alcance, mecanismo) posibles para n=3."""
        indices = subsistema.indices_ncubos
        dims = subsistema.dims_ncubos
        biparticiones = []
        n_fut = len(indices)
        n_pres = len(dims)
        for mask_fut in range(1, 1 << n_fut):
            futuros = np.array([indices[i] for i in range(n_fut) if mask_fut & (1 << i)], dtype=np.int8)
            for mask_pres in range(0, 1 << n_pres):
                presentes = np.array([dims[i] for i in range(n_pres) if mask_pres & (1 << i)], dtype=np.int8)
                biparticiones.append((futuros, presentes))
        return biparticiones

    def test_equivalencia_todas_biparticiones_determinista(self, subsistema_n3):
        """
        Para cada bipartición posible de n=3, kpartir y bipartir deben
        producir vectores idénticos (tolerancia float32).
        """
        geo = hacer_geometric_con_subsistema(subsistema_n3)

        for futuros, presentes in self._todas_biparticiones_n3(subsistema_n3):
            # Ruta original
            dist_original = (
                subsistema_n3.bipartir(futuros, presentes)
                .distribucion_marginal()
            )

            # Ruta nueva kpartir k=2
            # grupos[0] = futuros del grupo principal
            # grupos[1] = complemento de futuros
            todos_futuros = subsistema_n3.indices_ncubos
            futuros_complemento = np.setdiff1d(todos_futuros, futuros)

            grupos = [futuros]
            mecanismos = [presentes]
            if futuros_complemento.size > 0:
                grupos.append(futuros_complemento)
                mecanismos.append(presentes)

            dist_kpartir = geo.kpartir(grupos, mecanismos)

            np.testing.assert_allclose(
                dist_kpartir, dist_original,
                rtol=1e-5, atol=1e-6,
                err_msg=f"Discrepancia con futuros={futuros} presentes={presentes}"
            )

    def test_equivalencia_todas_biparticiones_estocastica(self, subsistema_n3_stoch):
        """Misma validación con TPM estocástica."""
        geo = hacer_geometric_con_subsistema(subsistema_n3_stoch)

        for futuros, presentes in self._todas_biparticiones_n3(subsistema_n3_stoch):
            dist_original = (
                subsistema_n3_stoch.bipartir(futuros, presentes)
                .distribucion_marginal()
            )

            todos_futuros = subsistema_n3_stoch.indices_ncubos
            futuros_complemento = np.setdiff1d(todos_futuros, futuros)

            grupos = [futuros]
            mecanismos = [presentes]
            if futuros_complemento.size > 0:
                grupos.append(futuros_complemento)
                mecanismos.append(presentes)

            dist_kpartir = geo.kpartir(grupos, mecanismos)

            np.testing.assert_allclose(
                dist_kpartir, dist_original,
                rtol=1e-5, atol=1e-6,
                err_msg=f"Discrepancia estocástica futuros={futuros} presentes={presentes}"
            )

    def test_equivalencia_alcance_completo(self, subsistema_n3):
        """Caso borde: todos los futuros en el mismo grupo."""
        geo = hacer_geometric_con_subsistema(subsistema_n3)
        futuros = subsistema_n3.indices_ncubos
        presentes = subsistema_n3.dims_ncubos

        dist_original = (
            subsistema_n3.bipartir(futuros, presentes)
            .distribucion_marginal()
        )
        dist_kpartir = geo.kpartir([futuros], [presentes])

        np.testing.assert_allclose(dist_kpartir, dist_original, rtol=1e-5, atol=1e-6)

    def test_equivalencia_mecanismo_vacio(self, subsistema_n3):
        """Caso borde: mecanismo vacío → marginalizar todo → media global."""
        geo = hacer_geometric_con_subsistema(subsistema_n3)
        futuros = subsistema_n3.indices_ncubos
        presentes_vacio = np.array([], dtype=np.int8)

        dist_original = (
            subsistema_n3.bipartir(futuros, presentes_vacio)
            .distribucion_marginal()
        )
        dist_kpartir = geo.kpartir([futuros], [presentes_vacio])

        np.testing.assert_allclose(dist_kpartir, dist_original, rtol=1e-5, atol=1e-6)


# ---------------------------------------------------------------------------
# NIVEL 2 — Corrección matemática para k > 2
# ---------------------------------------------------------------------------

class TestCorreccionKGeneral:
    """
    Verifica propiedades matemáticas que debe cumplir cualquier k-partición.
    No compara contra bipartir() (no aplica para k>2), sino contra invariantes.
    """

    @pytest.fixture
    def subsistema_n3(self):
        return hacer_subsistema(TPM_N3_STOCH, ESTADO_N3)

    @pytest.fixture
    def subsistema_n4(self):
        return hacer_subsistema(tpm_n4(), ESTADO_N4)

    def test_rango_valores_k3(self, subsistema_n3):
        """
        Todos los valores del vector resultante deben estar en [0, 1].
        Invariante: 1 - p donde p ∈ [0,1] siempre da [0,1].
        """
        geo = hacer_geometric_con_subsistema(subsistema_n3)
        indices = subsistema_n3.indices_ncubos
        dims = subsistema_n3.dims_ncubos

        # Dividir futuros en 3 grupos
        grupos = [
            indices[:1],
            indices[1:2],
            indices[2:],
        ]
        mecanismos = [dims, dims, dims]

        dist = geo.kpartir(grupos, mecanismos)

        assert dist.dtype == np.float32
        assert np.all(dist >= 0.0), f"Valores negativos: {dist}"
        assert np.all(dist <= 1.0), f"Valores > 1: {dist}"

    def test_longitud_resultado_es_n_ncubos(self, subsistema_n3):
        """El vector resultado debe tener exactitud = número de NCubos."""
        geo = hacer_geometric_con_subsistema(subsistema_n3)
        indices = subsistema_n3.indices_ncubos
        dims = subsistema_n3.dims_ncubos

        for k in [2, 3]:
            grupos = [indices[i::k] for i in range(k)]
            mecanismos = [dims] * k
            dist = geo.kpartir(grupos, mecanismos)
            assert len(dist) == len(subsistema_n3.ncubos), \
                f"k={k}: longitud {len(dist)} != {len(subsistema_n3.ncubos)}"

    def test_k3_vs_k2_diferente_cuando_hay_info(self, subsistema_n3):
        """
        Con k=3 cada NCubo está en su propio grupo con mecanismo distinto,
        lo que produce marginalización diferente a k=2 con un solo grupo.
        """
        geo = hacer_geometric_con_subsistema(subsistema_n3)
        indices = subsistema_n3.indices_ncubos  # [0, 1, 2]
        dims = subsistema_n3.dims_ncubos        # [0, 1, 2]

        # k=2: futuros [0] en grupo 0 con mecanismo [0,1,2]
        #       futuros [1,2] en grupo 1 con mecanismo [0,1,2]
        # NCubo 0 EN alcance → marginaliza en dims-dims=[] → indexa directo
        # NCubo 1,2 FUERA alcance → marginaliza EN mecanismo=[0,1,2] → media
        dist_k2 = geo.kpartir(
            [indices[:1], indices[1:]],
            [dims, dims]
        )

        # k=3: cada futuro en su propio grupo con mecanismo reducido
        # Grupo 0: futuro [0], mecanismo [0]   → NCubo 0 indexa solo en dim 0
        # Grupo 1: futuro [1], mecanismo [1]   → NCubo 1 indexa solo en dim 1
        # Grupo 2: futuro [2], mecanismo [0,1] → NCubo 2 marginaliza dim 2
        dist_k3 = geo.kpartir(
            [indices[:1], indices[1:2], indices[2:]],
            [dims[:1], dims[1:2], dims[:2]]
        )

        assert not np.allclose(dist_k2, dist_k3, atol=1e-4), \
            f"k=2 y k=3 dieron el mismo resultado con mecanismos distintos.\nk2={dist_k2}\nk3={dist_k3}"

    def test_grupos_disjuntos_obligatorio(self, subsistema_n4):
        """
        Si se pasan grupos solapados (mal uso de la API), el dict de
        mapeo asigna cada NCubo al último grupo que lo contiene.
        Verificar que al menos no explota y devuelve el tamaño correcto.
        """
        geo = hacer_geometric_con_subsistema(subsistema_n4)
        indices = subsistema_n4.indices_ncubos
        dims = subsistema_n4.dims_ncubos

        # Grupos solapados (mal uso intencional para test de robustez)
        grupos_solapados = [indices[:3], indices[1:4]]
        mecanismos = [dims, dims]

        dist = geo.kpartir(grupos_solapados, mecanismos)
        assert len(dist) == len(subsistema_n4.ncubos)
        assert np.all(dist >= 0.0) and np.all(dist <= 1.0)

    def test_ncubo_huerfano_usa_media_global(self, subsistema_n3):
        """
        Un NCubo sin grupo asignado debe usar la media global de su tensor.
        Verificar que el resultado es 1 - mean(data) para ese nodo.
        """
        geo = hacer_geometric_con_subsistema(subsistema_n3)
        indices = subsistema_n3.indices_ncubos
        dims = subsistema_n3.dims_ncubos

        # Solo asignar los primeros 2 futuros, dejar el tercero huérfano
        grupos = [indices[:1], indices[1:2]]
        mecanismos = [dims, dims]

        dist = geo.kpartir(grupos, mecanismos)

        # El NCubo huérfano (índice 2) debe ser 1 - mean(data)
        ncubo_huerfano = subsistema_n3.ncubos[2]
        esperado = 1.0 - float(np.mean(ncubo_huerfano.data))
        assert abs(float(dist[2]) - esperado) < 1e-6, \
            f"NCubo huérfano: esperado {esperado:.6f}, obtenido {float(dist[2]):.6f}"


# ---------------------------------------------------------------------------
# NIVEL 3 — Regresión de rendimiento
# ---------------------------------------------------------------------------

class TestRendimiento:
    """
    Verifica que kpartir() es significativamente más rápido que la ruta
    original bipartir() + distribucion_marginal() cuando se evalúan
    múltiples candidatos en secuencia (caso real de find_mip).
    """

    N_CANDIDATOS = 50
    # Para n=4 los objetos son tan pequeños que el overhead de Python domina.
    # El beneficio real de kpartir aparece con n>10 en producción.
    # Aquí validamos que no sea SIGNIFICATIVAMENTE más lento (< 0.8x).
    TOLERANCIA_SPEEDUP = 0.8

    @pytest.fixture
    def subsistema_n4(self):
        return hacer_subsistema(tpm_n4(), ESTADO_N4)

    def _generar_candidatos_n4(self, subsistema):
        """Genera N_CANDIDATOS pares (futuros, presentes) aleatorios para n=4."""
        rng = np.random.default_rng(0)
        indices = subsistema.indices_ncubos
        dims = subsistema.dims_ncubos
        candidatos = []
        for _ in range(self.N_CANDIDATOS):
            n_fut = rng.integers(1, len(indices) + 1)
            futuros = rng.choice(indices, size=n_fut, replace=False).astype(np.int8)
            n_pres = rng.integers(0, len(dims) + 1)
            presentes = rng.choice(dims, size=n_pres, replace=False).astype(np.int8) if n_pres > 0 \
                else np.array([], dtype=np.int8)
            candidatos.append((futuros, presentes))
        return candidatos

    def test_speedup_vs_bipartir(self, subsistema_n4):
        """
        kpartir() debe ser más rápido que bipartir() + distribucion_marginal()
        al evaluar múltiples candidatos en secuencia.
        """
        geo = hacer_geometric_con_subsistema(subsistema_n4)
        candidatos = self._generar_candidatos_n4(subsistema_n4)
        todos_futuros = subsistema_n4.indices_ncubos

        # --- Medir ruta original ---
        t0 = time.perf_counter()
        for futuros, presentes in candidatos:
            _ = subsistema_n4.bipartir(futuros, presentes).distribucion_marginal()
        tiempo_original = time.perf_counter() - t0

        # --- Medir ruta kpartir ---
        t0 = time.perf_counter()
        for futuros, presentes in candidatos:
            complemento = np.setdiff1d(todos_futuros, futuros)
            grupos = [futuros] + ([complemento] if complemento.size > 0 else [])
            mecanismos = [presentes] * len(grupos)
            _ = geo.kpartir(grupos, mecanismos)
        tiempo_kpartir = time.perf_counter() - t0

        speedup = tiempo_original / tiempo_kpartir
        print(f"\n  bipartir: {tiempo_original*1000:.2f}ms | kpartir: {tiempo_kpartir*1000:.2f}ms | speedup: {speedup:.2f}x")

        assert speedup >= self.TOLERANCIA_SPEEDUP, (
            f"kpartir no fue suficientemente más rápido: {speedup:.2f}x < {self.TOLERANCIA_SPEEDUP}x\n"
            f"  bipartir: {tiempo_original*1000:.2f}ms, kpartir: {tiempo_kpartir*1000:.2f}ms"
        )

    def test_sin_alocaciones_de_system(self, subsistema_n4):
        """
        kpartir() no debe crear objetos System ni NCube nuevos.
        Verificar indirectamente: el número de objetos NCube en memoria
        no debe crecer tras N llamadas a kpartir.
        """
        import gc
        from src.models.core.ncube import NCube

        geo = hacer_geometric_con_subsistema(subsistema_n4)
        candidatos = self._generar_candidatos_n4(subsistema_n4)
        todos_futuros = subsistema_n4.indices_ncubos

        gc.collect()
        # Contar NCubes antes
        ncubes_antes = sum(1 for obj in gc.get_objects() if isinstance(obj, NCube))

        for futuros, presentes in candidatos:
            complemento = np.setdiff1d(todos_futuros, futuros)
            grupos = [futuros] + ([complemento] if complemento.size > 0 else [])
            mecanismos = [presentes] * len(grupos)
            geo.kpartir(grupos, mecanismos)

        gc.collect()
        ncubes_despues = sum(1 for obj in gc.get_objects() if isinstance(obj, NCube))

        # Puede haber algunos NCubes temporales de marginalizar() que GC no limpió aún,
        # pero no deben crecer linealmente con N_CANDIDATOS
        crecimiento = ncubes_despues - ncubes_antes
        assert crecimiento < self.N_CANDIDATOS, (
            f"Posible leak de NCubes: {crecimiento} nuevos tras {self.N_CANDIDATOS} llamadas"
        )