import os
import sys
import threading
from pathlib import Path
from tkinter import *
from tkinter import ttk, scrolledtext
import re

def clean_ansi(text: str) -> str:
    """Elimina códigos de escape ANSI de la cadena."""
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

ROOT = Path(__file__).resolve().parent

STRATEGIES_KGEOMIP = ["KGeoMip"]
PAGE_LETTERS = [chr(ord("A") + i) for i in range(26)]


class App:
    def __init__(self):
        self.win = Tk()
        self.win.title("MIP/IIT — Interfaz de Análisis")
        self.win.geometry("700x100+100+100")
        self.win.resizable(True, True)
        self.win.minsize(640, 480)

        style = ttk.Style()
        style.theme_use("clam")

        main = ttk.Frame(self.win, padding=12)
        main.pack(fill=BOTH, expand=True)

        # --- Módulo ---
        f_mod = ttk.LabelFrame(main, text="Módulo", padding=8)
        f_mod.pack(fill=X, pady=(0, 8))
        self.modulo = StringVar(value="KGeoMip")
        ttk.Radiobutton(f_mod, text="KGeoMip", variable=self.modulo,
                        value="KGeoMip", command=self._toggle_modulo).pack(side=LEFT, padx=6)

        # --- Parámetros ---
        self.f_params = ttk.LabelFrame(main, text="Parámetros de entrada", padding=8)
        self.f_params.pack(fill=X, pady=(0, 8))

        self._filas: dict[int, ttk.Frame] = {}

        def campo(texto, default):
            nonlocal row
            frame = ttk.Frame(self.f_params)
            frame.pack(fill=X, pady=1)
            ttk.Label(frame, text=texto, width=32, anchor=W).pack(side=LEFT)
            e = ttk.Entry(frame, width=36)
            e.insert(0, default)
            e.pack(side=LEFT, padx=6, fill=X, expand=True)
            self._filas[row] = frame
            row += 1
            return e

        row = 0
        self.estado_inicial = campo("Estado inicial (binario):", "100000000000000")
        self.condiciones = campo("Condiciones (binario):", "1110")
        self.alcance = campo("Alcance (binario):", "1110")
        self.mecanismo = campo("Mecanismo (binario):", "1110")

        self.alcance_letras = campo("Alcance (letras, ej. ABC):", "ABC")
        self.mecanismo_letras = campo("Mecanismo (letras, ej. ABC):", "ABC")

        # k
        frame_k = ttk.Frame(self.f_params)
        frame_k.pack(fill=X, pady=1)
        ttk.Label(frame_k, text="k (particiones):", width=32, anchor=W).pack(side=LEFT)
        self.k_entry = ttk.Entry(frame_k, width=12)
        self.k_entry.insert(0, "2")
        self.k_entry.pack(side=LEFT, padx=6)
        self.k_entry.bind("<KeyRelease>", self._toggle_sa_params)
        self._filas[row] = frame_k
        row += 1

        # SA parameters (hidden when k <= 2)
        self._sa_rows: list[int] = []

        frame_sa1 = ttk.Frame(self.f_params)
        ttk.Label(frame_sa1, text="SA habilitado:", width=32, anchor=W).pack(side=LEFT)
        self.sa_enabled_var = BooleanVar(value=True)
        ttk.Checkbutton(frame_sa1, variable=self.sa_enabled_var).pack(side=LEFT, padx=6)
        self._filas[row] = frame_sa1
        self._sa_rows.append(row)
        row += 1

        frame_sa2 = ttk.Frame(self.f_params)
        ttk.Label(frame_sa2, text="SA max_iter:", width=32, anchor=W).pack(side=LEFT)
        self.sa_max_iter_entry = ttk.Entry(frame_sa2, width=12)
        self.sa_max_iter_entry.insert(0, "1700")
        self.sa_max_iter_entry.pack(side=LEFT, padx=6)
        self._filas[row] = frame_sa2
        self._sa_rows.append(row)
        row += 1

        frame_sa3 = ttk.Frame(self.f_params)
        ttk.Label(frame_sa3, text="SA max_time (seg):", width=32, anchor=W).pack(side=LEFT)
        self.sa_max_time_entry = ttk.Entry(frame_sa3, width=12)
        self.sa_max_time_entry.insert(0, "25.0")
        self.sa_max_time_entry.pack(side=LEFT, padx=6)
        self._filas[row] = frame_sa3
        self._sa_rows.append(row)
        row += 1

        # Página / variante TPM
        frame_pag = ttk.Frame(self.f_params)
        frame_pag.pack(fill=X, pady=1)
        ttk.Label(frame_pag, text="Variante TPM (página):", width=32, anchor=W).pack(side=LEFT)
        self.pagina_var = StringVar(value="A")
        self.pagina_cb = ttk.Combobox(frame_pag, textvariable=self.pagina_var,
                                      values=PAGE_LETTERS, state="readonly", width=10)
        self.pagina_cb.pack(side=LEFT, padx=6)
        self._filas[row] = frame_pag
        row += 1

        # Estrategia
        frame_estr = ttk.Frame(self.f_params)
        frame_estr.pack(fill=X, pady=1)
        ttk.Label(frame_estr, text="Estrategia:", width=32, anchor=W).pack(side=LEFT)
        self.estrategia_var = StringVar(value="KGeoMip")
        self.estrategia_cb = ttk.Combobox(frame_estr, textvariable=self.estrategia_var,
                                          values=STRATEGIES_KGEOMIP, state="readonly", width=18)
        self.estrategia_cb.pack(side=LEFT, padx=6)
        self._filas[row] = frame_estr
        row += 1

        self._toggle_modulo()

        # --- Botón ejecutar ---
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=X, pady=6)
        self.run_btn = ttk.Button(btn_frame, text="▶ Ejecutar", command=self._ejecutar)
        self.run_btn.pack(side=LEFT, padx=(0, 6))
        self.progress = ttk.Progressbar(btn_frame, mode="indeterminate", length=200)
        self.progress.pack(side=LEFT, fill=X, expand=True)

        # --- Salida ---
        lbl_out = ttk.Label(main, text="Salida:")
        lbl_out.pack(anchor=W, pady=(4, 0))
        self.output = scrolledtext.ScrolledText(main, height=20, font=("Consolas", 10))
        self.output.pack(fill=BOTH, expand=True)

    # ------------------------------------------------------------------
    def _toggle_modulo(self):
        modo = self.modulo.get()
        self.estrategia_cb["values"] = STRATEGIES_KGEOMIP
        if self.estrategia_var.get() not in STRATEGIES_KGEOMIP:
            self.estrategia_var.set("KGeoMip")

    def _toggle_sa_params(self, event=None):
        try:
            k = int(self.k_entry.get().strip())
            show = k > 2
        except ValueError:
            show = False
        for row in self._sa_rows:
            self._show_row(row, show)

    def _show_row(self, row, show):
        frame = self._filas.get(row)
        if frame:
            if show:
                frame.pack(fill=X, pady=1)
            else:
                frame.pack_forget()

    # ------------------------------------------------------------------
    def _log(self, msg):
        self.output.insert(END, msg + "\n")
        self.output.see(END)
        self.win.update_idletasks()

    def _ejecutar(self):
        self.output.delete("1.0", END)
        self.run_btn.config(state=DISABLED)
        self.progress.start(10)
        t = threading.Thread(target=self._run_analysis, daemon=True)
        t.start()

    def _run_analysis(self):
        try:
            pagina = self.pagina_var.get().strip()
            estado = self.estado_inicial.get().strip()
            self._run_kgeomip(estado, pagina)
        except Exception as e:
            self._log(f"\nERROR: {e}")
            import traceback
            self._log(traceback.format_exc())
        finally:
            self.progress.stop()
            self.run_btn.config(state=NORMAL)

    def _run_kgeomip(self, estado, pagina):
        method2_root = ROOT / "GeoMIP" / "src" / "Method2_Dynamic_Programming_Reformulation"
        old_cwd = Path.cwd()
        os.chdir(method2_root)
        sys.path.insert(0, str(method2_root))

        try:
            from src.models.base.application import aplicacion
            aplicacion.pagina_sample_network = pagina

            alcance_l = self.alcance_letras.get().strip().upper()
            mecanismo_l = self.mecanismo_letras.get().strip().upper()
            try:
                k = int(self.k_entry.get().strip())
            except ValueError:
                k = 2

            from cli import _letras_a_binario
            n = len(estado)
            alcance_bin = _letras_a_binario(alcance_l, n)
            mecanismo_bin = _letras_a_binario(mecanismo_l, n)
            condicion = "1" * n

            self._log(f"  Módulo:     KGeoMip")
            self._log(f"  Página TPM: {pagina}")
            self._log(f"  Estado ini: {estado}")
            self._log(f"  Alcance:    {alcance_l} → {alcance_bin}")
            self._log(f"  Mecanismo:  {mecanismo_l} → {mecanismo_bin}")
            self._log(f"  k:          {k}")
            self._log(f"  ─────────────────────────────────────────")

            from src.controllers.manager import Manager
            gestor = Manager(estado)
            ruta_tpm = gestor.tpm_filename
            self._log(f"  Cargando TPM: {ruta_tpm}")

            import numpy as np
            tpm = np.genfromtxt(ruta_tpm, delimiter=",")
            self._log(f"  TPM: {tpm.shape[0]} estados × {tpm.shape[1]} nodos\n")

            from src.controllers.strategies.kgeomip import KGeoMip
            analizador = KGeoMip(gestor)

            if k > 2:
                analizador.sa_enabled = self.sa_enabled_var.get()
                try:
                    analizador.sa_max_iter = int(self.sa_max_iter_entry.get().strip())
                except ValueError:
                    pass
                try:
                    analizador.sa_max_time = float(self.sa_max_time_entry.get().strip())
                except ValueError:
                    pass
                self._log(f"  SA enabled:  {analizador.sa_enabled}")
                self._log(f"  SA max_iter: {analizador.sa_max_iter}")
                self._log(f"  SA max_time: {analizador.sa_max_time}s")

            self._log(f"  Ejecutando KGeoMip (k={k})...\n")
            resultado = analizador.aplicar_estrategia(
                condicion=condicion, alcance=alcance_bin,
                mecanismo=mecanismo_bin, tpm=tpm, k=k,
            )
            # resultado es una cadena con colores ANSI
            texto_limpio = clean_ansi(str(resultado))
            self._log(texto_limpio)

            # --- Extracción de datos para CSV ---
            # --- Extracción de datos para CSV ---
            particion = ""
            perdida = ""
            tiempo = ""

            lineas = texto_limpio.splitlines()

            # Detectar qué formato de partición se está usando
            formato_g = False  # Formato con G0:, G1:, etc.
            formato_barras = False  # Formato con barras | ... ||

            # Primero, identificar el formato
            for line in lineas:
                if "G0:" in line and "G1:" in line:
                    formato_g = True
                    break
                if "Mejor K-Partición" in line:
                    formato_barras = True
                    break

            # Extraer según el formato detectado
            if formato_g:
                # Formato con G0:, G1:, etc. (k>=3)
                for line in lineas:
                    if "G0:" in line and "G1:" in line:
                        if "Mejor" in line:
                            particion = line.split("Mejor K-Partición:")[-1].strip()
                        else:
                            particion = line.strip()
                        break
            elif formato_barras:
                # Nuevo formato 3 líneas: futuro, presente, etiquetas
                for i, line in enumerate(lineas):
                    if "Mejor K-Partición" in line:
                        for j in range(i+1, min(i+5, len(lineas))):
                            if lineas[j].strip().startswith("|") and "||" in lineas[j]:
                                particion_lines = [lineas[j].rstrip()]
                                if j+1 < len(lineas) and lineas[j+1].strip().startswith("|"):
                                    particion_lines.append(lineas[j+1].rstrip())
                                    if j+2 < len(lineas) and lineas[j+2].strip():
                                        particion_lines.append(lineas[j+2].rstrip())
                                particion = "\n".join(particion_lines)
                                break
                        break

            # Si ninguno de los formatos anteriores funcionó, intentar búsqueda genérica
            if not particion:
                for line in lineas:
                    if line.strip().startswith("G0:") or (line.strip().startswith("|") and "Distribucion" not in line):
                        particion = line.strip()
                        break

            # Limpiar espacios múltiples (solo para formato G0:, el nuevo ya está limpio)
            if particion and "G0:" in particion:
                particion = re.sub(r'\s+', ' ', particion).strip()

            # Buscar pérdida (φ) - funciona para ambos formatos
            for line in lineas:
                if "Perdida mínima" in line or "φ" in line:
                    match = re.search(r"([0-9]+\.[0-9]+)", line)
                    if match:
                        perdida = match.group(1)
                        break

            # Buscar tiempo (Segundos:)
            for line in lineas:
                if "Segundos:" in line:
                    parts = line.split("Segundos:")
                    if len(parts) > 1:
                        tiempo = parts[1].strip().split()[0]
                        break

            # Si no encontró tiempo, buscar en la línea siguiente a "Tiempos de ejecución:"
            if not tiempo:
                for i, line in enumerate(lineas):
                    if "Tiempos de ejecución:" in line and i+1 < len(lineas):
                        next_line = lineas[i+1]
                        if "Segundos:" in next_line:
                            parts = next_line.split("Segundos:")
                            if len(parts) > 1:
                                tiempo = parts[1].strip().split()[0]
                        break

            # Mostrar los tres valores al final, en formato CSV con tabuladores
            csv_line = f"{particion}\t{perdida}\t{tiempo}"
            self._log("\n" + "="*50)
            self._log("📋 DATOS PARA EXCEL (copiar esta línea):")
            self._log(csv_line)
            self._log("="*50)

        finally:
            os.chdir(old_cwd)

    def run(self):
        self.win.mainloop()


if __name__ == "__main__":
    App().run()