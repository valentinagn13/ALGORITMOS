#!/usr/bin/env python3
"""
Genera gráficos comparativos a partir de resultados_n10.xlsx (hoja 10A-Elementos).
Uso: python graficos.py
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import re
from pathlib import Path

sns.set_theme(style="whitegrid", palette="muted")

RUTA_EXCEL = Path(__file__).resolve().parent / "resultados_10.xlsx"
RUTA_GUARDAR = Path(__file__).resolve().parent
HOJA = "10A-Elementos"

def clean_valor(val):
    """Convierte un valor a float, limpiando comas, espacios, etc."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    s = s.replace(",", ".")
    s = re.sub(r"[^\d.eE+\-]", "", s)
    try:
        return float(s)
    except ValueError:
        return np.nan

def procesar_excel():
    df = pd.read_excel(RUTA_EXCEL, sheet_name=HOJA, header=None)
    data_rows = df.iloc[5:].copy()
    data_rows.columns = range(15)
    data_rows = data_rows.dropna(how="all").reset_index(drop=True)
    data_rows.columns = [
        "#Prueba", "Alcance", "Mecanismo",
        "Part_k2", "Perd_k2", "Tiem_k2",
        "Part_k3", "Perd_k3", "Tiem_k3",
        "Part_k4", "Perd_k4", "Tiem_k4",
        "Part_k5", "Perd_k5", "Tiem_k5",
    ]
    data_rows["#Prueba"] = data_rows["#Prueba"].astype(int)
    for k in [2, 3, 4, 5]:
        data_rows[f"Perd_k{k}"] = data_rows[f"Perd_k{k}"].apply(clean_valor)
        data_rows[f"Tiem_k{k}"] = data_rows[f"Tiem_k{k}"].apply(clean_valor)
    return data_rows

