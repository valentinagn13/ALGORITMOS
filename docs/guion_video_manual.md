# Guion para Video Manual de Usuario — Proyecto kGeoMip

---

## Escena 1: Introducción (1 minuto)

**Visual:** Mostrar el proyecto abierto en VSCode o terminal, con el árbol de directorios.

**Voz en off:**
"Este proyecto implementa **kGeoMip**, una estrategia geométrico-topológica para encontrar la **Mejor K-Partición** de un sistema. El problema viene de la Teoría de Información Integrada (IIT): dado un sistema representado como una matriz de transición de probabilidades (TPM), queremos dividir sus nodos en `k` grupos de forma que se minimice la *pérdida de información integrada* (φ, phi).

El proyecto ofrece varias formas de interactuar: una **interfaz gráfica (GUI)**, una **terminal interactiva (CLI)**, un **modo batch por Excel**, un **script de pruebas rápido**, y un **generador de gráficos comparativos**. En este video veremos cada una."

---

## Escena 2: Requisitos y configuración (1 minuto)

**Visual:** Terminal, ejecutando setup.

**Texto en pantalla:** `bash setup.sh`

**Voz en off:**
"Antes de empezar, necesitamos Python 3.11 o superior. El archivo `setup.sh` hace todo automáticamente: crea un entorno virtual, instala las dependencias con `uv` y sincroniza los subproyectos."

**Comandos a mostrar:**
```bash
cd projecto-analisis-20261
bash setup.sh
source venv/bin/activate
```

**Voz:**
"Ejecutamos `bash setup.sh`. Al finalizar, activamos el entorno virtual con `source venv/bin/activate`. Todo listo."

---

## Escena 3: Interfaz Gráfica — GUI (3 minutos)

**Visual:** Ventana de la GUI apareciendo.

**Comando:**
```bash
python gui.py
```

**Voz:**
"La GUI es la forma más amigable. La lanzamos con `python gui.py`. Se abre una ventana con todos los parámetros pre‑cargados con valores por defecto."

**Recorrer cada campo (señalar con cursor):**

1. **Estado inicial:** Una cadena binaria. Ej: `1000000000` — el primer nodo encendido, los demás apagados.
2. **Alcance (futuro):** Letras mayúsculas que indican qué nodos consideramos en el instante *t+1*. Ej: `ABCDEFGHIJ`.
3. **Mecanismo (presente):** Letras mayúsculas para los nodos en el instante *t*. Ej: `ABCDEFGHIJ`.
4. **k (particiones):** Número de grupos en los que dividir el sistema. Mínimo 2.
5. **SA habilitado / max_iter / max_time:** Cuando `k > 2`, aparecen parámetros de *Simulated Annealing*. Por defecto 1700 iteraciones y 25 segundos máximo.
6. **Variante TPM:** Página del dataset (A, B, C...). Cada letra es una red distinta del mismo tamaño.
7. **Estrategia:** Siempre KGeoMip (única disponible).

**Acción:** Hacer clic en "Ejecutar".

**Voz:**
"Presionamos **Ejecutar**. La barra de progreso se mueve mientras el algoritmo trabaja. Al terminar, en el panel vemos:
- La **mejor k-partición** encontrada (los grupos de nodos).
- El valor de **φ (pérdida)** — mientras más bajo, mejor.
- El **tiempo de ejecución** en segundos."

**Señalar la línea final:**
"Al final aparece una línea con pestañas que resume el resultado, lista para copiar y pegar en una hoja de cálculo."

---

## Escena 4: Terminal Interactiva — CLI (2 minutos)

**Visual:** Terminal.

**Comando:**
```bash
cd kGeoMip/src/Method2_Dynamic_Programming_Reformulation
uv run exec.py --cli
```

**Voz:**
"La CLI es un asistente paso a paso. Ejecutamos `uv run exec.py --cli` (o `python cli.py`)."

**Mostrar cada paso:**
1. Aparece un banner con el nombre del proyecto.
2. **Lista de TPMs disponibles:** Muestra los tamaños de red detectados.
3. **Ingresar estado inicial:** Escribimos `1000000000`.
4. **Seleccionar página:** Elegimos `A`.
5. **Ingresar alcance:** Letras del futuro.
6. **Ingresar mecanismo:** Letras del presente.
7. **Ingresar k:** Por ejemplo `3`.
8. El sistema ejecuta y muestra el resultado con colores.

**Voz:**
"El asistente es ideal cuando trabajamos en una terminal sin entorno gráfico, por ejemplo en un servidor remoto."

---

