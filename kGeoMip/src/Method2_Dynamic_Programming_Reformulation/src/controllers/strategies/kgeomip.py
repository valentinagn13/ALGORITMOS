import heapq
import logging
import math
import random
from src.constants.error import ERROR_INCOMPATIBLE_SIZES
from src.models.core.system import System
from src.constants.base import NET_LABEL, STR_ZERO
from src.funcs.base import ABECEDARY, seleccionar_subestado
from src.middlewares.slogger import SafeLogger
from src.funcs.base import emd_efecto
from src.models.base.sia import SIA
from src.constants.base import (
    ACTUAL,
    EFECTO,
    TYPE_TAG,
)
from src.constants.models import (
    KGEOMIP_ANALYSIS_TAG,
    KGEOMIP_LABEL,
    KGEOMIP_STRAREGY_TAG,
)
from src.controllers.manager import Manager
from src.funcs.format import fmt_grupos_particion
from src.middlewares.profile import profiler_manager, profile
from src.models.core.solution import Solution
import numpy as np
import time
from typing import List, Dict, Tuple, Optional


class KGeoMip(SIA):
    def __init__(self, gestor: Manager):
        super().__init__(gestor)
        profiler_manager.start_session(
            f"{NET_LABEL}{len(gestor.estado_inicial)}{gestor.pagina}"
        )
        self.etiquetas = [tuple(s.lower() for s in ABECEDARY), ABECEDARY]
        self.logger = SafeLogger(KGEOMIP_STRAREGY_TAG)
        self.tabla_transiciones: dict = {}
        self.vertices: set[tuple]
        self.tabla: dict[int, list[tuple[int, int]]] = {}
        self.memoria_particiones: dict[tuple, tuple[float, np.ndarray]] = {}
        self._candidatos_log: list[tuple[str, float]] = []
        self._tiempo_preparacion: float = 0.0
        self._tiempo_hipercubo: float = 0.0
        self._tiempo_candidatos: float = 0.0

        self._cache_phi: dict[tuple, float] = {}
        self._cache_marg: dict[tuple, float] = {}
        self._tiempo_sa: float = 0.0

        self.sa_enabled = True
        self.sa_enabled_force = False
        self.sa_min_n = 10
        self.sa_max_iter = 1700
        self.sa_max_time = 25.0
        self.sa_T0: Optional[float] = None
        self.sa_alpha = 0.995
        self.sa_seed = 42

    @staticmethod
    def _bits_to_int(bits):
        val = 0
        for b in bits:
            val = (val << 1) | b
        return val

    @profile(context={TYPE_TAG: KGEOMIP_ANALYSIS_TAG})
    def aplicar_estrategia(
        self,
        condicion: str,
        alcance: str,
        mecanismo: str,
        tpm: np.ndarray,  #! COMENTAR PARA UN SOLO ESTADO INICIAL
        k: int = 2,
    ):
        self.logger.info("═" * 60)
        self.logger.info("     ESTRATEGIA K-GeoMIP — INICIO")
        self.logger.info("═" * 60)

        self.sia_preparar_subsistema(condicion, alcance, mecanismo, tpm)  #! COMENTAR PARA UN SOLO ESTADO INICIAL
        # self.sia_preparar_subsistema(condicion, alcance, mecanismo)  #! DESCOMENTAR PARA UN SOLO ESTADO INICIAL

        self._tiempo_preparacion = time.time()

        futuro = tuple(
            (EFECTO, efecto) for efecto in self.sia_subsistema.indices_ncubos
        )
        presente = tuple(
            (ACTUAL, actual) for actual in self.sia_subsistema.dims_ncubos
        )

        self.logger.info("─" * 50)
        self.logger.info("  FASE 1: PREPARACIÓN DEL SUBSISTEMA")
        self.logger.info("─" * 50)
        self.logger.info(f"  • Condición (background):   {condicion}")
        self.logger.info(f"  • Alcance (futuro):         {alcance}")
        self.logger.info(f"  • Mecanismo (presente):     {mecanismo}")
        self.logger.info(f"  • TPM original cargada:     {tpm.shape}")
        dims_cond = np.array([i for i, b in enumerate(condicion) if b == '0'], dtype=np.int8)
        self.logger.info(f"  • Dimensiones condicionadas: {dims_cond.tolist()}")
        self.logger.info(f"  • Variables futuro (alcance): {self.sia_subsistema.indices_ncubos.tolist()}")
        self.logger.info(f"  • Variables presente (mecanismo): {self.sia_subsistema.dims_ncubos.tolist()}")
        self.logger.info(f"  • Subsistema NCubos:        {len(self.sia_subsistema.ncubos)}")
        self.logger.info(f"  • Distribución marginal ref: {np.array2string(self.sia_dists_marginales, precision=4)}")

        # Aplanar datos de cada NCubo una sola vez para acceso O(1) en calcular_costo
        self._flat_data = [ncubo.data.ravel() for ncubo in self.sia_subsistema.ncubos]

        self.vertices = set(presente + futuro)
        dims = self.sia_subsistema.dims_ncubos
        self.estado_inicial = self.sia_subsistema.estado_inicial[dims]
        self.estado_final = 1 - self.estado_inicial

        self._tiempo_preparacion = time.time() - self._tiempo_preparacion

        self.logger.info(f"  ✅ Preparación completada en {self._tiempo_preparacion:.4f}s")

        mip = self.find_mip(k=k)

        grupos_futuro, grupos_presente = self._formatear_particion(mip, k)
        fmt_mip = fmt_grupos_particion(grupos_futuro, grupos_presente)

        # ── Tabla comparativa final ──
        self.logger.info("")
        self.logger.info("═" * 60)
        self.logger.info("     FASE 5: SELECCIÓN FINAL — TABLA COMPARATIVA")
        self.logger.info("═" * 60)
        self.logger.info(f"  {'Candidato':<30} {'φ (EMD)':<15}")
        self.logger.info("  " + "─" * 45)
        for desc, phi_val in self._candidatos_log:
            marca = " ◀ MIP" if phi_val == self.memoria_particiones[mip][0] else ""
            self.logger.info(f"  {desc:<30} {phi_val:<15.6f}{marca}")
        self.logger.info("")
        self.logger.info(f"  🏆 MIP elegido:  φ = {self.memoria_particiones[mip][0]:.6f}")
        self.logger.info(f"  📋 Partición final:\n{fmt_mip}")
        self.logger.info("")

        return Solution(
            estrategia=KGEOMIP_LABEL,
            perdida=self.memoria_particiones[mip][0],
            distribucion_subsistema=self.sia_dists_marginales,
            distribucion_particion=self.memoria_particiones[mip][1],
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=fmt_mip,
            grupos_futuro=grupos_futuro,
            grupos_presente=grupos_presente,
            tiempos_parciales={
                "preparacion": self._tiempo_preparacion,
                "hipercubo": self._tiempo_hipercubo,
                "candidatos": self._tiempo_candidatos,
            },
        )

    def _formatear_particion(self, mip: tuple, k: int) -> tuple[list[str], list[str]]:
        """
        Convierte una partición (mip) en listas estructuradas de grupos.

        Returns:
            (grupos_futuro, grupos_presente):
              - grupos_futuro:  lista de cadenas con letras MAYÚSCULAS separadas por coma
              - grupos_presente: lista de cadenas con letras minúsculas separadas por coma
        """
        if k == 2:
            complemento = list(set(self.vertices) - set(mip))

            fut_mip = sorted(n for tag, n in mip if tag == 1)
            pres_mip = sorted(n for tag, n in mip if tag == 0)
            fut_comp = sorted(n for tag, n in complemento if tag == 1)
            pres_comp = sorted(n for tag, n in complemento if tag == 0)

            grupos_fut = [
                ",".join(ABECEDARY[i] for i in fut_mip),
                ",".join(ABECEDARY[i] for i in fut_comp),
            ]
            grupos_pres = [
                ",".join(ABECEDARY[i].lower() for i in pres_mip),
                ",".join(ABECEDARY[i].lower() for i in pres_comp),
            ]
            return grupos_fut, grupos_pres

        # k > 2
        grupos: dict[int, list[int]] = {}
        for g_idx, nodo in mip:
            grupos.setdefault(g_idx, []).append(nodo)

        grupos_fut = []
        grupos_pres = []
        for g in sorted(grupos):
            nodos = sorted(grupos[g])
            grupos_fut.append(",".join(ABECEDARY[i] for i in nodos))
            grupos_pres.append(",".join(ABECEDARY[i].lower() for i in nodos))

        return grupos_fut, grupos_pres

    def find_mip(self, k: int = 2):
        """
        Encuentra la k-partición óptima usando el enfoque geométrico-topológico.

        Para k=2 el comportamiento es idéntico al original (bipartición).
        Para k>2 los candidatos se generan asignando variables futuras a k grupos
        basándose en la tabla de costos T, y cada candidato se evalúa con kpartir()
        en lugar de bipartir(), evitando construir objetos System intermedios.
        """
        estado_inicial = self.estado_inicial
        estado_final = self.estado_final
        self.idx_ncubos = list(range(len(self.sia_subsistema.indices_ncubos)))
        n_ncubos = len(self.sia_subsistema.indices_ncubos)

        # ── FASE 2: HIPERCUBO ──
        self.logger.info("")
        self.logger.info("─" * 50)
        self.logger.info("  FASE 2: CONSTRUCCIÓN DEL HIPERCUBO DE ESTADOS")
        self.logger.info("─" * 50)
        self.logger.info(f"  • Estado inicial (s₀):  {estado_inicial.tolist()}")
        self.logger.info(f"  • Estado final   (s₁):  {estado_final.tolist()}")
        self.logger.info(f"  • Dimensiones:          {len(estado_inicial)}")
        self.logger.info(f"  • Nodos futuros:        {n_ncubos}")
        self._tiempo_hipercubo = time.time()

        # Inicializar caminos PRIMERO, luego la tabla (corrige bug de orden)
        self.caminos: Dict[int, List[List[int]]] = {0: [estado_inicial.tolist()]}
        estado_ini_tuple = tuple(self.caminos[0][0])
        self._bits_estado_inicial = self._bits_to_int(reversed(self.caminos[0][0]))
        self.tabla_transiciones[
            (estado_ini_tuple, estado_ini_tuple)
        ] = [0.0] * n_ncubos

        for nivel in range(1, len(estado_inicial) + 1):
            self.calcular_costos_nivel(estado_final, nivel)

        # Mostrar resumen de caminos por nivel
        for nivel, estados in self.caminos.items():
            self.logger.debug(f"  • Nivel {nivel}: {len(estados)} estados")

        self.logger.info(f"  • Transiciones en tabla: {len(self.tabla_transiciones)}")

        self._tiempo_hipercubo = time.time() - self._tiempo_hipercubo
        self.logger.info(f"  ✅ Hipercubo construido en {self._tiempo_hipercubo:.4f}s")

        # ── FASE 3: IDENTIFICACIÓN DE CANDIDATOS ──
        self._tiempo_candidatos = time.time()
        candidatos = self.identificar_particiones_optimas(k=k)
        self.logger.info("")
        self.logger.info("─" * 50)
        self.logger.info("  FASE 3: EVALUACIÓN DE CANDIDATOS")
        self.logger.info("─" * 50)

        # Precomputar arrays de índices globales una sola vez
        dims_ncubos = self.sia_subsistema.dims_ncubos
        indices_ncubos = self.sia_subsistema.indices_ncubos

        for idx_c, grupos_locales in enumerate(candidatos):
            if k == 2:
                presentes_loc, futuros_loc = grupos_locales
                presentes_arr = np.array(presentes_loc, dtype=np.int8)
                futuros_arr = np.array(futuros_loc, dtype=np.int8)
                presentes_glob = dims_ncubos[presentes_arr] if presentes_arr.size > 0 else np.array([], dtype=np.int8)
                futuros_glob = indices_ncubos[futuros_arr] if futuros_arr.size > 0 else np.array([], dtype=np.int8)

                # ── Mostrar candidato ──
                futuros_letras = "".join(ABECEDARY[i] for i in futuros_glob)
                presentes_letras = "".join(ABECEDARY[i] for i in presentes_glob)

                grupos_glob = [futuros_glob]
                mecanismos_glob = [presentes_glob]

                todos_futuros = indices_ncubos
                futuros_complemento = np.setdiff1d(todos_futuros, futuros_glob)
                if futuros_complemento.size > 0:
                    grupos_glob.append(futuros_complemento)
                    mecanismos_glob.append(presentes_glob)

                dist = self.kpartir(grupos_glob, mecanismos_glob)
                emd = emd_efecto(dist, self.sia_dists_marginales)

                key = tuple([(0, nodo) for nodo in presentes_glob] +
                             [(1, nodo) for nodo in futuros_glob])
                self.memoria_particiones[key] = (emd, dist)
                self._candidatos_log.append((f"k=2 #{idx_c+1} [{futuros_letras}|{presentes_letras}]", emd))

            else:
                grupos_glob = []
                mecanismos_glob = []
                key_parts = []

                grupos_letras = []
                for g_idx, futuros_loc in enumerate(grupos_locales):
                    futuros_g = indices_ncubos[futuros_loc] if len(futuros_loc) > 0 else np.array([], dtype=np.int8)

                    presentes_loc = [i for i in range(len(dims_ncubos)) if i % k == g_idx]
                    presentes_g = dims_ncubos[presentes_loc] if presentes_loc else np.array([], dtype=np.int8)

                    grupos_glob.append(futuros_g)
                    mecanismos_glob.append(presentes_g)
                    key_parts.extend([(g_idx, int(n)) for n in futuros_g])
                    g_letras = "".join(ABECEDARY[i] for i in futuros_g) if futuros_g.size > 0 else "∅"
                    grupos_letras.append(g_letras)

                dist = self.kpartir(grupos_glob, mecanismos_glob)
                emd = emd_efecto(dist, self.sia_dists_marginales)

                key = tuple(key_parts)
                self.memoria_particiones[key] = (emd, dist)
                self._candidatos_log.append((f"k={k} #{idx_c+1} {grupos_letras}", emd))

        self._tiempo_candidatos = time.time() - self._tiempo_candidatos
        self.logger.info(f"  ✅ {len(candidatos)} candidatos evaluados en {self._tiempo_candidatos:.4f}s")

        # ── FASE 4: SIMULATED ANNEALING (solo k>2 y si está habilitado) ──
        if k > 2 and self._sa_debe_ejecutar(k, n_ncubos):
            self._local_from_global = {
                int(g): i for i, g in enumerate(indices_ncubos)
            }

            mejor_key = min(
                self.memoria_particiones, key=lambda k_: self.memoria_particiones[k_][0]
            )
            mejor_phi_heuristico = self.memoria_particiones[mejor_key][0]

            particion_inicial = self._key_a_particion(mejor_key, n_ncubos)

            particion_sa, phi_sa = self.simulated_annealing(k, particion_inicial)

            if phi_sa < mejor_phi_heuristico - 1e-12:
                key_parts = []
                grupos_letras = []
                for g_idx in range(k):
                    miembros = [int(indices_ncubos[i]) for i in range(n_ncubos)
                                if particion_sa[i] == g_idx]
                    key_parts.extend([(g_idx, m) for m in miembros])
                    g_letras = "".join(ABECEDARY[i] for i in miembros) if miembros else "∅"
                    grupos_letras.append(g_letras)

                _, dist_sa = self._evaluar_particion(particion_sa, k)
                key_sa = tuple(key_parts)
                self.memoria_particiones[key_sa] = (phi_sa, dist_sa)
                self._candidatos_log.append((f"SA k={k} {grupos_letras}", phi_sa))
                self.logger.info(f"  🏆 SA mejoró: φ = {mejor_phi_heuristico:.6f} → {phi_sa:.6f}")
            else:
                self.logger.info(f"  ℹ️  SA no encontró mejora (φ heurístico = {mejor_phi_heuristico:.6f})")

        return min(
            self.memoria_particiones, key=lambda k_: self.memoria_particiones[k_][0]
        )

    def _sa_debe_ejecutar(self, k: int, n: int) -> bool:
        if k <= 2:
            return False
        if self.sa_enabled_force:
            return True
        return self.sa_enabled and n >= self.sa_min_n

    def kpartir(
        self,
        grupos: list[np.ndarray],
        mecanismos: list[np.ndarray],
    ) -> np.ndarray:
        """
        Calcula la distribución marginal de una k-partición.
        
        Regla de decisión:
        - Si hay exactamente 2 grupos con el mismo mecanismo (caso bipartición con complemento):
            * Grupo 0 (índice 0) → "dentro" (marginalizar en dims - mecanismo)
            * Grupo 1 (índice 1) → "fuera" (marginalizar EN mecanismo)
        - En caso contrario (k>2 o grupos con mecanismos diferentes):
            * Todos los nodos que pertenecen a algún grupo se tratan como "dentro"
            * Los nodos sin grupo se tratan como "fuera" (marginalizar en mecanismo de referencia)
        """
        subsistema = self.sia_subsistema
        estado_inicial = subsistema.estado_inicial

        # Detectar si es el caso especial de bipartición con complemento (k=2)
        es_biparticion_con_complemento = (
            len(grupos) == 2 and len(mecanismos) == 2 and
            np.array_equal(mecanismos[0], mecanismos[1])
        )

        # Mapeo nodo -> (g_idx, mecanismo) para búsqueda O(1)
        nodo_info: dict[int, tuple[int, np.ndarray]] = {}
        for g_idx, (grupo, mecanismo) in enumerate(zip(grupos, mecanismos)):
            for nodo in grupo:
                nodo_info[int(nodo)] = (g_idx, mecanismo)

        # Mecanismo de referencia para nodos fuera de todos los grupos
        mecanismo_fuera = np.array([], dtype=np.int8)
        for mec in mecanismos:
            if len(mec) > 0:
                mecanismo_fuera = mec
                break

        n_ncubos = len(subsistema.ncubos)
        resultado = np.empty(n_ncubos, dtype=np.float32)

        for i, ncubo in enumerate(subsistema.ncubos):
            idx_ncubo = int(ncubo.indice)

            if idx_ncubo in nodo_info:
                g_idx, mecanismo_grupo = nodo_info[idx_ncubo]
                if es_biparticion_con_complemento and g_idx == 1:
                    ejes = mecanismo_grupo
                    grupo_str = "fuera"
                else:
                    ejes = np.setdiff1d(ncubo.dims, mecanismo_grupo)
                    grupo_str = "dentro"
            else:
                ejes = mecanismo_fuera
                grupo_str = "sin-grupo"

            prob = self._marginalizar_e_indexar(ncubo, ejes, estado_inicial)
            resultado[i] = 1.0 - prob

            if self.logger._logger.isEnabledFor(logging.DEBUG):
                letra = ABECEDARY[idx_ncubo] if idx_ncubo < len(ABECEDARY) else f"?{idx_ncubo}"
                self.logger.debug(f"       NCubo {letra}({idx_ncubo}) → grupo={grupo_str}  P(ON)={prob:.4f}  dist={1.0-prob:.4f}")

        emd_parcial = emd_efecto(resultado, self.sia_dists_marginales)
        if self.logger._logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"       Distribución resultante: {np.array2string(resultado, precision=4)}")
            self.logger.debug(f"       EMD parcial: {emd_parcial:.6f}")
        return resultado

    def _marginalizar_e_indexar(
        self,
        ncubo,
        ejes: np.ndarray,
        estado_inicial: np.ndarray,
    ) -> float:
        """
        Aplica marginalización sobre `ejes` y luego indexa con estado_inicial.
        Extraído de kpartir() para claridad y reutilización.

        - ejes vacíos    → sin marginalización, indexar directo
        - ejes == dims   → marginalizar todo → media del tensor
        - caso parcial   → marginalizar y luego indexar dims restantes
        """
        key = (ncubo.indice, tuple(ejes), tuple(estado_inicial))
        if key in self._cache_marg:
            return self._cache_marg[key]

        if ejes.size == 0:
            sub_estado = tuple(estado_inicial[j] for j in ncubo.dims)
            val = float(ncubo.data[seleccionar_subestado(sub_estado)])
        elif ejes.size == ncubo.dims.size:
            val = float(np.mean(ncubo.data))
        else:
            cubo_marg = ncubo.marginalizar(ejes)
            if cubo_marg.dims.size == 0:
                val = float(cubo_marg.data)
            else:
                sub_estado = tuple(estado_inicial[j] for j in cubo_marg.dims)
                val = float(cubo_marg.data[seleccionar_subestado(sub_estado)])

        self._cache_marg[key] = val
        return val

    def calcular_costos_nivel(self, estado_final: np.ndarray, nivel):
        n = len(estado_final)
        visitados: set[tuple] = set()
        self.caminos[nivel] = []
        for estado_anterior in self.caminos[nivel - 1]:
            estado_actual = np.array(estado_anterior)
            for i in range(n):
                if estado_actual[i] != estado_final[i]:
                    nuevo_estado = estado_actual.copy()
                    nuevo_estado[i] = estado_final[i]
                    nuevo_estado_tuple = tuple(nuevo_estado)
                    if nuevo_estado_tuple not in visitados:
                        self.caminos[nivel].append(nuevo_estado.tolist())
                        self.calcular_costo(
                            self.caminos[0][0], nuevo_estado.tolist(), self.idx_ncubos
                        )
                        visitados.add(nuevo_estado_tuple)

    def calcular_costo(self, estado_inicial: tuple, estado_final: tuple, ncubos: list[int]):
        """
        Calcula el costo de transición del estado_inicial al estado_final
        para las variables futuras en ncubos.

        Fórmula: tx(i,j) = γ · (|X[i] - X[j]| + Σ tx(k,j))
        donde γ = 1/2^dH(i,j) y k recorre vecinos intermedios en caminos óptimos.
        """
        key = tuple(estado_inicial), tuple(estado_final)
        if key not in self.tabla_transiciones:
            self.tabla_transiciones[key] = [None] * len(self.sia_subsistema.indices_ncubos)

        distancia_hamming = self.hamming(estado_inicial, estado_final)
        factor = 1 / (2 ** distancia_hamming)

        estado_fin_int = self._bits_to_int(reversed(estado_final))

        # Calcular diferencias absolutas para todos los NCubos de una vez (vectorizado)
        diffs = np.abs(
            np.array([flat[self._bits_estado_inicial] for flat in self._flat_data])
            - np.array([flat[estado_fin_int] for flat in self._flat_data])
        )
        self.tabla_transiciones[key] = diffs.tolist()

        # Acumular costos de vecinos intermedios si dH > 1
        if distancia_hamming > 1:
            for i in range(len(estado_inicial)):
                if estado_inicial[i] != estado_final[i]:
                    nuevo_estado = list(estado_final)
                    nuevo_estado[i] = estado_inicial[i]
                    temp_key = tuple(estado_inicial), tuple(nuevo_estado)
                    for n in ncubos:
                        self.tabla_transiciones[key][n] += self.tabla_transiciones[temp_key][n]

        # Aplicar factor de decrecimiento exponencial
        self.tabla_transiciones[key] = [
            factor * v for v in self.tabla_transiciones[key]
        ]

    def identificar_particiones_optimas(self, k: int = 2) -> list:
        """
        Identifica particiones candidatas basadas en los costos de la tabla T.

        Para k=2: comportamiento original — devuelve pares [presentes, futuros].
        Para k>2: agrupa las variables futuras en k clusters usando los vectores
                  de costo como features, asignando cada variable al grupo de
                  menor costo acumulado.

        Returns:
            Lista de candidatos. Cada candidato es:
              - k=2: [presentes_idx, futuros_idx]  (listas de índices locales)
              - k>2: [grupo_0_idx, grupo_1_idx, ..., grupo_{k-1}_idx]
        """
        key = tuple(self.caminos[0][0]), tuple(self.estado_final)
        costos: list = self.tabla_transiciones[key]
        n_vars = len(costos)
        candidatos = []

        if k == 2:
            self.logger.info("")
            self.logger.info(f"  • Candidatos k=2 — one-removed (n_vars={n_vars}) + niveles intermedios ({len(self.caminos)//2} niveles)")
            for idx in range(n_vars):
                presentes = list(range(len(self.estado_final)))
                futuros = [i for i in range(n_vars) if i != idx]
                candidatos.append([presentes, futuros])

            es_par = len(self.caminos) % 2 == 0
            mitad = len(self.caminos) // 2 if es_par else (len(self.caminos) // 2) + 1

            for nivel in range(1, mitad):
                costo_candidato_nivel = 1e5
                presentes_nivel, futuros_nivel = [], []

                for estado in self.caminos[nivel]:
                    costo_candidato = 0
                    presentes, futuros = [], []
                    actual = self.tabla_transiciones.get(
                        (tuple(self.caminos[0][0]), tuple(estado)), None
                    )
                    estado_complementario = (1 - np.array(estado)).tolist()
                    complementario = self.tabla_transiciones.get(
                        (tuple(self.caminos[0][0]), tuple(estado_complementario)), None
                    )
                    for idx, i in enumerate(estado):
                        if i == self.caminos[0][0][idx]:
                            presentes.append(idx)
                    for idx in range(len(self.idx_ncubos)):
                        if actual[idx] <= complementario[idx]:
                            futuros.append(idx)
                            costo_candidato += actual[idx]
                        else:
                            costo_candidato += complementario[idx]
                    if costo_candidato < costo_candidato_nivel:
                        costo_candidato_nivel = costo_candidato
                        presentes_nivel = presentes
                        futuros_nivel = futuros

                candidatos.append([presentes_nivel, futuros_nivel])

        else:
            self.logger.info(f"")
            self.logger.info(f"  • Candidatos k={k} — round-robin por costo ({n_vars} vars, {len(self.caminos)//2} niveles)")
            costos_arr = np.array(costos, dtype=np.float64)
            orden = np.argsort(costos_arr)

            grupos_base = [[] for _ in range(k)]
            for pos, var_idx in enumerate(orden):
                grupos_base[pos % k].append(int(var_idx))
            candidatos.append(grupos_base)

            es_par = len(self.caminos) % 2 == 0
            mitad = len(self.caminos) // 2 if es_par else (len(self.caminos) // 2) + 1

            for nivel in range(1, mitad):
                mejor_costo = 1e5
                mejor_grupos = None

                for estado in self.caminos[nivel]:
                    actual = self.tabla_transiciones.get(
                        (tuple(self.caminos[0][0]), tuple(estado)), None
                    )
                    if actual is None:
                        continue

                    costos_nivel = np.array(actual, dtype=np.float64)
                    orden_nivel = np.argsort(costos_nivel)

                    grupos_nivel = [[] for _ in range(k)]
                    for pos, var_idx in enumerate(orden_nivel):
                        grupos_nivel[pos % k].append(int(var_idx))

                    costo_total = float(np.sum(costos_nivel))
                    if costo_total < mejor_costo:
                        mejor_costo = costo_total
                        mejor_grupos = grupos_nivel

                if mejor_grupos is not None:
                    candidatos.append(mejor_grupos)

        return candidatos

    # ─────────────────────────────────────────────────────────
    #  SIMULATED ANNEALING PARA k>2
    # ─────────────────────────────────────────────────────────

    def _heuristico_a_particion(self, grupos_locales: list, n: int) -> np.ndarray:
        particion = np.full(n, -1, dtype=np.int8)
        for g_idx, grupo in enumerate(grupos_locales):
            for var_idx in grupo:
                particion[int(var_idx)] = g_idx
        return particion

    def _key_a_particion(self, key: tuple, n: int) -> np.ndarray:
        particion = np.full(n, -1, dtype=np.int8)
        for g_idx, nodo_global in key:
            pos = int(self._local_from_global.get(int(nodo_global), -1))
            if pos >= 0:
                particion[pos] = g_idx
        return particion

    def _particion_a_grupos_glob(self, particion: np.ndarray, k: int):
        n = len(particion)
        grupos_glob: list[np.ndarray] = []
        mecanismos_glob: list[np.ndarray] = []
        dims_ncubos = self.sia_subsistema.dims_ncubos
        indices_ncubos = self.sia_subsistema.indices_ncubos

        for g_idx in range(k):
            miembros = [int(indices_ncubos[i]) for i in range(n) if particion[i] == g_idx]
            futuros_g = np.array(miembros, dtype=np.int8) if miembros else np.array([], dtype=np.int8)

            presentes_loc = [i for i in range(len(dims_ncubos)) if i % k == g_idx]
            presentes_g = dims_ncubos[presentes_loc] if presentes_loc else np.array([], dtype=np.int8)

            grupos_glob.append(futuros_g)
            mecanismos_glob.append(presentes_g)

        return grupos_glob, mecanismos_glob

    def _evaluar_particion(self, particion: np.ndarray, k: int) -> tuple[float, np.ndarray]:
        clave = tuple(int(x) for x in particion)
        if clave in self._cache_phi:
            return self._cache_phi[clave]

        grupos_glob, mecanismos_glob = self._particion_a_grupos_glob(particion, k)
        dist = self._fast_kpartir(grupos_glob, mecanismos_glob)
        emd = emd_efecto(dist, self.sia_dists_marginales)
        self._cache_phi[clave] = (emd, dist)
        return emd, dist

    def _fast_kpartir(self, grupos, mecanismos) -> np.ndarray:
        subsistema = self.sia_subsistema
        estado_inicial = subsistema.estado_inicial

        es_biparticion_con_complemento = (
            len(grupos) == 2 and len(mecanismos) == 2 and
            np.array_equal(mecanismos[0], mecanismos[1])
        )

        nodo_info: dict[int, tuple[int, np.ndarray]] = {}
        for g_idx, (grupo, mecanismo) in enumerate(zip(grupos, mecanismos)):
            for nodo in grupo:
                nodo_info[int(nodo)] = (g_idx, mecanismo)

        mecanismo_fuera = np.array([], dtype=np.int8)
        for mec in mecanismos:
            if len(mec) > 0:
                mecanismo_fuera = mec
                break

        n_ncubos = len(subsistema.ncubos)
        resultado = np.empty(n_ncubos, dtype=np.float32)

        for i, ncubo in enumerate(subsistema.ncubos):
            idx_ncubo = int(ncubo.indice)
            if idx_ncubo in nodo_info:
                g_idx, mecanismo_grupo = nodo_info[idx_ncubo]
                if es_biparticion_con_complemento and g_idx == 1:
                    ejes = mecanismo_grupo
                else:
                    ejes = np.setdiff1d(ncubo.dims, mecanismo_grupo)
            else:
                ejes = mecanismo_fuera

            prob = self._marginalizar_e_indexar(ncubo, ejes, estado_inicial)
            resultado[i] = 1.0 - prob

        return resultado

    def simulated_annealing(
        self,
        k: int,
        particion_inicial: np.ndarray,
    ) -> tuple[np.ndarray, float]:
        n = len(particion_inicial)

        random.seed(self.sa_seed)
        rng = random.Random(self.sa_seed)

        actual = particion_inicial.copy()
        actual_phi, _ = self._evaluar_particion(actual, k)
        mejor = actual.copy()
        mejor_phi = actual_phi

        if self.sa_T0 is not None:
            T = self.sa_T0
        else:
            T = max(0.1 * actual_phi, 0.001)

        t_start = time.time()
        n_iter = 0

        self.logger.info(f"")
        self.logger.info("─" * 50)
        self.logger.info(f"  FASE 4: SIMULATED ANNEALING (k={k}, n={n})")
        self.logger.info("─" * 50)
        self.logger.info(f"  • T0        = {T:.6f}")
        self.logger.info(f"  • α         = {self.sa_alpha}")
        self.logger.info(f"  • max_iter  = {self.sa_max_iter}")
        self.logger.info(f"  • max_time  = {self.sa_max_time:.1f}s")
        self.logger.info(f"  • φ inicial = {actual_phi:.6f}")

        for n_iter in range(1, self.sa_max_iter + 1):
            elapsed = time.time() - t_start
            if elapsed >= self.sa_max_time:
                self.logger.info(f"  ⏱  Límite de tiempo alcanzado ({elapsed:.1f}s)")
                break

            if T < 1e-10:
                break

            nodo = rng.randint(0, n - 1)
            grupo_actual = int(actual[nodo])
            nuevo_grupo = rng.randint(0, k - 2)
            if nuevo_grupo >= grupo_actual:
                nuevo_grupo += 1

            vecino = actual.copy()
            vecino[nodo] = nuevo_grupo

            vecino_phi, _ = self._evaluar_particion(vecino, k)

            delta = vecino_phi - actual_phi

            if delta < 0 or rng.random() < math.exp(-delta / T):
                actual = vecino
                actual_phi = vecino_phi
                if actual_phi < mejor_phi:
                    mejor = actual.copy()
                    mejor_phi = actual_phi

            T *= self.sa_alpha

            if n_iter % 1000 == 0:
                self.logger.debug(f"     iter {n_iter:5d}  T={T:.6f}  actual_φ={actual_phi:.6f}  mejor_φ={mejor_phi:.6f}")

        t_total = time.time() - t_start
        self._tiempo_sa += t_total
        self.logger.info(f"  • iteraciones = {n_iter}")
        self.logger.info(f"  • tiempo SA  = {t_total:.4f}s")
        self.logger.info(f"  • φ final    = {mejor_phi:.6f}")
        self.logger.info(f"  • mejora     = {actual_phi - mejor_phi:+.6f}")
        self.logger.info("")

        return mejor, mejor_phi

    def hamming(self, a: List[int], b: List[int]) -> int:
        return sum(x != y for x, y in zip(a, b))