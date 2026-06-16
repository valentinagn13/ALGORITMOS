# Manual Técnico — Proyecto kGeoMip

## 1. Descripción General

kGeoMip es un framework para resolver el problema de la Mejor K-Particion (MIP) en el contexto de la Teoría de Información Integrada (IIT). Dado un sistema representado como una matriz de transición de probabilidades (TPM), el algoritmo divide los nodos en k grupos de forma que se minimice la pérdida de información integrada (φ, phi).

El proyecto implementa una estrategia geométrico-topológica que construye un hipercubo de estados, calcula costos de transición entre ellos, identifica candidatos a partición de forma eficiente y, para k>2, usa Simulated Annealing para refinar la búsqueda.

## 2. Arquitectura del Sistema

El proyecto sigue una arquitectura en capas con 5 niveles:

```
┌──────────────────────────────────────────────────┐
│  PUNTO DE ENTRADA  (gui, cli, batch, test)       │
├──────────────────────────────────────────────────┤
│  CONTROLADORES  (Manager, KGeoMip, BruteForce)    │
├──────────────────────────────────────────────────┤
│  MODELOS  (System, NCube, Solution, SIA)          │
├──────────────────────────────────────────────────┤
│  FUNCIONES  (EMD, formatos, generadores)          │
├──────────────────────────────────────────────────┤
│  CONSTANTES  (rutas, etiquetas, errores)          │
└──────────────────────────────────────────────────┘
```

Las capas superiores dependen de las inferiores, nunca al revés. Los middlewares (logging, profiling) cruzan todas las capas.

## 3. Estructura de Directorios

```
ALGORITMOS/
├── gui.py                           Interfaz gráfica (Tkinter)
├── batch_test.py                    Batería de pruebas rápida
├── generar_red.py                   Generador de TPM sintéticas
├── setup.sh                         Script de instalación (Linux)
├── requirements.txt                 Dependencias Python
├── README.md                        Documentación general
│
├── kGeoMip/
│   ├── data/
│   │   └── creation.py              Generador avanzado de TPM
│   │
│   └── src/Method2_Dynamic_Programming_Reformulation/
│       ├── exec.py                  Lanzador principal
│       ├── cli.py                   Terminal interactiva
│       ├── test_kpartir.py          Suite de tests unitarios
│       ├── pyproject.toml           Configuración uv
│       │
│       └── src/
│           ├── .samples/            TPMs de muestra (N*.csv)
│           │
│           ├── controllers/
│           │   ├── manager.py       Gestor de rutas y TPMs
│           │   └── strategies/
│           │       ├── kgeomip.py   Estrategia KGeoMip
│           │       ├── force.py     Estrategia BruteForce
│           │       └── phi.py       Estrategia PyPhi
│           │
│           ├── models/
│           │   ├── base/
│           │   │   ├── sia.py       Clase base abstracta SIA
│           │   │   └── application.py  Config singleton
│           │   ├── core/
│           │   │   ├── system.py    Sistema de NCubos
│           │   │   ├── ncube.py     Cubo n-dimensional
│           │   │   └── solution.py  Resultado del análisis
│           │   └── enums/
│           │       ├── notation.py  Notación (little-endian, etc)
│           │       └── distance.py  Métricas de distancia
│           │
│           ├── funcs/
│           │   ├── base.py          EMD, ABECEDARY, utilidades
│           │   ├── format.py        Formateo de particiones
│           │   └── system.py        Generadores combinatorios
│           │
│           ├── middlewares/
│           │   ├── slogger.py       Logger seguro con colores
│           │   └── profile.py       Profiler con pyinstrument
│           │
│           └── constants/
│               ├── base.py          Constantes generales
│               ├── models.py        Etiquetas de estrategias
│               └── error.py         Mensajes de error
│
├── src/.samples/                    TPMs de respaldo
├── resultados/                      Gráficos y análisis
├── docs/                            Documentación
└── .logs/                           Archivos de log
```

## 4. Instalación y Configuración

### 4.1 Requisitos

- Python 3.11 o superior
- Sistema operativo: Windows o Linux
- Gestor de paquetes uv (recomendado) o pip

### 4.2 Instalación en Linux

```bash
bash setup.sh
source .venv/bin/activate
```

Esto crea un entorno virtual, instala dependencias con pip y sincroniza los subproyectos con uv.

