#!/usr/bin/env python3
import sys
from pathlib import Path

geo_src = Path("kGeoMip/src/Method2_Dynamic_Programming_Reformulation").absolute()
sys.path.insert(0, str(geo_src))

from src.controllers.manager import Manager

def main():
    gestor = Manager(estado_inicial="0"*10)
    # Intenta sin argumentos extra
    nombre_archivo = gestor.generar_red(dimensiones=10)
    if nombre_archivo:
        print(f"✅ Red generada: {nombre_archivo}")
    else:
        print("❌ No se generó.")

if __name__ == "__main__":
    main()