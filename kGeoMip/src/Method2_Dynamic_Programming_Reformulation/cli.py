"""
Interfaz interactiva por terminal para el análisis de la partición óptima.

Uso:
    python cli.py

Flujo:
    1. Ingresar estado inicial (binario)
    2. Ingresar alcance (letras del sistema a conservar en futuro)
    3. Ingresar mecanismo (letras del sistema a conservar en presente)
    4. Ingresar k (número de particiones ≥ 2)
     5. El sistema carga la TPM, ejecuta KGeoMip y muestra la solución.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.controllers.manager import Manager
from src.controllers.strategies.kgeomip import KGeoMip
from src.funcs.base import ABECEDARY, emd_efecto
from src.models.base.application import aplicacion


BANNER = """
  ╔══════════════════════════════════════════════════════╗
  ║   kGeoMip — Análisis de Particiones Óptimas (k-MIP)  ║
  ║   Estrategia Geométrico-Topológica (KGeoMip)         ║
  ╚══════════════════════════════════════════════════════╝
"""


def _letras_sistema(n: int) -> str:
    if n > len(ABECEDARY):
        return f"{len(ABECEDARY)} labels disponibles"
    return "".join(ABECEDARY[i] for i in range(n))


def _letras_a_binario(letras: str, n_bits: int) -> str:
    binario = ["0"] * n_bits
    for letra in letras:
        c = letra.upper()
        if c in ABECEDARY:
            pos = ABECEDARY.index(c)
            if pos < n_bits:
                binario[pos] = "1"
    return "".join(binario)


def _validar_letras(letras: str, n_bits: int) -> tuple[bool, str]:
    if not letras:
        return False, "No puede estar vacío."
    for letra in letras:
        c = letra.upper()
        if c not in ABECEDARY or ABECEDARY.index(c) >= n_bits:
            return False, f"'{letra}' no es válida. Use: {_letras_sistema(n_bits)}"
    return True, ""


def _listar_tpms_disponibles() -> list[int]:
    samples_dirs = [
        Path(__file__).resolve().parent / "src" / ".samples",
        Path(__file__).resolve().parent.parent.parent / "data" / "samples",
    ]
    sizes = set()
    for d in samples_dirs:
        if d.exists():
            for f in d.glob("N*.csv"):
                name = f.stem
                if name[0] == "N" and name[1:].rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ").isdigit():
                    n_str = "".join(c for c in name[1:] if c.isdigit())
                    if n_str:
                        sizes.add(int(n_str))
    return sorted(sizes)


def _elegir_pagina(n: int, sizes_disponibles: dict[int, list[str]]):
    pages = sizes_disponibles.get(n, ["A"])
    if len(pages) == 1:
        return pages[0]
    print(f"\n  Variantes TPM disponibles para N={n}: {', '.join(pages)}")
    while True:
        p = input(f"  Seleccione variante [{pages[0]}]: ").strip().upper()
        if not p:
            return pages[0]
        if p in pages:
            return p
        print(f"  Variante inválida. Opciones: {', '.join(pages)}")


def _scanner_tpms() -> dict[int, list[str]]:
    samples_dirs = [
        Path(__file__).resolve().parent / "src" / ".samples",
        Path(__file__).resolve().parent.parent.parent / "data" / "samples",
    ]
    result: dict[int, list[str]] = {}
    for d in samples_dirs:
        if d.exists():
            for f in d.glob("N*.csv"):
                stem = f.stem
                n_str = "".join(c for c in stem[1:] if c.isdigit())
                pag = "".join(c for c in stem[1:] if c.isalpha())
                if n_str and pag:
                    n = int(n_str)
                    result.setdefault(n, []).append(pag)
    return {k: sorted(v) for k, v in result.items()}


def ejecutar_interactivo():
    print(BANNER)

    tpms = _scanner_tpms()
    if not tpms:
        print("  ERROR: No se encontraron archivos TPM en data/samples/ ni src/.samples/")
        sys.exit(1)

    print(f"  TPMs disponibles: N{', N'.join(str(k) for k in sorted(tpms))}")
    print()

    estado_inicial = input("  Estado inicial (binario, ej: 1000000000000000000): ").strip()
    if not estado_inicial or not all(c in "01" for c in estado_inicial):
        print("  ERROR: debe ingresar un string binario (solo 0s y 1s).")
        sys.exit(1)

    n = len(estado_inicial)
    if n not in tpms:
        print(f"\n  ⚠ No hay TPM para N={n}. TPMs disponibles: N{', N'.join(str(k) for k in sorted(tpms))}")
        sys.exit(1)

    pagina = _elegir_pagina(n, tpms)
    aplicacion.pagina_sample_network = pagina

    letras_sistema = _letras_sistema(n)
    print(f"\n  Sistema: {n} variables  →  {letras_sistema}")
    print()

    while True:
        raw = input(f"  Alcance (futuro) — letras a conservar [{letras_sistema}]: ").strip().upper()
        valido, err = _validar_letras(raw, n)
        if valido:
            alcance_letras = raw
            break
        print(f"  ERROR: {err}")

    while True:
        raw = input(f"  Mecanismo (presente) — letras a conservar [{letras_sistema}]: ").strip().upper()
        valido, err = _validar_letras(raw, n)
        if valido:
            mecanismo_letras = raw
            break
        print(f"  ERROR: {err}")

    while True:
        raw = input("  k (número de particiones, ≥ 2) [2]: ").strip()
        if not raw:
            k = 2
            break
        try:
            k = int(raw)
            if k < 2:
                print("  ERROR: k debe ser ≥ 2.")
                continue
            break
        except ValueError:
            print("  ERROR: debe ingresar un número entero.")

    print()
    print("  ──────────────────────────────────────────────────")
    print("  PARÁMETROS")
    print("  ──────────────────────────────────────────────────")
    print(f"    Estado inicial:  {estado_inicial}  (N={n})")
    print(f"    Variante TPM:    N{n}{pagina}.csv")
    print(f"    Alcance:         {alcance_letras}")
    print(f"    Mecanismo:       {mecanismo_letras}")
    print(f"    k:               {k}")
    print()

    condicion = "1" * n
    alcance_bin = _letras_a_binario(alcance_letras, n)
    mecanismo_bin = _letras_a_binario(mecanismo_letras, n)

    if "1" not in alcance_bin:
        print("  ERROR: alcance debe contener al menos una variable.")
        sys.exit(1)
    if "1" not in mecanismo_bin:
        print("  ERROR: mecanismo debe contener al menos una variable.")
        sys.exit(1)

    print("  ──────────────────────────────────────────────────")
    print("  INICIALIZANDO ANÁLISIS...")
    print("  ──────────────────────────────────────────────────")
    print()

    try:
        gestor = Manager(estado_inicial)
        ruta_tpm = gestor.tpm_filename
        print(f"  Cargando TPM: {ruta_tpm}")
        if not ruta_tpm.exists():
            print(f"  ERROR: no se encontró {ruta_tpm}")
            sys.exit(1)

        tpm = np.genfromtxt(ruta_tpm, delimiter=",")
        print(f"  TPM cargada: {tpm.shape[0]} estados × {tpm.shape[1]} nodos")
        print()

        analizador = KGeoMip(gestor)
        solucion = analizador.aplicar_estrategia(
            condicion=condicion,
            alcance=alcance_bin,
            mecanismo=mecanismo_bin,
            tpm=tpm,
            k=k,
        )

        print(solucion)

    except FileNotFoundError as e:
        print(f"\n  ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n  ERROR durante el análisis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    ejecutar_interactivo()