### 4.3 Instalación en Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd kGeoMip\src\Method2_Dynamic_Programming_Reformulation
uv sync
cd ..\..\..
```

### 4.4 Dependencias Principales

- numpy >= 1.26.4
- scipy >= 1.17.0
- pyphi >= 1.2.0
- pyinstrument >= 5.1.2
- pandas >= 2.3.3
- openpyxl >= 3.1.5
- colorama >= 0.4.6

## 5. Guía de Uso

### 5.1 Interfaz Gráfica (GUI)

```bash
python gui.py
```

Se abre una ventana con los siguientes parámetros:

- **Estado inicial**: Cadena binaria que representa el estado del sistema en t=0. Ejemplo: `1000000000` (nodo 0 encendido, los demás apagados).
- **Alcance (futuro)**: Letras mayúsculas indicando qué nodos se consideran en t+1. Ejemplo: `ABCDEFGHIJ`.
- **Mecanismo (presente)**: Letras mayúsculas para nodos en t. Ejemplo: `ABCDEFGHIJ`.
- **k (particiones)**: Número de grupos (mínimo 2).
- **SA habilitado**: Activa Simulated Annealing cuando k > 2.
- **SA max_iter / max_time**: Límites del SA.
- **Variante TPM**: Letra de página del dataset (A, B, C...).
- **Estrategia**: Actualmente solo KGeoMip.

Al presionar "Ejecutar", la barra de progreso se activa mientras el algoritmo trabaja. El panel de salida muestra:

1. La mejor k-partición encontrada
2. El valor de φ (pérdida mínima)
3. El tiempo de ejecución

### 5.2 Terminal Interactiva (CLI)

```bash
cd kGeoMip/src/Method2_Dynamic_Programming_Reformulation
python cli.py
```

O desde el lanzador:

```bash
cd kGeoMip/src/Method2_Dynamic_Programming_Reformulation
python exec.py --cli
```

El asistente guía paso a paso:

1. Detecta TPMs disponibles y muestra sus tamaños
2. Solicita estado inicial, alcance, mecanismo y k
3. Ejecuta el análisis y muestra el resultado con colores

### 5.3 Modo Batch por Excel

```bash
cd kGeoMip/src/Method2_Dynamic_Programming_Reformulation
python exec.py
```

Este modo lee un archivo Excel de entrada (por defecto busca en `kGeoMip/results/Pruebas_Metodo2.xlsx`). Cada fila contiene un par alcance|mecanismo.

Procesa todas las pruebas en paralelo con un tiempo máximo de 1 hora por prueba usando multiprocessing. Los resultados se guardan en un archivo Excel de salida con columnas: iteración, alcance, mecanismo, partición, pérdida φ y tiempo.

### 5.4 Batería de Pruebas Rápidas

```bash
python batch_test.py [k]
```

Ejecuta 9 combinaciones predefinidas de alcance y mecanismo sobre la red N10A. El parámetro k es opcional (por defecto 5). Útil para pruebas de rendimiento rápidas.

### 5.5 Tests Unitarios

```bash
cd kGeoMip/src/Method2_Dynamic_Programming_Reformulation
python -m pytest test_kpartir.py -v
```

Suite que valida tres niveles:

- **Nivel 1**: Equivalencia numérica de kpartir(k=2) vs bipartir()
- **Nivel 2**: Corrección matemática para k>2 (valores en [0,1], longitudes correctas, nodos huérfanos)
- **Nivel 3**: Regresión de rendimiento (kpartir no debe ser significativamente más lento)

### 5.6 Generar Nuevas Redes

```bash
python generar_red.py
```

Genera una TPM sintética determinista de 10 nodos y la guarda en el directorio de muestras.

Para control más fino:

```bash
python kGeoMip/data/creation.py
```

## 6. Formato de TPM (Datos de Entrada)

Las TPM son archivos CSV en el directorio `.samples/` con el formato `N{n}{pagina}.csv`.

- **n**: Número de nodos (ej: N10A.csv = 10 nodos, página A)
- Cada fila representa un estado en t (2^n filas para sistema completo)
- Cada columna representa la probabilidad del nodo i en t+1
- Valores: 0 o 1 para sistemas deterministas, [0,1] para estocásticos
- Delimitador: coma (,)

Ejemplo (N3A.csv, 8 filas × 3 columnas):

```
0,0,0
0,0,1
0,1,0
...
```

## 7. Arquitectura del Algoritmo

### 7.1 Flujo Principal

El método `KGeoMip.aplicar_estrategia()` ejecuta 5 fases:

**Fase 1 — Preparación del Subsistema**

1. Carga la TPM y construye un `System` con `NCube` por nodo
2. Condiciona el sistema al estado de fondo (fondo = bits en 0)
3. Resta dimensiones de alcance y mecanismo para obtener el subsistema
4. Calcula la distribución marginal de referencia (P(OFF) para cada NCubo)

**Fase 2 — Construcción del Hipercubo de Estados**

1. Genera todos los estados binarios alcanzables desde el estado inicial
2. Para cada nivel de distancia de Hamming, calcula costos de transición
3. Fórmula de costo: `tx(i,j) = γ · |X[i] - X[j]|` donde `γ = 1/2^dH(i,j)`

**Fase 3 — Identificación de Candidatos**

Para k=2:
- Heurística "one-removed": prueba quitando cada nodo del alcance
- Estados de nivel intermedio del hipercubo

Para k>2:
- Round-robin: ordena nodos por costo, asigna en ronda a cada grupo
- Combinaciones de estados de nivel

Cada candidato se evalúa con `kpartir()`:
1. Distribuye los NCubos entre los k grupos según sus futuros
2. Para cada NCubo, marginaliza sobre los ejes fuera de su grupo
3. Calcula la distribución resultante (1 - P(ON) para cada NCubo)
4. Mide EMD entre distribución resultante y la de referencia

**Fase 4 — Simulated Annealing (k>2)**

1. Parte de la mejor partición heurística
2. Itera moviendo un futuro aleatorio a otro grupo
3. Acepta si mejora φ o con probabilidad exp(-Δ/T)
4. Enfría: T = α · T por iteración

**Fase 5 — Selección Final**

1. Recupera la partición con mínima φ de la memoria
2. Construye y retorna un objeto `Solution`

### 7.2 Estrategias Alternativas

- **BruteForce**: Exhaustivo (solo k=2). Evalúa todas las biparticiones posibles.
- **Phi**: Wrapper de la librería externa PyPhi para comparación.

### 7.3 Métrica de Distancia

La métrica por defecto es `emd-effect` (Earth Mover's Distance sobre el efecto):

```
EMD(u, v) = Σ|u_i - v_i|
```

Es la distancia L1 entre dos distribuciones de probabilidad. También soporta `emd-cause` (con matriz de distancia Hamming), Manhattan y Euclidiana.

## 8. Modelo de Datos

### 8.1 NCube

Un NCube representa la TPM de un nodo como un tensor binario n-dimensional.

- `indice`: Identificador del nodo (0..n-1)
- `dims`: Dimensiones del cubo (ejes que representan los nodos causales)
- `data`: Tensor de forma (2,) × dims.size con valores de probabilidad

Operaciones:
- `condicionar(indices, estado)`: Slice del tensor a lo largo de ejes especificados
- `marginalizar(ejes)`: Promedio sobre ejes especificados

### 8.2 System

Contenedor de NCubos que representa el sistema completo.

Operaciones:
- `condicionar(indices)`: Fija dimensiones de fondo al estado inicial
- `substraer(alcance, mecanismo)`: Extrae subsistema por dimensiones
- `bipartir(alcance, mecanismo)`: Crea bipartición
- `distribucion_marginal()`: Calcula P(OFF) para cada NCubo

### 8.3 Solution

Contenedor del resultado del análisis:

- `estrategia`: Nombre de la estrategia usada
- `perdida`: Valor de φ (pérdida mínima)
- `particion`: Representación textual de la partición
- `distribucion_subsistema`: Distribución marginal del subsistema
- `distribucion_particion`: Distribución de la mejor partición
- `tiempo_ejecucion`: Tiempo total en segundos
- `tiempos_parciales`: Desglose por fase
- `grupos_futuro` y `grupos_presente`: Listas de etiquetas por grupo

### 8.4 Manager

Resuelve rutas de archivos TPM. Estrategia de búsqueda:

1. Variable de entorno `GEOMIP_SAMPLES_DIR`
2. `kGeoMip/.../src/.samples/` (directorio principal)
3. `kGeoMip/.../.samples/` (fallback)
4. Raíz del proyecto `src/.samples/` (respaldo)
5. Raíz del proyecto `data/samples/` (respaldo legacy)

### 8.5 Application (Singleton)

Configuración global del proyecto:

- `pagina_sample_network`: Letra de página de TPM
- `semilla_numpy`: Semilla para generación de redes
- `notacion`: Tipo de notación endian
- `distancia_metrica`: Métrica de distancia
- `profiler_habilitado`: Activa/desactiva profiling

## 9. Middlewares

### 9.1 SafeLogger

Logger con formato de color y soporte para caracteres especiales.

- Niveles: DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL
- Salida a consola con colores (vía colorama) y archivo
- Modo silencioso para batch (`SafeLogger.silent = True`)

### 9.2 ProfilingManager

Integración con pyinstrument para profiling.

- Sesiones con nombre (identifican ejecuciones)
- Salida en HTML con reportes interactivos
- Decorador `@profile(context={...})` para métodos específicos

## 10. Convenciones de Código

- **Notación**: little-endian por defecto (bit 0 = nodo A)
- **ABECEDARY**: 40 letras (A..Z, AA..AN) para etiquetar nodos
- **Estado inicial**: Cadena binaria donde '1' = activo
- **Alcance/Mecanismo**: Letras mayúsculas (ABECEDARY) indicando nodos incluidos
- **φ**: Valor de pérdida (menor = mejor partición)

## 11. Solución de Problemas

| Problema | Causa | Solución |
|---|---|---|
| "TPM no encontrada" | Archivo N{n}{pag}.csv no existe | Generar red con `generar_red.py` o copiar TPM a `.samples/` |
| Error de encoding φ | Windows cp1252 | Usar `phi` en lugar de `φ` en prints |
| Tests de rendimiento fallan | n muy pequeño (<10) | El beneficio real aparece con n>10 |
| ImportError en gui.py | Path no insertado | Ejecutar desde raíz del proyecto |
| "No module named pytest" | pytest no instalado | `pip install pytest` |