## Escena 5: Script de pruebas batch (1 minuto)

**Visual:** Terminal.

**Comando:**
```bash
python batch_test.py 5
```

**Voz:**
"El script `batch_test.py` ejecuta 9 combinaciones predefinidas de alcance y mecanismo sobre la red N20A, con un valor de `k` que elegimos. Aquí usamos `k=5`."

**Mostrar salida:**
```
1--------------------------------------------------
Alcance: ABCDEFGHIJ
Mecanismo: ABCDEFGHIJ
Partición ... | φ=0.0049 | Tiempo=0.0331 seg
```

**Voz:**
"Cada prueba está numerada y separada. Muestra el alcance, el mecanismo, la partición encontrada, la pérdida φ y el tiempo. Útil para hacer pruebas rápidas de rendimiento."

---

## Escena 6: Modo batch por Excel (2 minutos)

**Visual:** Terminal y Excel.

**Preparación:**
```bash
cd kGeoMip/src/Method2_Dynamic_Programming_Reformulation
uv run exec.py
```

**Voz:**
"El modo batch lee un archivo Excel de entrada: `kGeoMip/results/Pruebas_Metodo2.xlsx`. Cada fila contiene un par alcance|mecanismo. El sistema procesa todas las pruebas en paralelo con un tiempo máximo de 1 hora por prueba."

**Mostrar el Excel de entrada y luego el de salida:**
"Los resultados se guardan en `resultados_Geometric.xlsx`, con columnas: iteración, alcance, mecanismo, partición, pérdida (φ) y tiempo. Ideal para correr baterías grandes de pruebas y después analizarlas."

---

## Escena 7: Generar gráficos comparativos (2 minutos)

**Visual:** Terminal + mostrar los PNG.

**Comando:**
```bash
python resultados/graficos.py
```

**Voz:**
"El script `graficos.py` lee el archivo `resultados_10.xlsx` con datos de 49 pruebas en un sistema de 10 nodos, para k=2, 3, 4 y 5. Genera 5 gráficos automáticamente:"

**Mostrar cada gráfico:**

1. **G1 — Tiempo promedio por k:** "Barras con el tiempo promedio. k=2 es el más rápido."
2. **G2 — Pérdida promedio por k:** "Barras con la pérdida φ promedio. k=2 tiene la menor pérdida."
3. **G3 — Scatter tiempo vs pérdida:** "Cada punto es una prueba. Colores distintos por k. Escala logarítmica en Y."
4. **G4 — Líneas por prueba:** "Tiempo de cada prueba para cada k. Vemos cómo se comportan."
5. **G5 — Boxplot de tiempos:** "Distribución de tiempos por k. Se ven los valores atípicos."

**Voz:**
"Los gráficos se guardan como PNG en la carpeta `resultados/`. También se imprimen los promedios en consola para verificar."

---

## Escena 8: Generar nuevas redes (1 minuto)

**Visual:** Terminal.

**Comando rápido:**
```bash
python generar_red.py
```

**Voz:**
"Si necesitamos una red sintética nueva, `generar_red.py` crea una TPM para 22 nodos y la guarda como `N22A.csv` en la carpeta de muestras."

**Comando avanzado:**
```bash
python kGeoMip/data/creation.py
```

**Voz:**
"El script `creation.py` permite generar redes de cualquier tamaño. Por defecto crea una de 8 nodos; editando el archivo podemos cambiarlo."

---

## Escena 9: Resumen del flujo de trabajo (1 minuto)

**Visual:** Diagrama de flujo simple (puede ser una imagen o animación).

**Voz:**
"En resumen, el flujo típico de trabajo es:

1. **Elegir o generar una red** (TPM) de `kGeoMip/src/Method2_Dynamic_Programming_Reformulation/src/.samples/`.
2. **Configurar el análisis:** estado inicial, alcance, mecanismo, k.
3. **Ejecutar** con la GUI, la CLI, o batch.
4. **kGeoMip** construye el hipercubo de estados, calcula φ para cada candidato a partición, y para k>2 usa *Simulated Annealing* para buscar la mejor partición.
5. **Obtener resultados:** partición óptima, pérdida φ y tiempo.
6. **Visualizar:** con `graficos.py` generamos gráficos comparativos."

---

## Escena 10: Cierre (30 segundos)

**Visual:** Logo del proyecto o pantalla final.

**Voz:**
"Eso es todo. Con estas herramientas puedes analizar cualquier red TPM, encontrar sus mejores k-particiones y visualizar los resultados. El código completo está en el repositorio. ¡Gracias por ver este manual!"
