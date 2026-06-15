import time
from typing import Union
import numpy as np
from src.middlewares.slogger import SafeLogger
from src.funcs.base import emd_efecto, ABECEDARY
from src.middlewares.profile import profiler_manager, profile
from src.funcs.format import fmt_biparte_q
from src.controllers.manager import Manager
from src.models.base.sia import SIA

from src.models.core.solution import Solution
from src.constants.models import (
    QNODES_ANALYSIS_TAG,
    QNODES_LABEL,
    QNODES_STRAREGY_TAG,
)
from src.constants.base import (
    TYPE_TAG,
    NET_LABEL,
    INFTY_NEG,
    INFTY_POS,
    LAST_IDX,
    EFECTO,
    ACTUAL,
)


class QNodes(SIA):
    """
    Clase QNodes para el análisis de redes mediante el algoritmo Q.

    Esta clase implementa un gestor principal para el análisis de redes que utiliza
    el algoritmo Q para encontrar la partición óptima que minimiza la
    pérdida de información en el sistema. Hereda de la clase base SIA (Sistema de
    Información Activo) y proporciona funcionalidades para analizar la estructura
    y dinámica de la red.

    Args:
    ----
        config (Loader):
            Instancia de la clase Loader que contiene la configuración del sistema
            y los parámetros necesarios para el análisis.

    Attributes:
    ----------
        m (int):
            Número de elementos en el conjunto de purview (vista).

        n (int):
            Número de elementos en el conjunto de mecanismos.

        tiempos (tuple[np.ndarray, np.ndarray]):
            Tupla de dos arrays que representan los tiempos para los estados
            actual y efecto del sistema.

        etiquetas (list[tuple]):
            Lista de tuplas conteniendo las etiquetas para los nodos,
            con versiones en minúsculas y mayúsculas del abecedario.

        vertices (set[tuple]):
            Conjunto de vértices que representan los nodos de la red,
            donde cada vértice es una tupla (tiempo, índice).

        memoria (dict):
            Diccionario para almacenar resultados intermedios y finales
            del análisis (memoización).

        logger:
            Instancia del logger configurada para el análisis Q.

    Methods:
    -------
        run(condicion, purview, mechanism):
            Ejecuta el análisis principal de la red con las condiciones,
            purview y mecanismo especificados.

        algorithm(vertices):
            Implementa el algoritmo Q para encontrar la partición
            óptima del sistema.

        funcion_submodular(deltas, omegas):
            Calcula la función submodular para evaluar particiones candidatas.

        view_solution(mip):
            Visualiza la solución encontrada en términos de las particiones
            y sus valores asociados.

        nodes_complement(nodes):
            Obtiene el complemento de un conjunto de nodos respecto a todos
            los vértices del sistema.

    Notes:
    -----
    - La clase implementa una versión secuencial del algoritmo Q para encontrar la partición que minimiza la pérdida de información.
    - Utiliza memoización para evitar recálculos innecesarios durante el proceso.
    - El análisis se realiza considerando dos tiempos: actual (presente) y
      efecto (futuro).
    """

    def __init__(self, gestor: Manager):
        super().__init__(gestor)
        profiler_manager.start_session(
            f"{NET_LABEL}{len(gestor.estado_inicial)}{gestor.pagina}"
        )
        self.m: int
        self.n: int
        self.tiempos: tuple[np.ndarray, np.ndarray]
        self.etiquetas = [tuple(s.lower() for s in ABECEDARY), ABECEDARY]
        self.vertices: set[tuple]
        self.memoria_omega = dict()
        self.memoria_particiones = dict()

        self.indices_alcance: np.ndarray
        self.indices_mecanismo: np.ndarray

        self.logger = SafeLogger(QNODES_STRAREGY_TAG)

        self._tiempo_preparacion: float = 0.0
        self._tiempo_algoritmo: float = 0.0
        self._candidatos_log: list[tuple[str, float]] = []

    @profile(context={TYPE_TAG: QNODES_ANALYSIS_TAG})
    def aplicar_estrategia(
        self,
        condicion: str,
        alcance: str,
        mecanismo: str,
        tpm: np.ndarray = None,
        k: int = 2,
    ):
        self.logger.info("═" * 60)
        self.logger.info("     ESTRATEGIA Q-NODES — INICIO")
        self.logger.info("═" * 60)

        if tpm is not None:
            self.sia_preparar_subsistema(condicion, alcance, mecanismo, tpm)
        else:
            self.sia_preparar_subsistema(condicion, alcance, mecanismo)

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
        self.logger.info(f"  • k (particiones):          {k}")
        self.logger.info(f"  • Vértices futuro (EFECTO): {[ABECEDARY[e] for e in self.sia_subsistema.indices_ncubos]}")
        self.logger.info(f"  • Vértices presente (ACTUAL): {[ABECEDARY[a] for a in self.sia_subsistema.dims_ncubos]}")
        self.logger.info(f"  • Distribución marginal ref: {np.array2string(self.sia_dists_marginales, precision=4)}")

        self.m = self.sia_subsistema.indices_ncubos.size
        self.n = self.sia_subsistema.dims_ncubos.size

        self.indices_alcance = self.sia_subsistema.indices_ncubos
        self.indices_mecanismo = self.sia_subsistema.dims_ncubos

        self.tiempos = (
            np.zeros(self.n, dtype=np.int8),
            np.zeros(self.m, dtype=np.int8),
        )

        vertices = list(presente + futuro)
        self.vertices = set(presente + futuro)

        self._tiempo_preparacion = time.time() - self._tiempo_preparacion
        self.logger.info(f"  ✅ Preparación completada en {self._tiempo_preparacion:.4f}s")

        if k == 2:
            mip = self._algorithm_k2(vertices)
            fmt_mip = fmt_biparte_q(list(mip), self.nodes_complement(mip))
        else:
            mip = self._algorithm_kk(vertices, k)
            fmt_mip = self._formatear_kparticion(mip, k)

        # ── Tabla comparativa final ──
        self.logger.info("")
        self.logger.info("═" * 60)
        self.logger.info("     SELECCIÓN FINAL — TABLA COMPARATIVA")
        self.logger.info("═" * 60)
        self.logger.info(f"  {'Grupo candidato':<30} {'EMD':<15}")
        self.logger.info("  " + "─" * 45)
        for desc, phi_val in self._candidatos_log:
            marca = " ◀ MÍN" if phi_val == self.memoria_particiones[mip][0] else ""
            self.logger.info(f"  {desc:<30} {phi_val:<15.6f}{marca}")
        self.logger.info("")
        self.logger.info(f"  🏆 Grupo elegido: EMD = {self.memoria_particiones[mip][0]:.6f}")
        self.logger.info(f"  📋 Partición final:\n{fmt_mip}")
        self.logger.info(f"  ⏱  Tiempos: preparación={self._tiempo_preparacion:.4f}s  algoritmo={self._tiempo_algoritmo:.4f}s  total={time.time()-self.sia_tiempo_inicio:.4f}s")

        return Solution(
            estrategia=QNODES_LABEL,
            perdida=self.memoria_particiones[mip][0],
            distribucion_subsistema=self.sia_dists_marginales,
            distribucion_particion=self.memoria_particiones[mip][1],
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=fmt_mip,
            tiempos_parciales={
                "preparacion": self._tiempo_preparacion,
                "algoritmo": self._tiempo_algoritmo,
            },
        )

    def _algorithm_k2(self, vertices):
        return self.algorithm(vertices)

    def _algorithm_kk(self, vertices, k):
        self._tiempo_algoritmo = time.time()
        self.logger.info("")
        self.logger.info("─" * 50)
        self.logger.info(f"  FASE 2: BÚSQUEDA DE k={k}-PARTICIONES (round-robin)")
        self.logger.info("─" * 50)

        dims_ncubos = self.sia_subsistema.dims_ncubos
        indices_ncubos = self.sia_subsistema.indices_ncubos

        grupos_alcance = [[] for _ in range(k)]
        for pos, var in enumerate(indices_ncubos):
            grupos_alcance[pos % k].append(int(var))

        grupos_mecanismo = [[] for _ in range(k)]
        for pos, dim in enumerate(dims_ncubos):
            grupos_mecanismo[pos % k].append(int(dim))

        mejor_emd = INFTY_POS
        mejor_dist = None
        mejor_grupos = None
        mejor_key = None

        for g_idx in range(k):
            futuros_g = np.array(grupos_alcance[g_idx], dtype=np.int8)
            presentes_g = np.array(grupos_mecanismo[g_idx], dtype=np.int8)

            grupos_glob = [futuros_g]
            mecanismos_glob = [presentes_g]

            otros_futuros = np.setdiff1d(indices_ncubos, futuros_g)
            otros_presentes = np.setdiff1d(dims_ncubos, presentes_g)

            if otros_futuros.size > 0:
                grupos_glob.append(otros_futuros)
                mecanismos_glob.append(otros_presentes)

            dist = self._kpartir(grupos_glob, mecanismos_glob)
            emd = emd_efecto(dist, self.sia_dists_marginales)

            g_letras = "".join(ABECEDARY[i] for i in futuros_g) if futuros_g.size > 0 else "∅"
            self.logger.info(f"  • Grupo G{g_idx}: [{g_letras}]  φ = {emd:.6f}")
            self._candidatos_log.append((f"G{g_idx} [{g_letras}]", emd))

            key = tuple([(g_idx, int(n)) for n in futuros_g])
            self.memoria_particiones[key] = (emd, dist)

            if emd < mejor_emd:
                mejor_emd = emd
                mejor_dist = dist
                mejor_grupos = g_idx
                mejor_key = key

        self._tiempo_algoritmo = time.time() - self._tiempo_algoritmo
        self.logger.info(f"  ✅ Búsqueda k={k} completada en {self._tiempo_algoritmo:.4f}s")
        return mejor_key

    def _kpartir(self, grupos, mecanismos):
        subsistema = self.sia_subsistema
        estado_inicial = subsistema.estado_inicial

        nodo_info = {}
        for g_idx, (grupo, mecanismo) in enumerate(zip(grupos, mecanismos)):
            for nodo in grupo:
                nodo_info[int(nodo)] = (g_idx, mecanismo)

        n_ncubos = len(subsistema.ncubos)
        resultado = np.empty(n_ncubos, dtype=np.float32)

        for i, ncubo in enumerate(subsistema.ncubos):
            idx_ncubo = int(ncubo.indice)
            if idx_ncubo in nodo_info:
                g_idx, mecanismo_grupo = nodo_info[idx_ncubo]
                ejes = np.setdiff1d(ncubo.dims, mecanismo_grupo)
            else:
                ejes = np.array([], dtype=np.int8)

            if ejes.size == 0:
                sub_estado = tuple(estado_inicial[j] for j in ncubo.dims)
                prob = float(ncubo.data[sum(
                    (1 << j) * int(estado_inicial[j]) for j in ncubo.dims
                )])
            elif ejes.size == ncubo.dims.size:
                prob = float(np.mean(ncubo.data))
            else:
                cubo_marg = ncubo.marginalizar(ejes)
                if cubo_marg.dims.size == 0:
                    prob = float(cubo_marg.data)
                else:
                    sub_estado = tuple(estado_inicial[j] for j in cubo_marg.dims)
                    bits = sum((1 << j) * int(estado_inicial[j]) for j in cubo_marg.dims)
                    prob = float(cubo_marg.data.ravel()[bits])

            resultado[i] = 1.0 - prob

        return resultado

    def _formatear_kparticion(self, mip, k):
        grupos = {}
        for g_idx, nodo in mip:
            grupos.setdefault(g_idx, []).append(nodo)
        partes = []
        for g in sorted(grupos):
            letras = "".join(ABECEDARY[i] for i in grupos[g])
            partes.append(f"G{g}: [{letras}]")
        return " | ".join(partes)

    def _fmt_parte(self, parte) -> str:
        if isinstance(parte, tuple):
            t, idx = parte
            return ABECEDARY[idx] if t == 1 else ABECEDARY[idx].lower()
        elif isinstance(parte, list):
            return "+".join(self._fmt_parte(p) for p in parte)
        return str(parte)

    def _fmt_vertices(self, vertices_list) -> str:
        return "[" + ", ".join(self._fmt_parte(v) for v in vertices_list) + "]"

    def algorithm(self, vertices: list[tuple[int, int]]):
        self._tiempo_algoritmo = time.time()
        self.logger.info("")
        self.logger.info("─" * 50)
        self.logger.info("  FASE 2: ALGORITMO Q — BÚSQUEDA DE PARTICIONES")
        self.logger.info("─" * 50)

        omegas_origen = np.array([vertices[0]])
        deltas_origen = np.array(vertices[1:])

        vertices_fase = vertices

        omegas_ciclo = omegas_origen
        deltas_ciclo = deltas_origen

        total = len(vertices_fase) - 2
        for i in range(len(vertices_fase) - 2):
            self.logger.info(f"")
            self.logger.info(f"  ═══ FASE {i+1}/{len(vertices_fase)-2} ═══")
            omegas_ciclo = [vertices_fase[0]]
            deltas_ciclo = vertices_fase[1:]
            self.logger.info(f"  Ω inicial: {self._fmt_vertices(omegas_ciclo)}")
            self.logger.info(f"  Δ restantes: {self._fmt_vertices(deltas_ciclo)}")

            emd_particion_candidata = INFTY_POS
            dist_particion_candidata = None

            for j in range(len(deltas_ciclo) - 1):
                emd_local = 1e5
                indice_mip: int

                self.logger.info(f"  ─── Ciclo {j+1}/{len(deltas_ciclo)-1} ───")

                for k in range(len(deltas_ciclo)):
                    delta_actual = deltas_ciclo[k]
                    self.logger.info(f"    • Iteración: evaluando Δ_k = {self._fmt_parte(delta_actual)}")

                    emd_union, emd_delta, dist_marginal_delta = self.funcion_submodular(
                        delta_actual, omegas_ciclo
                    )
                    emd_iteracion = emd_union - emd_delta

                    self.logger.info(f"        emd_union({self._fmt_parte(delta_actual)} ∪ Ω) = {emd_union:.6f}")
                    self.logger.info(f"        emd_delta({self._fmt_parte(delta_actual)})           = {emd_delta:.6f}")
                    self.logger.info(f"        diferencia (costo) = {emd_iteracion:.6f}")

                    if emd_iteracion < emd_local:
                        emd_local = emd_iteracion
                        indice_mip = k
                        self.logger.info(f"        ← nuevo mínimo local")

                    emd_particion_candidata = emd_delta
                    dist_particion_candidata = dist_marginal_delta

                self.logger.info(f"    ✅ Seleccionado Δ_{indice_mip} = {self._fmt_parte(deltas_ciclo[indice_mip])} con diferencia={emd_local:.6f}")

                omegas_ciclo.append(deltas_ciclo[indice_mip])
                deltas_ciclo.pop(indice_mip)
                self.logger.info(f"    Ω actualizado: {self._fmt_vertices(omegas_ciclo)}")
                self.logger.info(f"    Δ restantes:   {self._fmt_vertices(deltas_ciclo)}")

            # Guardar partición candidata de esta fase
            clave_particion = tuple(
                deltas_ciclo[LAST_IDX]
                if isinstance(deltas_ciclo[LAST_IDX], list)
                else deltas_ciclo
            )
            self.memoria_particiones[clave_particion] = emd_particion_candidata, dist_particion_candidata
            self.logger.info(f"  📦 Grupo candidato generado: {self._fmt_vertices(list(clave_particion))}")
            self.logger.info(f"  📊 EMD del grupo candidato: {emd_particion_candidata:.6f}")
            self._candidatos_log.append((f"Fase {i+1} {self._fmt_vertices(list(clave_particion))}", emd_particion_candidata))

            par_candidato = (
                [omegas_ciclo[LAST_IDX]]
                if isinstance(omegas_ciclo[LAST_IDX], tuple)
                else omegas_ciclo[LAST_IDX]
            ) + (
                deltas_ciclo[LAST_IDX]
                if isinstance(deltas_ciclo[LAST_IDX], list)
                else deltas_ciclo
            )

            omegas_ciclo.pop()
            omegas_ciclo.append(par_candidato)

            vertices_fase = omegas_ciclo
            self.logger.info(f"  ➡ Vértices para siguiente fase: {self._fmt_vertices(vertices_fase)}")

        self._tiempo_algoritmo = time.time() - self._tiempo_algoritmo
        self.logger.info(f"  ✅ Algoritmo Q completado en {self._tiempo_algoritmo:.4f}s")

        return min(
            self.memoria_particiones, key=lambda k: self.memoria_particiones[k][0]
        )

    def _fmt_dims(self, dims_list) -> str:
        return ",".join(ABECEDARY[d] for d in sorted(dims_list)) if dims_list else "∅"

    def funcion_submodular(
        self, deltas: Union[tuple, list[tuple]], omegas: list[Union[tuple, list[tuple]]]
    ):
        emd_delta = INFTY_NEG
        temporal = [[], []]

        if isinstance(deltas, tuple):
            d_tiempo, d_indice = deltas
            temporal[d_tiempo].append(d_indice)
        else:
            for delta in deltas:
                d_tiempo, d_indice = delta
                temporal[d_tiempo].append(d_indice)

        copia_delta = self.sia_subsistema

        dims_alcance_delta = temporal[EFECTO]
        dims_mecanismo_delta = temporal[ACTUAL]

        alcance_str = self._fmt_dims(dims_alcance_delta)
        mecanismo_str = self._fmt_dims(dims_mecanismo_delta)
        self.logger.info(f"        ┌─ Evaluación individual (Δ)")
        self.logger.info(f"        │  alcance (marginalizar fuera): {alcance_str}")
        self.logger.info(f"        │  mecanismo (marginalizar en):  {mecanismo_str}")

        particion_delta = copia_delta.bipartir(
            np.array(dims_alcance_delta, dtype=np.int8),
            np.array(dims_mecanismo_delta, dtype=np.int8),
        )
        vector_delta_marginal = particion_delta.distribucion_marginal()
        emd_delta = emd_efecto(vector_delta_marginal, self.sia_dists_marginales)
        self.logger.info(f"        │  dist marginal: {np.array2string(vector_delta_marginal, precision=4)}")
        self.logger.info(f"        │  EMD = {emd_delta:.6f}")
        self.logger.info(f"        └─")

        # Unión #
        for omega in omegas:
            if isinstance(omega, list):
                for omg in omega:
                    o_tiempo, o_indice = omg
                    temporal[o_tiempo].append(o_indice)
            else:
                o_tiempo, o_indice = omega
                temporal[o_tiempo].append(o_indice)

        copia_union = self.sia_subsistema

        dims_alcance_union = temporal[EFECTO]
        dims_mecanismo_union = temporal[ACTUAL]

        alcance_u_str = self._fmt_dims(dims_alcance_union)
        mecanismo_u_str = self._fmt_dims(dims_mecanismo_union)
        self.logger.info(f"        ┌─ Evaluación combinada (Δ ∪ Ω)")
        self.logger.info(f"        │  alcance (marginalizar fuera): {alcance_u_str}")
        self.logger.info(f"        │  mecanismo (marginalizar en):  {mecanismo_u_str}")

        particion_union = copia_union.bipartir(
            np.array(dims_alcance_union, dtype=np.int8),
            np.array(dims_mecanismo_union, dtype=np.int8),
        )
        vector_union_marginal = particion_union.distribucion_marginal()
        emd_union = emd_efecto(vector_union_marginal, self.sia_dists_marginales)
        self.logger.info(f"        │  dist marginal: {np.array2string(vector_union_marginal, precision=4)}")
        self.logger.info(f"        │  EMD = {emd_union:.6f}")
        self.logger.info(f"        └─")

        return emd_union, emd_delta, vector_delta_marginal

    def nodes_complement(self, nodes: list[tuple[int, int]]):
        return list(set(self.vertices) - set(nodes))
