from colorama import init, Fore, Style
# import pyttsx3
# from pyttsx3.engine import Engine
# from pyttsx3.voice import Voice
import numpy as np
from threading import Thread
from typing import Optional

from src.constants.base import FLOAT_ZERO
from src.models.base.application import aplicacion
from src.funcs.format import fmt_grupos_particion

# Iniciar colorama
init()


def _formatear_tiempo(segundos: float) -> str:
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = segundos % 60
    if h > 0:
        return f"{h}h {m}m {s:.2f}s"
    elif m > 0:
        return f"{m}m {s:.2f}s"
    else:
        return f"{s:.4f}s"


class Solution:
    """
    Clase Solution para representar y visualizar soluciones del sistema IIT.

    Esta clase maneja la representación, visualización y anunciación por voz de las soluciones
    encontradas durante el análisis de Integrated Information Theory (IIT). Proporciona
    funcionalidades para mostrar distribuciones de probabilidad, particiones del sistema
    y el valor φ (phi|small phi) asociado a la pérdida de información.

    Args:
    ----
        estrategia (str):
            La estrategia utilizada para la resolución del problema.

        perdida (float):
            El valor φ que representa la pérdida de información en el sistema.
            Este valor cuantifica la diferencia entre la distribución del subsistema
            y la distribución de la partición.

        distribucion_subsistema (np.ndarray):
            Array que representa la distribución de probabilidad del subsistema completo.
            Contiene las probabilidades de cada estado posible en el espacio del subsistema.

        distribucion_particion (np.ndarray):
            Array que representa la distribución de probabilidad de la partición.
            Contiene las probabilidades de cada estado en el espacio de la partición
            que minimiza la información integrada.

        particion (str):
            Representación en formato string de la mejor partición encontrada.
            Utiliza notación matemática para mostrar la estructura de la partición.

        hablar (bool, opcional):
            Si es True, anuncia la solución encontrada usando síntesis de voz.
            Por defecto es True.

        voz (Optional[str], opcional):
            Identificador específico de la voz a utilizar para la síntesis.
            Si no se especifica, se busca automáticamente una voz en español.

    Attributes:
    ----------
        perdida (float):
            El valor φ de la solución.

        distribucion_subsistema (np.ndarray):
            La distribución de probabilidad del subsistema.

        distribucion_particion (np.ndarray):
            La distribución de probabilidad de la partición.

        particion (str):
            La representación de la mejor partición.

        id_voz (Optional[str]):
            El identificador de la voz seleccionada para la síntesis.

    Examples:
    --------
    >>> # Crear una solución básica
    >>> solucion = Solution(
    ...     perdida=0.25,
    ...     distribucion_subsistema=np.array([0.0, 1.0, 0.0, 0.0]),
    ...     distribucion_particion=np.array([0.0, 0.75, 0.0, 0.25]),
    ...     particion="⎛ A,C ⎞⎛ B ⎞
    ...                ⎝a,b,c⎠⎝ ∅ ⎠"
    ... )
    >>> print(solucion)  # Muestra la solución formateada con colores

    >>> # Crear una solución sin anuncio por voz
    >>> solucion_silenciosa = Solution(
    ...     perdida=0.25,
    ...     distribucion_subsistema=np.array([0.0, 1.0, 0.0, 0.0]),
    ...     distribucion_particion=np.array([0.0, 0.75, 0.0, 0.25]),
    ...     particion="⎛ A,C ⎞⎛ B ⎞
    ...                ⎝a,b,c⎠⎝ ∅ ⎠",
    ...     hablar=False
    ... )
    """

    def __init__(
        self,
        estrategia: str,
        perdida: float,
        distribucion_subsistema: np.ndarray,
        distribucion_particion: np.ndarray,
        particion: str,
        tiempo_total: float = FLOAT_ZERO,
        hablar: bool = True,
        voz: Optional[str] = None,
        tiempos_parciales: Optional[dict[str, float]] = None,
        grupos_futuro: Optional[list[str]] = None,
        grupos_presente: Optional[list[str]] = None,
    ) -> None:
        """
        Inicializa una nueva instancia de Solution.
        Consultar la documentación de la clase para detalles de los parámetros.
        """
        self.estrategia = estrategia
        self.perdida = perdida
        self.distribucion_subsistema = distribucion_subsistema
        self.distribucion_particion = distribucion_particion
        self.particion = particion
        self.tiempo_ejecucion = tiempo_total
        self.tiempos_parciales = tiempos_parciales or {}
        self.id_voz = voz
        self.hablar = hablar
        self.grupos_futuro = grupos_futuro or []
        self.grupos_presente = grupos_presente or []

    # def __obtener_voz_espanol(self, motor: Engine) -> Optional[str]:
    #     """
    #     Busca y obtiene un identificador de voz en español del sistema.

    #     Esta función implementa un sistema de prioridades para seleccionar
    #     la mejor voz disponible en español, priorizando voces específicas
    #     de diferentes regiones hispanohablantes.

    #     Args:
    #     ----
    #         motor:
    #             Instancia del motor de síntesis de voz pyttsx3.Engine.

    #     Returns:
    #     -------
    #         Optional[str]:
    #             El identificador de la voz seleccionada, o None si no se
    #             encuentra ninguna voz.

    #     Notes:
    #     -----
    #         El orden de prioridad es:
    #         1. Sabina (México)
    #         2. Helena (España)
    #         3. Cualquier voz con "spanish" en el nombre
    #         4. Cualquier voz con "español" en el nombre
    #         5. Cualquier voz con "es-" en el identificador
    #         6. Primera voz disponible si no se encuentra ninguna en español
    #     """
    #     voces: list[Voice] = motor.getProperty("voices")

    #     prioridades = [
    #         ("sabina", "méxico"),
    #         ("helena", "españa"),
    #         ("spanish", None),
    #         ("español", None),
    #         ("es-", None),
    #     ]

    #     for nombre_buscado, region in prioridades:
    #         for voz in voces:
    #             nombre_voz = voz.name.lower()
    #             id_voz = voz.id.lower()

    #             if nombre_buscado in nombre_voz or nombre_buscado in id_voz:
    #                 if region is None or region in nombre_voz:
    #                     return voz.id

    #     return voces[0].id if voces else None

    # def __anunciar_solucion(self) -> None:
    #     """
    #     Anuncia la solución encontrada usando síntesis de voz en español.

    #     Esta función configura y utiliza el motor de síntesis de voz para anunciar de forma audible que se ha encontrado una solución, incluyendo el valor φ calculado.

    #     La función se ejecuta en un hilo separado para no bloquear la ejecución principal del programa mientras se realiza la síntesis de voz.

    #     Notes:
    #     -----
    #         - Utilizar una velocidad de habla más lenta (150) para mejor comprensión
    #         - Se establece el volumen al 90% por defecto
    #         - Maneja excepciones de forma silenciosa para no interrumpir la ejecución
    #     """
    #     try:
    #         motor = pyttsx3.init()

    #         id_voz = self.id_voz or self.__obtener_voz_espanol(motor)
    #         if id_voz:
    #             motor.setProperty("voice", id_voz)

    #         motor.setProperty("rate", 150)
    #         motor.setProperty("volume", 0.9)

    #         mensaje = f"Solución encontrada con {self.estrategia}." + (
    #             f"El valor de fi es de {self.perdida:.2f}"
    #             if self.perdida > FLOAT_ZERO
    #             else "No hubo pérdida."
    #         )
    #         motor.say(mensaje)
    #         motor.runAndWait()
    #     except Exception as e:
    #         print(f"Error al inicializar el motor de voz: {e}")

    def _display_particion(self) -> str:
        if self.grupos_futuro and self.grupos_presente:
            return fmt_grupos_particion(self.grupos_futuro, self.grupos_presente)
        return self.particion

    def __str__(self) -> str:
        """
        Genera una representación en string formateada y coloreadita de la solución.

        Returns:
        -------
        str:
            Representación visual de la solución que incluye:
            - Valor φ en verdecito
            - Distribuciones del subsistema y partición
            - Mejor partición encontrada en magenta
            - Elementos decorativos en cyan
            - Tiempos parciales detallados

        Notes:
        -----
            Utiliza la biblioteca colorama para el formato de colores, permitiedo una visualización clara por terminal.
        """
        bilinea = "═" * 50
        trilinea = "≡" * 50

        def formatear_distribucion(
            distribucion: np.ndarray,
            evitar_desbordamiento=True,
        ):
            rango = distribucion.size
            mensaje_desborde = ""
            if evitar_desbordamiento:
                LIMITE = 64
                excedente = rango - LIMITE
                if excedente > 0:
                    mensaje_desborde = f" {excedente} valores más.."
                    rango = LIMITE

            datos = " ".join(
                f"{Fore.WHITE}{distribucion[idx]:.4f}"
                if distribucion[idx] > 0
                else f"{Fore.LIGHTBLACK_EX}0."
                for idx in range(rango)
            )
            return f"[ {datos}{mensaje_desborde} {Fore.WHITE}]"

        # if True:
        #     voz = Thread(target=self.__anunciar_solucion)
        #     voz.start()

        es_pyphi = self.estrategia == "Pyphi"
        tipo_distribucion = "" if es_pyphi else "marginal"

        # ── Tiempos ──
        tiempo_h, tiempo_m, tiempo_s = (
            f"{self.tiempo_ejecucion/3600:.2f}",
            f"{self.tiempo_ejecucion/60:.1f}",
            f"{self.tiempo_ejecucion:.4f}",
        )

        # ── Tiempos parciales ──
        parciales_str = ""
        if self.tiempos_parciales:
            lineas = []
            for fase, t in self.tiempos_parciales.items():
                lineas.append(f"{fase}: {_formatear_tiempo(t)}")
            parciales_str = "\n".join(
                f"    {Fore.WHITE}{l}" for l in lineas
            )
            parciales_str = f"\n{Fore.BLUE}Tiempos parciales:\n{parciales_str}"

        return f"""{Fore.CYAN}{bilinea}

{Fore.RED}{self.estrategia} fue la estrategia de solucion.

{Fore.BLUE}Distancia métrica utilizada:
{Fore.WHITE}{aplicacion.distancia_metrica}
{Fore.BLUE}Notación utilizada en indexación:
{Fore.WHITE}{aplicacion.notacion}

{Fore.YELLOW}Distribucion {tipo_distribucion} del Subsistema:
{Style.RESET_ALL}{formatear_distribucion(self.distribucion_subsistema)}
{Fore.YELLOW}Distribucion {tipo_distribucion} de la Partición:
{Style.RESET_ALL}{formatear_distribucion(self.distribucion_particion)}

{Fore.YELLOW}Mejor Bi-Partición:
{Fore.MAGENTA}{self._display_particion()}
{Fore.GREEN}Perdida mínima ( φ ) = {self.perdida:.4f}

{Fore.BLUE}Tiempos de ejecución:
{Fore.WHITE}Horas: {tiempo_h} = Minutos: {tiempo_m} = Segundos: {tiempo_s}{parciales_str}

{Fore.CYAN}{trilinea}{Style.RESET_ALL}"""

    def __repr__(self) -> str:
        """
        Implementa la representación oficial de la clase Solution.

        Returns:
        -------
            str:
                La misma representación que __str__ para consistencia.
        """
        return self.__str__()
