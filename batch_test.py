#!/usr/bin/env python3
"""
Ejecuta una batería de pruebas para el análisis de particiones (GeometricSIA).
Uso: python batch_tests.py [k]
Ejemplo: python batch_tests.py 5
"""

import sys
import os
import re
from pathlib import Path

# Añadir rutas necesarias para importar los módulos del proyecto
ROOT = Path(__file__).resolve().parent
METHOD2_ROOT = ROOT / "GeoMIP" / "src" / "Method2_Dynamic_Programming_Reformulation"
sys.path.insert(0, str(METHOD2_ROOT))

# Importar funciones y clases necesarias
from src.models.base.application import aplicacion
from cli import _letras_a_binario
from src.controllers.manager import Manager
from src.controllers.strategies.geometric import GeometricSIA
import numpy as np

def clean_ansi(text: str) -> str:
    """Elimina códigos de escape ANSI."""
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

def run_test(estado, alcance_letras, mecanismo_letras, k, pagina='A'):
    """
    Ejecuta una prueba de GeometricSIA y devuelve (particion, perdida, tiempo)
    """
    # Configurar página TPM
    aplicacion.pagina_sample_network = pagina

    n = len(estado)
    alcance_bin = _letras_a_binario(alcance_letras.upper(), n)
    mecanismo_bin = _letras_a_binario(mecanismo_letras.upper(), n)
    condicion = "1" * n

    # Cargar TPM
    gestor = Manager(estado)
    ruta_tpm = gestor.tpm_filename
    tpm = np.genfromtxt(ruta_tpm, delimiter=",")

    # Instanciar estrategia
    analizador = GeometricSIA(gestor)

    # Ejecutar
    resultado_raw = analizador.aplicar_estrategia(
        condicion=condicion,
        alcance=alcance_bin,
        mecanismo=mecanismo_bin,
        tpm=tpm,
        k=k
    )
    texto_limpio = clean_ansi(str(resultado_raw))
    lineas = texto_limpio.splitlines()

    # Extraer datos (mismo método que en la GUI)
    particion = ""
    perdida = ""
    tiempo = ""

    # Detectar formato (G0: o barras)
    formato_g = any("G0:" in line and "G1:" in line for line in lineas)
    formato_barras = any("Mejor Bi-Partición" in line for line in lineas)

    if formato_g:
        for line in lineas:
            if "G0:" in line and "G1:" in line:
                if "Mejor" in line:
                    particion = line.split("Mejor Bi-Partición:")[-1].strip()
                else:
                    particion = line.strip()
                break
    elif formato_barras:
        # Convertir formato de barras a G0: | G1:
        for i, line in enumerate(lineas):
            if "Mejor Bi-Partición" in line:
                for j in range(i+1, min(i+5, len(lineas))):
                    siguiente = lineas[j].strip()
                    if "|" in siguiente and "||" in siguiente:
                        partes = siguiente.split("||")
                        grupo1_raw = partes[0].replace("|", "").strip()
                        grupo2_raw = partes[1].replace("|", "").strip() if len(partes) > 1 else ""
                        if grupo1_raw:
                            elementos1 = [e.strip() for e in grupo1_raw.split(",")]
                            grupo1 = f"[{''.join(elementos1)}]"
                        else:
                            grupo1 = "[]"
                        if grupo2_raw and grupo2_raw != "∅":
                            elementos2 = [e.strip() for e in grupo2_raw.split(",")]
                            grupo2 = f"[{''.join(elementos2)}]"
                        else:
                            grupo2 = "[∅]"
                        particion = f"G0: {grupo1} | G1: {grupo2}"
                        break
                break

    # Buscar pérdida
    for line in lineas:
        if "Perdida mínima" in line or "φ" in line:
            match = re.search(r"([0-9]+\.[0-9]+)", line)
            if match:
                perdida = match.group(1)
                break

    # Buscar tiempo
    for line in lineas:
        if "Segundos:" in line:
            parts = line.split("Segundos:")
            if len(parts) > 1:
                tiempo = parts[1].strip().split()[0]
                break
    if not tiempo:
        for i, line in enumerate(lineas):
            if "Tiempos de ejecución:" in line and i+1 < len(lineas):
                next_line = lineas[i+1]
                if "Segundos:" in next_line:
                    parts = next_line.split("Segundos:")
                    if len(parts) > 1:
                        tiempo = parts[1].strip().split()[0]
                    break

    # Convertir punto a coma para compatibilidad con Google Sheets
    perdida = perdida.replace('.', ',') if perdida else ""
    tiempo = tiempo.replace('.', ',') if tiempo else ""

    return particion, perdida, tiempo