def grafico1_tiempo_promedio(df):
    ks = [2, 3, 4, 5]
    tiempos = [df[f"Tiem_k{k}"].dropna() for k in ks]
    promedios = [t.mean() for t in tiempos]
    desvios = [t.std() for t in tiempos]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar([str(k) for k in ks], promedios, yerr=desvios, capsize=6,
                  color=["#4C72B0", "#DD8452", "#55A868", "#C44E52"],
                  edgecolor="black", linewidth=0.8)
    for bar, val in zip(bars, promedios):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(promedios)*0.02,
                f"{val:.4f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_xlabel("Número de particiones (k)", fontsize=12)
    ax.set_ylabel("Tiempo promedio (segundos)", fontsize=12)
    ax.set_title("Tiempo promedio de ejecución por número de particiones (k)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(RUTA_GUARDAR / "g1_tiempo_promedio.png", dpi=150)
    print("\nG1 - Tiempo promedio por k:")
    for k, p in zip(ks, promedios):
        print(f"  k={k}: {p:.4f} s  (desv=±{desvios[ks.index(k)]:.4f})")

def grafico2_perdida_promedio(df):
    ks = [2, 3, 4, 5]
    perdidas = [df[f"Perd_k{k}"].dropna() for k in ks]
    promedios = [p.mean() for p in perdidas]
    desvios = [p.std() for p in perdidas]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar([str(k) for k in ks], promedios, yerr=desvios, capsize=6,
                  color=["#4C72B0", "#DD8452", "#55A868", "#C44E52"],
                  edgecolor="black", linewidth=0.8)
    for bar, val in zip(bars, promedios):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(promedios)*0.02,
                f"{val:.4f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_xlabel("Número de particiones (k)", fontsize=12)
    ax.set_ylabel("Pérdida promedio (φ)", fontsize=12)
    ax.set_title("Pérdida promedio (φ) por número de particiones (k)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(RUTA_GUARDAR / "g2_perdida_promedio.png", dpi=150)
    print("\nG2 - Pérdida promedio por k:")
    for k, p in zip(ks, promedios):
        print(f"  k={k}: {p:.4f}  (desv=±{desvios[ks.index(k)]:.4f})")

def grafico3_scatter(df):
    ks = [2, 3, 4, 5]
    colores = {2: "#4C72B0", 3: "#DD8452", 4: "#55A868", 5: "#C44E52"}
    labels = {2: "k=2", 3: "k=3", 4: "k=4", 5: "k=5"}
    fig, ax = plt.subplots(figsize=(8, 6))
    for k in ks:
        sub = df[[f"Perd_k{k}", f"Tiem_k{k}"]].dropna()
        ax.scatter(sub[f"Perd_k{k}"], sub[f"Tiem_k{k}"],
                   c=colores[k], label=labels[k], alpha=0.7, edgecolors="black", linewidth=0.5, s=50)
    ax.set_xlabel("Pérdida (φ)", fontsize=12)
    ax.set_ylabel("Tiempo (segundos)", fontsize=12)
    ax.set_title("Relación entre tiempo de ejecución y pérdida (φ)", fontsize=13, fontweight="bold")
    ax.legend(fontsize=11)
    ax.set_yscale("log")
    plt.tight_layout()
    plt.savefig(RUTA_GUARDAR / "g3_scatter_tiempo_vs_perdida.png", dpi=150)
    print("\nG3 - Scatter generado con escala log en Y.")

def grafico4_lineas(df):
    ks = [2, 3, 4, 5]
    colores = {2: "#4C72B0", 3: "#DD8452", 4: "#55A868", 5: "#C44E52"}
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for k in ks:
        sub = df[["#Prueba", f"Tiem_k{k}"]].dropna()
        ax.plot(sub["#Prueba"], sub[f"Tiem_k{k}"],
                marker="o", markersize=3, linewidth=1.2, color=colores[k], label=f"k={k}")
    ax.set_xlabel("#Prueba", fontsize=12)
    ax.set_ylabel("Tiempo (segundos)", fontsize=12)
    ax.set_title("Tiempo de ejecución por prueba y número de particiones", fontsize=13, fontweight="bold")
    ax.legend(fontsize=11)
    ax.set_yscale("log")
    plt.tight_layout()
    plt.savefig(RUTA_GUARDAR / "g4_lineas_tiempo_por_prueba.png", dpi=150)
    print("\nG4 - Líneas generado con escala log en Y.")

def grafico5_boxplot(df):
    ks = [2, 3, 4, 5]
    datos = [df[f"Tiem_k{k}"].dropna().values for k in ks]
    colores = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    bp = ax.boxplot(datos, patch_artist=True,
                    widths=0.5, showmeans=True,
                    meanprops=dict(marker="D", markerfacecolor="white", markeredgecolor="black"))
    ax.set_xticklabels([str(k) for k in ks])
    for patch, color in zip(bp["boxes"], colores):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.set_xlabel("Número de particiones (k)", fontsize=12)
    ax.set_ylabel("Tiempo (segundos)", fontsize=12)
    ax.set_title("Distribución de tiempos de ejecución por k", fontsize=13, fontweight="bold")
    ax.set_yscale("log")
    plt.tight_layout()
    plt.savefig(RUTA_GUARDAR / "g5_boxplot_tiempos.png", dpi=150)
    print("\nG5 - Boxplot generado con escala log en Y.")

def main():
    print("Leyendo Excel...")
    df = procesar_excel()
    print(f"  Pruebas cargadas: {len(df)}")
    print(f"  Columnas: {list(df.columns)}")
    print(df[["#Prueba", "Perd_k2", "Tiem_k2", "Perd_k3", "Tiem_k3",
              "Perd_k4", "Tiem_k4", "Perd_k5", "Tiem_k5"]].head(10).to_string())
    grafico1_tiempo_promedio(df)
    grafico2_perdida_promedio(df)
    grafico3_scatter(df)
    grafico4_lineas(df)
    grafico5_boxplot(df)
    print(f"\nGráficos guardados en: {RUTA_GUARDAR}")
    print("Para verlos abre los PNG en la carpeta resultados/.")

if __name__ == "__main__":
    main()
