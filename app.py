"""Distribuidor de alumnos para clase (Streamlit)."""
import math
import random

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Distribuidor de clase", page_icon="🪑", layout="wide")

HARD = 1000  # penalización de una regla obligatoria incumplida
TIPOS = {
    "Deben ir juntos": "J",
    "No pueden ir juntos": "S",
    "Prefiere estar con": "P",
    "Prefiere no estar con": "E",
}
NOMBRE_TIPO = {v: k for k, v in TIPOS.items()}
COLS = ["Alumno A", "Regla", "Alumno B", "Peso"]

EJ_ALUMNOS = (
    "Ana, F\nBea, F\nCarlos, M\nDani, M\nEva, F\nFran, M\n"
    "Gus, M\nHugo, M\nIris, F\nJon, M\nKira, F\nLuz, F"
)
EJ_REGLAS = [
    ("Ana", "Prefiere estar con", "Bea", 3),
    ("Carlos", "Prefiere estar con", "Dani", 2),
    ("Eva", "No pueden ir juntos", "Fran", 1),
    ("Gus", "Deben ir juntos", "Hugo", 1),
    ("Iris", "Prefiere no estar con", "Jon", 2),
]


def reglas_vacias():
    return pd.DataFrame(
        {
            "Alumno A": pd.Series(dtype="object"),
            "Regla": pd.Series(dtype="object"),
            "Alumno B": pd.Series(dtype="object"),
            "Peso": pd.Series(dtype="int64"),
        }
    )


def cargar_ejemplo():
    st.session_state.alumnos_txt = EJ_ALUMNOS
    st.session_state.reglas = pd.DataFrame(EJ_REGLAS, columns=COLS)
    st.session_state.pop("resultado", None)


# ---------------------------------------------------------------- lógica
def norm_sexo(t):
    t = t.strip().upper()
    if t.startswith(("F", "CHICA", "NIÑA", "NINA")):
        return "F"
    if t.startswith(("M", "H", "CHICO", "NIÑO", "NINO")):
        return "M"
    return ""


def leer_alumnos(texto):
    nombres, sexos, vistos = [], [], {}
    for linea in texto.splitlines():
        partes = [p.strip() for p in linea.replace(";", ",").replace("\t", ",").split(",")]
        nombre = partes[0] if partes else ""
        if not nombre:
            continue
        sexo = norm_sexo(partes[1]) if len(partes) > 1 else ""
        if nombre in vistos:
            vistos[nombre] += 1
            nombre = f"{nombre} ({vistos[nombre]})"
        else:
            vistos[nombre] = 1
        nombres.append(nombre)
        sexos.append(sexo)
    return nombres, sexos


def tamanos(n, k):
    base, resto = divmod(n, k)
    return [base + 1] * resto + [base] * (k - resto)


def juntos(arr, a, b, en_fila):
    return abs(arr[a] - arr[b]) == 1 if en_fila else arr[a] == arr[b]