def main():
    # k se puede pasar como argumento, por defecto 5
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    print(f"Ejecutando pruebas con k = {k}\n", file=sys.stderr)

    # Estado inicial fijo (20 bits)
    estado = "10000000000000000000"

    # Lista de pruebas: (alcance, mecanismo)
    pruebas = [
        ("ABCDEFGHIJKLMNOPQRST", "ABCDEFGHIJKLMNOPQRST"),  # 1
        ("ABCDEFGHIJKLMNOPQRST", "ABCDEFGHIJKLMNOPQRS"),   # 2
        ("ABCDEFGHIJKLMNOPQRST", "BCDEFGHIJKLMNOPQRST"),   # 3
        # ("ABCDEFGHIJKLMNOPQRST", "BCDEFGHIJKLMNOPQRS"),    # 4
        # ("ABCDEFGHIJKLMNOPQRST", "ABDEGHJKMNPQST"),        # 5
        # ("ABCDEFGHIJKLMNOPQRST", "ACEGIKMOQS"),            # 6
        # ("ABCDEFGHIJKLMNOPQRST", "BDFHJLNPRT"),            # 7
        # ("ABCDEFGHIJKLMNOPQRS",  "ABCDEFGHIJKLMNOPQRST"),  # 8
        # ("ABCDEFGHIJKLMNOPQRS",  "ABCDEFGHIJKLMNOPQRS"),   # 9
        # ("ABCDEFGHIJKLMNOPQRS",  "BCDEFGHIJKLMNOPQRST"),   # 10
        # ("ABCDEFGHIJKLMNOPQRS",  "BCDEFGHIJKLMNOPQRS"),    # 11
        # ("ABCDEFGHIJKLMNOPQRS",  "ABDEGHJKMNPQST"),        # 12
        # ("ABCDEFGHIJKLMNOPQRS",  "ACEGIKMOQS"),            # 13
        # ("ABCDEFGHIJKLMNOPQRS",  "BDFHJLNPRT"),            # 14
        # ("BCDEFGHIJKLMNOPQRST",  "ABCDEFGHIJKLMNOPQRST"),  # 15
        # ("BCDEFGHIJKLMNOPQRST",  "ABCDEFGHIJKLMNOPQRS"),   # 16
        # ("BCDEFGHIJKLMNOPQRST",  "BCDEFGHIJKLMNOPQRST"),   # 17
        # ("BCDEFGHIJKLMNOPQRST",  "BCDEFGHIJKLMNOPQRS"),    # 18
        # ("BCDEFGHIJKLMNOPQRST",  "ABDEGHJKMNPQST"),        # 19
        # ("BCDEFGHIJKLMNOPQRST",  "ACEGIKMOQS"),            # 20
        # ("BCDEFGHIJKLMNOPQRST",  "BDFHJLNPRT"),            # 21
        # ("BCDEFGHIJKLMNOPQRS",   "ABCDEFGHIJKLMNOPQRST"),  # 22
        # ("BCDEFGHIJKLMNOPQRS",   "ABCDEFGHIJKLMNOPQRS"),   # 23
        # ("BCDEFGHIJKLMNOPQRS",   "BCDEFGHIJKLMNOPQRST"),   # 24
        # ("BCDEFGHIJKLMNOPQRS",   "BCDEFGHIJKLMNOPQRS"),    # 25
        # ("BCDEFGHIJKLMNOPQRS",   "ABDEGHJKMNPQST"),        # 26
        # ("BCDEFGHIJKLMNOPQRS",   "ACEGIKMOQS"),            # 27
        # ("BCDEFGHIJKLMNOPQRS",   "BDFHJLNPRT"),            # 28
        # ("ABDEGHJKMNPQST",       "ABCDEFGHIJKLMNOPQRST"),  # 29
        # ("ABDEGHJKMNPQST",       "ABCDEFGHIJKLMNOPQRS"),   # 30
        # ("ABDEGHJKMNPQST",       "BCDEFGHIJKLMNOPQRST"),   # 31
        # ("ABDEGHJKMNPQST",       "BCDEFGHIJKLMNOPQRS"),    # 32
        # ("ABDEGHJKMNPQST",       "ABDEGHJKMNPQST"),        # 33
        # ("ABDEGHJKMNPQST",       "ACEGIKMOQS"),            # 34
        # ("ABDEGHJKMNPQST",       "BDFHJLNPRT"),            # 35
        # ("ACEGIKMOQS",           "ABCDEFGHIJKLMNOPQRST"),  # 36
        # ("ACEGIKMOQS",           "ABCDEFGHIJKLMNOPQRS"),   # 37
        # ("ACEGIKMOQS",           "BCDEFGHIJKLMNOPQRST"),   # 38
        # ("ACEGIKMOQS",           "BCDEFGHIJKLMNOPQRS"),    # 39
        # ("ACEGIKMOQS",           "ABDEGHJKMNPQST"),        # 40
        # ("ACEGIKMOQS",           "ACEGIKMOQS"),            # 41
        # ("ACEGIKMOQS",           "BDFHJLNPRT"),            # 42
        # ("BDFHJLNPRT",           "ABCDEFGHIJKLMNOPQRST"),  # 43
        # ("BDFHJLNPRT",           "ABCDEFGHIJKLMNOPQRS"),   # 44
        # ("BDFHJLNPRT",           "BCDEFGHIJKLMNOPQRST"),   # 45
        # ("BDFHJLNPRT",           "BCDEFGHIJKLMNOPQRS"),    # 46
        # ("BDFHJLNPRT",           "ABDEGHJKMNPQST"),        # 47
        # ("BDFHJLNPRT",           "ACEGIKMOQS"),            # 48
        # ("BDFHJLNPRT",           "BDFHJLNPRT"),            # 49
        # ("BCDEFGJKLMNO",         "BCDEFGHIJKLMNO"),        # 50
    ]

    # Lista para almacenar las líneas de salida
    salidas = []

    # Ejecutar cada prueba
    for idx, (alc, mec) in enumerate(pruebas, start=1):
        print(f"\n--- Prueba {idx} ---", file=sys.stderr)
        print(f"Alcance: {alc}, Mecanismo: {mec}, k={k}", file=sys.stderr)
        try:
            particion, perdida, tiempo = run_test(estado, alc, mec, k, pagina='A')
            # Formato CSV con tabuladores (mismo que se pegará al final)
            linea = f"{particion}\t{perdida}\t{tiempo}"
            salidas.append(linea)
            # Mostrar en vivo también
            print(linea)
        except Exception as e:
            print(f"ERROR en prueba {idx}: {e}", file=sys.stderr)
            salidas.append("\t\t")  # línea vacía para mantener formato

    # Al final, imprimir todas las salidas juntas
    print("\n" + "="*60, file=sys.stderr)
    print("SALIDAS:", file=sys.stderr)
    print("="*60, file=sys.stderr)
    for linea in salidas:
        print(linea)

if __name__ == "__main__":
    main()