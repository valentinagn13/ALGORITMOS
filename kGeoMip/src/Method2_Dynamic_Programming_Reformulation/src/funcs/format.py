from src.funcs.base import ABECEDARY, LOWER_ABECEDARY
from src.constants.base import VOID_STR


def fmt_grupos_particion(
    grupos_futuro: list[str],
    grupos_presente: list[str],
) -> str:
    """
    Formatea grupos de partición en el formato de dos líneas más etiquetas G1, G2, …

    Ejemplo (k=3):
        | A,C,D,E,H,P,Q || B,F,G,J,M,R,T || I,K,L,N,O,S |
        | a,c,d,e,h,p,q ||  b,f,g,j,m,r  || i,k,l,n,o,s |
               G1               G2              G3
    """
    top_parts: list[str] = []
    bottom_parts: list[str] = []
    widths: list[int] = []

    for fut, pres in zip(grupos_futuro, grupos_presente):
        w = max(len(fut), len(pres)) + 2  # +2 for padding spaces
        widths.append(w)
        top_parts.append(fut.center(w))
        bottom_parts.append(pres.center(w))

    sep = "||"
    top_line = "|" + sep.join(top_parts) + "|"
    bottom_line = "|" + sep.join(bottom_parts) + "|"

    # Build S₁, S₂, … label line
    label_chars: list[str] = []
    for i, w in enumerate(widths):
        start = 1 + sum(widths[j] + 2 for j in range(i))
        center = start + w // 2
        label = f"G{i + 1}"
        pos = center - len(label) // 2
        while len(label_chars) <= pos + len(label):
            label_chars.append(" ")
        for k, c in enumerate(label):
            label_chars[pos + k] = c

    label_line = "".join(label_chars).rstrip()

    return top_line + "\n" + bottom_line + "\n" + label_line


def fmt_biparticion(
    parte_uno: list[tuple[int, ...], tuple[int, ...]],
    parte_dos: list[tuple[int, ...], tuple[int, ...]],
) -> str:
    # Extraer mecanismo y purview de cada parte
    mech_p, pur_p = parte_uno
    mech_d, purv_d = parte_dos

    # Convertir índices a letras o símbolo vacío si no hay elementos
    purv_prim = ",".join(ABECEDARY[j] for j in pur_p) if pur_p else VOID_STR
    mech_prim = ",".join(LOWER_ABECEDARY[i] for i in mech_p) if mech_p else VOID_STR

    purv_dual = ",".join(ABECEDARY[i] for i in purv_d) if purv_d else VOID_STR
    mech_dual = ",".join(LOWER_ABECEDARY[j] for j in mech_d) if mech_d else VOID_STR

    width_prim = max(len(purv_prim), len(mech_prim)) + 2
    width_dual = max(len(purv_dual), len(mech_dual)) + 2

    return (
        f"|{purv_prim:^{width_prim}}||{purv_dual:^{width_dual}}|\n"
        f"|{mech_prim:^{width_prim}}||{mech_dual:^{width_dual}}|\n"
    )


def fmt_biparte_q(
    prim: list[tuple[int, int]],
    dual: list[tuple[int, int]],
    to_sort: bool = True,
) -> str:
    top_prim, bottom_prim = fmt_parte_q(prim, to_sort)
    top_dual, bottom_dual = fmt_parte_q(dual, to_sort)

    return f"{top_prim}{top_dual}\n{bottom_prim}{bottom_dual}"


def fmt_parte_q(parte: list[tuple[int, int]], to_sort: bool = True) -> tuple[str, str]:
    if to_sort:
        # Ordenar por índice #
        parte.sort(key=lambda x: x[1])

    purv, mech = [], []
    for time, idx in parte:
        purv.append(ABECEDARY[idx]) if time else mech.append(LOWER_ABECEDARY[idx])

    str_purv = ",".join(purv) if purv else VOID_STR
    str_mech = ",".join(mech) if mech else VOID_STR
    width = max(len(str_purv), len(str_mech)) + 2

    return f"|{str_purv:^{width}}|", f"|{str_mech:^{width}}|"