def resolver(n, reglas, sexo, sizes, modo, min_sexo, iters, seed):
    """Recocido simulado. arr[i] = grupo del alumno i (o posición en la fila)."""
    rng = random.Random(seed)
    en_fila = modo == "Fila"

    def puntuar(arr):
        s = 0
        for a, b, k, w in reglas:
            t = juntos(arr, a, b, en_fila)
            if k == "J" and not t:
                s -= HARD
            elif k == "S" and t:
                s -= HARD
            elif k == "P" and t:
                s += 10 * w
            elif k == "E" and t:
                s -= 15 * w
        if min_sexo and not en_fila:
            cuenta = {}
            for i in range(n):
                if sexo[i]:
                    clave = (arr[i], sexo[i])
                    cuenta[clave] = cuenta.get(clave, 0) + 1
            for g in range(len(sizes)):
                for x in ("M", "F"):
                    s -= (HARD // 2) * max(0, min_sexo - cuenta.get((g, x), 0))
        return s

    mejor, mejor_s = None, -10**9
    reinicios = 4
    pasos = max(1, iters // reinicios)
    for _ in range(reinicios):
        if en_fila:
            arr = list(range(n))
        else:
            arr = [g for g, sz in enumerate(sizes) for _ in range(sz)]
        rng.shuffle(arr)
        cur = puntuar(arr)
        if cur > mejor_s:
            mejor, mejor_s = arr[:], cur
        for it in range(pasos):
            temp = 30 * (0.01 ** (it / pasos))
            i, j = rng.sample(range(n), 2)
            if arr[i] == arr[j]:
                continue
            arr[i], arr[j] = arr[j], arr[i]
            nuevo = puntuar(arr)
            if nuevo >= cur or rng.random() < math.exp((nuevo - cur) / temp):
                cur = nuevo
                if cur > mejor_s:
                    mejor, mejor_s = arr[:], cur
            else:
                arr[i], arr[j] = arr[j], arr[i]
    return mejor


def informe(res):
    en_fila = res["modo"] == "Fila"
    filas = []
    for a, b, k, w in res["reglas"]:
        t = juntos(res["arr"], a, b, en_fila)
        ok = {"J": t, "S": not t, "P": t, "E": not t}[k]
        filas.append(
            {
                "Alumno A": res["nombres"][a],
                "Regla": NOMBRE_TIPO[k],
                "Alumno B": res["nombres"][b],
                "Cumplida": "✅" if ok else "❌",
                "_k": k,
                "_ok": ok,
            }
        )
    return filas


def etiqueta(res, i):
    s = res["sexos"][i]
    return res["nombres"][i] + (f" ({s})" if s else "")


def mostrar(res):
    n = len(res["nombres"])
    filas = informe(res)
    duras = [f for f in filas if f["_k"] in "JS"]
    prefs = [f for f in filas if f["_k"] == "P"]
    evitar = [f for f in filas if f["_k"] == "E"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Reglas obligatorias", f"{sum(f['_ok'] for f in duras)} / {len(duras)}")
    c2.metric("Preferencias cumplidas", f"{sum(f['_ok'] for f in prefs)} / {len(prefs)}")
    c3.metric("No preferencias respetadas", f"{sum(f['_ok'] for f in evitar)} / {len(evitar)}")
    if any(not f["_ok"] for f in duras):
        st.warning(
            "Hay reglas obligatorias sin cumplir: pueden ser contradictorias o demasiado "
            "estrictas para este tamaño de grupo. Revisa las reglas o genera otra distribución."
        )

    if res["modo"] == "Fila":
        orden = sorted(range(n), key=lambda i: res["arr"][i])
        st.markdown(" → ".join(etiqueta(res, i) for i in orden))
        tabla = pd.DataFrame(
            {
                "Posición": range(1, n + 1),
                "Alumno": [res["nombres"][i] for i in orden],
                "Sexo": [res["sexos"][i] for i in orden],
            }
        )
    else:
        etiq = {"Parejas": "Pareja", "Tríos": "Trío"}.get(res["modo"], "Grupo")
        k = len(res["sizes"])
        cols = st.columns(min(k, 4))
        filas_tabla = []
        for g in range(k):
            miembros = [i for i in range(n) if res["arr"][i] == g]
            with cols[g % len(cols)]:
                with st.container(border=True):
                    st.markdown(f"**{etiq} {g + 1}** ({len(miembros)})")
                    for i in miembros:
                        st.write(etiqueta(res, i))
            for i in miembros:
                filas_tabla.append(
                    {"Grupo": f"{etiq} {g + 1}", "Alumno": res["nombres"][i], "Sexo": res["sexos"][i]}
                )
        tabla = pd.DataFrame(filas_tabla)

    st.download_button(
        "Descargar CSV",
        tabla.to_csv(index=False).encode("utf-8-sig"),
        file_name="distribucion.csv",
        mime="text/csv",
    )
    if filas:
        with st.expander("Detalle de cada regla"):
            st.dataframe(pd.DataFrame(filas).drop(columns=["_k", "_ok"]), hide_index=True)


# ---------------------------------------------------------------- interfaz
if "alumnos_txt" not in st.session_state:
    st.session_state.alumnos_txt = ""
if "reglas" not in st.session_state:
    st.session_state.reglas = reglas_vacias()

st.title("🪑 Distribuidor de alumnos")
st.caption("Escribe los alumnos, define quién puede o no ir junto y deja que el programa proponga la distribución.")

tab1, tab2, tab3 = st.tabs(["Alumnos", "Reglas y preferencias", "Distribución"])

with tab1:
    st.text_area(
        "Un alumno por línea. Opcional: coma y sexo (M = chico, F = chica).",
        key="alumnos_txt",
        height=280,
        placeholder="Ana, F\nLuis, M\nJ.P.",
    )
    st.button("Cargar ejemplo", on_click=cargar_ejemplo)

nombres, sexos = leer_alumnos(st.session_state.alumnos_txt)
n = len(nombres)
reglas = []

with tab2:
    if n < 2:
        st.info("Añade al menos 2 alumnos en la pestaña Alumnos.")
    else:
        st.markdown(
            "- **Deben ir juntos / No pueden ir juntos**: reglas obligatorias.\n"
            "- **Prefiere estar con / Prefiere no estar con**: la elección es de A hacia B; "
            "el peso (1 a 3) indica su importancia."
        )
        editado = st.data_editor(
            st.session_state.reglas,
            key="ed_reglas",
            num_rows="dynamic",
            column_config={
                "Alumno A": st.column_config.SelectboxColumn("Alumno A", options=nombres, required=True),
                "Regla": st.column_config.SelectboxColumn("Regla", options=list(TIPOS), required=True),
                "Alumno B": st.column_config.SelectboxColumn("Alumno B", options=nombres, required=True),
                "Peso": st.column_config.NumberColumn("Peso", min_value=1, max_value=3, step=1, default=1),
            },
        )
        idx = {nm: i for i, nm in enumerate(nombres)}
        for _, r in editado.iterrows():
            a, b, t = r["Alumno A"], r["Alumno B"], TIPOS.get(r["Regla"])
            if a in idx and b in idx and a != b and t:
                w = int(r["Peso"]) if pd.notna(r["Peso"]) else 1
                reglas.append((idx[a], idx[b], t, max(1, min(3, w))))

with tab3:
    if n < 2:
        st.info("Añade al menos 2 alumnos para poder distribuirlos.")
    else:
        modo = st.radio("Tipo de distribución", ["Parejas", "Tríos", "Grupos", "Fila"], horizontal=True)
        sizes, ok_config = [], True
        if modo == "Parejas":
            sizes = tamanos(n, max(1, n // 2))
        elif modo == "Tríos":
            sizes = tamanos(n, max(1, round(n / 3)))
        elif modo == "Grupos":
            tmin, tmax = st.slider("Tamaño de cada grupo", 3, 6, (3, 6))
            kmin, kmax = math.ceil(n / tmax), n // tmin
            if kmin > kmax or kmax < 1:
                st.error("Con este rango de tamaños no se pueden formar grupos. Prueba con otro rango.")
                ok_config = False
            else:
                k = kmin
                if kmin < kmax:
                    k = st.slider("Número de grupos", kmin, kmax, min(kmax, max(kmin, round(n / 4))))
                sizes = tamanos(n, k)
        if sizes and modo != "Fila":
            st.caption("Tamaños: " + ", ".join(str(s) for s in sizes))

        min_sexo = 0
        if modo != "Fila" and any(sexos):
            min_sexo = st.number_input(
                "Mínimo de chicos y de chicas por grupo",
                0, 3, 0,
                help="En parejas, 1 = parejas mixtas (chico-chica).",
            )
        with st.expander("Opciones avanzadas"):
            iters = st.slider("Esfuerzo de búsqueda", 4000, 60000, 20000, step=2000)

        if ok_config and st.button("Generar distribución", type="primary"):
            with st.spinner("Calculando…"):
                arr = resolver(n, reglas, sexos, sizes, modo, int(min_sexo), iters, random.randrange(10**9))
            st.session_state.resultado = {
                "arr": arr, "nombres": nombres, "sexos": sexos,
                "modo": modo, "reglas": reglas, "sizes": sizes,
            }
        if "resultado" in st.session_state:
            mostrar(st.session_state.resultado)
