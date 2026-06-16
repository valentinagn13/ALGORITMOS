# Proyecto-20261

Este repositorio contiene la implementacion de kGeoMip para el analisis de MIP/IIT:

1. `kGeoMip/src/Method2_Dynamic_Programming_Reformulation`

## Requisitos

- Linux (probado en Ubuntu)
- Python 3.11+ (hay entornos locales con 3.12)
- `uv` instalado

Instalacion de `uv` (si no lo tienes):

```bash
pip install uv
```

## Estructura Rapida

- `kGeoMip/src/Method1_GPU_Accelerated/`: procesamiento por lotes desde Excel.
- `kGeoMip/src/Method2_Dynamic_Programming_Reformulation/`: procesamiento por lotes desde Excel.
- `kGeoMip/src/Method2_Dynamic_Programming_Reformulation/src/.samples/`: datasets TPM `N*.csv`.
- `kGeoMip/results/`: archivos Excel de entrada/salida para Method2.

## 2) Ejecutar Method2_Dynamic_Programming_Reformulation

### Dependencias

Desde `kGeoMip/src/Method2_Dynamic_Programming_Reformulation/`:

```bash
cd kGeoMip/src/Method2_Dynamic_Programming_Reformulation
uv sync
```

### Ejecucion

```bash
uv run exec.py
```

### Entrada por defecto

- Excel entrada: `kGeoMip/results/Pruebas_Metodo2.xlsx`
- Hoja usada actualmente: indice `8`
- Columna subsistema: `B`

### Salida por defecto

- Excel salida: `kGeoMip/results/resultados_Geometric.xlsx`
