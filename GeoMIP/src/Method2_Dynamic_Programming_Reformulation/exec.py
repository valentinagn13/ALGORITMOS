import sys

from src.models.base.application import aplicacion
from src.main import iniciar


def main():
    """Inicializar el aplicativo.

    Flags:
        --cli, -i   → Modo interactivo por terminal (lee entradas del usuario).
        (sin flag)  → Modo Excel batch (comportamiento original).
    """

    if "--cli" in sys.argv or "-i" in sys.argv:
        from cli import ejecutar_interactivo
        ejecutar_interactivo()
        return

    aplicacion.profiler_habilitado = True

    iniciar()


if __name__ == "__main__":
    main()
