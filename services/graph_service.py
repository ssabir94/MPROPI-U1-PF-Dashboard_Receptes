# Representar els resums calculats al servei de dades. Convertir a float
# només per dibuixar; conservar els imports Decimal als càlculs i a les taules.
from io import BytesIO
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter


def crear_grafica_grups(comparacio_grups, grup_seleccionat="", vista="escriptori"):
    """Comparar el percentatge de receptes i d'import de cada categoria."""
    from textwrap import fill

    # Utilitzar etiquetes breus només per presentar les categories.
    # Conservar els noms originals del CSV a la taula i als registres.
    noms_breus = {
        "A": "Tracte alimentari i metabolisme",
        "B": "Sang i òrgans hematopoètics",
        "C": "Sistema cardiovascular",
        "D": "Dermatològics",
        "G": "Sistema genitourinari i hormones sexuals",
        "H": "Hormones sistèmiques (excl. sexuals i insulines)",
        "J": "Antiinfecciosos d'ús sistèmic",
        "L": "Antineoplàsics i immunomoduladors",
        "M": "Sistema musculoesquelètic",
        "N": "Sistema nerviós",
        "P": "Antiparasitaris, insecticides i repel·lents",
        "R": "Sistema respiratori",
        "S": "Òrgans dels sentits",
        "V": "Diversos",
    }

    # Acceptar només els dos formats de presentació previstos.
    if vista not in {"escriptori", "mobil"}:
        raise ValueError("La vista de la gràfica no és vàlida.")

    # Mantenir un ordre estable encara que s'ordeni la taula de sota.
    grups = sorted(
        comparacio_grups,
        key=lambda grup: (-grup["receptes"], grup["codi"]),
    )
    if vista == "mobil":
        # Situar el nom damunt de les dues mesures per aprofitar tota
        # l’amplada del telèfon, conservant els mateixos percentatges i ordre.
        etiquetes = [f"{g['codi']} · {noms_breus.get(g['codi'], g['nom'] or 'Sense especificar')}" for g in grups]
        calculable = any(g["receptes"] > 0 for g in grups) and any(g["import_integre"] > 0 for g in grups)
        series = [
            ("Receptes", "#3F72A6", [float(g["percentatge_receptes"]) for g in grups]),
            ("Import íntegre", "#287D78", [float(g["percentatge_import"]) for g in grups]),
        ]
        return _crear_grafica_mobil(
            etiquetes if calculable else [], series,
            "Receptes i import per categoria", "percentatge",
            [i for i, g in enumerate(grups) if g["codi"] == grup_seleccionat],
            "No hi ha dades per comparar." if not grups else "No es poden comparar percentatges amb un total zero.",
        )

    altura = max(3.0, len(grups) * 0.64 + 1.6)
    # Utilitzar Figure directament per evitar l’estat global de pyplot
    # i crear una figura independent per a cada petició.
    figura = Figure(figsize=(12, altura), layout="constrained")
    eixos = figura.subplots()

    calculable = (
        any(grup["receptes"] > 0 for grup in grups)
        and any(grup["import_integre"] > 0 for grup in grups)
    )
    if not grups or not calculable:
        missatge = (
            "No hi ha dades per al període, edat i sexe indicats."
            if not grups else "No es poden comparar percentatges perquè algun total és zero."
        )
        eixos.text(
            0.5, 0.5, missatge,
            ha="center", va="center", transform=eixos.transAxes,
        )
        eixos.set_axis_off()
    else:
        etiquetes = []
        for grup in grups:
            nom = noms_breus.get(grup["codi"], grup["nom"] or "Sense especificar")
            etiquetes.append(fill(f"{grup['codi']} · {nom}", width=36))

        posicions = list(range(len(grups)))
        # Ressaltar la categoria sense eliminar les altres del denominador.
        for posicio, grup in enumerate(grups):
            if grup["codi"] == grup_seleccionat:
                eixos.axhspan(posicio - 0.47, posicio + 0.47, color="#e5f2ef", zorder=0)
        # Assignar un color estable a cada mesura i mantenir el mateix
        # significat a la llegenda, a les ajudes de l’HTML i a la gràfica mensual.
        series = [
            ("percentatge_receptes", "% de receptes", "#3F72A6", -0.18),
            ("percentatge_import", "% de l’import íntegre", "#287D78", 0.18),
        ]
        maxim = 0
        for camp, etiqueta, color, desplacament in series:
            valors = [float(grup[camp]) for grup in grups]
            maxim = max(maxim, max(valors, default=0))
            barres = eixos.barh(
                [posicio + desplacament for posicio in posicions],
                valors, height=0.29, label=etiqueta, color=color,
            )

            # Diferenciar els percentatges molt petits d'un zero exacte.
            textos = [
                "< 0,01 %" if 0 < valor < 0.01
                else f"{valor:.2f} %".replace(".", ",")
                for valor in valors
            ]
            eixos.bar_label(
                barres, labels=textos, padding=5, fontsize=10, color="#172c3c",
            )

        eixos.set_yticks(posicions)
        eixos.set_yticklabels(etiquetes, fontsize=11)
        for etiqueta, grup in zip(eixos.get_yticklabels(), grups):
            if grup["codi"] == grup_seleccionat:
                etiqueta.set_fontweight("bold")
        eixos.tick_params(axis="y", length=0, pad=12)
        eixos.invert_yaxis()
        eixos.set_xlim(0, max(maxim, 1) * 1.24)
        # Evitar marques superiors al 100 % en seleccions d'una categoria.
        eixos.set_xticks([
            valor for valor in eixos.get_xticks()
            if 0 <= valor <= min(100, eixos.get_xlim()[1])
        ])
        eixos.xaxis.set_major_formatter(
            FuncFormatter(lambda valor, posicio: f"{valor:g} %".replace(".", ","))
        )
        eixos.set_xlabel("Percentatge del total comparat", labelpad=12)
        eixos.set_title("Part de les receptes i de l’import per categoria", loc="left", pad=48)
        eixos.legend(
            loc="lower left", bbox_to_anchor=(0, 1.01), ncol=2,
            frameon=False, borderaxespad=0, fontsize=10,
        )

        # Separar visualment les categories sense afegir vores pesades.
        for posicio in posicions[1:]:
            eixos.axhline(posicio - 0.5, color="#edf1f4", linewidth=0.8, zorder=0)
        eixos.set_axisbelow(True)
        eixos.grid(axis="x", color="#e4ebef", linewidth=0.8)
        for costat in ("top", "right", "left"):
            eixos.spines[costat].set_visible(False)
        eixos.spines["bottom"].set_color("#bdcdd6")

    # Preparar el PNG en memòria per no sobreescriure un fitxer compartit
    # entre consultes amb filtres diferents.
    imatge = BytesIO()
    figura.savefig(imatge, format="png", dpi=120)
    imatge.seek(0)
    return imatge


def crear_grafica_mensual(resum_mensual, mesura="receptes", mes_seleccionat="", vista="escriptori"):
    """Comparar el context anual i ressaltar el mes sense filtrar l'any."""
    configuracions = {
        "receptes": {
            "titol": "Receptes facturades per mes",
            "etiqueta": "Nombre de receptes", "color": "#3F72A6",
            "destacat": "#244F7A",
        },
        "import_integre": {
            "titol": "Import íntegre per mes",
            "etiqueta": "Import íntegre en euros", "color": "#287D78",
            "destacat": "#195752",
        },
    }
    if mesura not in configuracions:
        raise ValueError("La mesura seleccionada no és vàlida.")
    if mes_seleccionat and mes_seleccionat not in {str(mes) for mes in range(1, 13)}:
        raise ValueError("El mes seleccionat no és vàlid.")

    if vista not in {"escriptori", "mobil"}:
        raise ValueError("La vista de la gràfica no és vàlida.")
    configuracio = configuracions[mesura]
    if vista == "mobil":
        # Representar els mesos en vertical per mantenir llegibles els noms
        # i els imports, sense escurçar ni alterar els valors informats.
        noms = ["Gener", "Febrer", "Març", "Abril", "Maig", "Juny", "Juliol", "Agost", "Setembre", "Octubre", "Novembre", "Desembre"]
        dades_mes = {fila["mes"]: float(fila[mesura]) for fila in resum_mensual}
        valors = [dades_mes.get(mes) for mes in range(1, 13)]
        return _crear_grafica_mobil(
            noms if resum_mensual else [],
            [("Receptes" if mesura == "receptes" else "Import íntegre", configuracio["color"], valors)],
            configuracio["titol"], mesura,
            [int(mes_seleccionat) - 1] if mes_seleccionat else [],
            "No hi ha dades en cap mes amb aquests filtres.",
        )
    figura = Figure(figsize=(11, 4.8), layout="constrained")
    eixos = figura.subplots()
    if not resum_mensual:
        eixos.text(
            0.5, 0.5, "No hi ha dades en cap mes del 2024 per a aquests filtres.",
            ha="center", va="center", transform=eixos.transAxes,
        )
        eixos.set_axis_off()
    else:
        noms_mesos = [
            "Gen", "Feb", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Oct", "Nov", "Des",
        ]
        mesos = [fila["mes"] for fila in resum_mensual]
        valors = [float(fila[mesura]) for fila in resum_mensual]
        mes_destacat = int(mes_seleccionat) if mes_seleccionat else None
        colors = [
            configuracio["destacat"] if mes == mes_destacat else configuracio["color"]
            for mes in mesos
        ]
        if mes_destacat:
            eixos.axvspan(mes_destacat - 0.43, mes_destacat + 0.43, color="#e5f2ef", zorder=0)

        barres = eixos.bar(mesos, valors, color=colors, width=0.62, zorder=3)
        # Afegir un contorn al mes seleccionat per distingir-lo també
        # sense dependre només de la diferència entre dos tons del mateix color.
        if mes_destacat in mesos:
            barra_destacada = barres[mesos.index(mes_destacat)]
            barra_destacada.set_edgecolor("#172c3c")
            barra_destacada.set_linewidth(1.8)
        # Mostrar els dotze mesos sense inventar recomptes per als absents.
        eixos.set_xticks(range(1, 13))
        eixos.set_xticklabels(noms_mesos)
        eixos.set_xlim(0.4, 12.6)
        # Partir de zero per no exagerar les diferències entre barres
        # i reservar espai superior per a l’etiqueta del mes seleccionat.
        eixos.set_ylim(0, max(max(valors, default=0), 1) * 1.2)
        for mes in range(1, 13):
            if mes not in mesos:
                eixos.text(
                    mes, 0.025, "Sense registres", rotation=90,
                    ha="center", va="bottom", fontsize=8, color="#526775",
                    transform=eixos.get_xaxis_transform(),
                )
        if mes_destacat:
            eixos.get_xticklabels()[mes_destacat - 1].set_fontweight("bold")
            # Anotar només el mes ressaltat per evitar dotze etiquetes superposades.
            if mes_destacat in mesos:
                index = mesos.index(mes_destacat)
                valor = valors[index]
                text = (
                    f"{valor:,.0f}".replace(",", ".") if mesura == "receptes"
                    else f"{valor:,.2f}".replace(",", "|").replace(".", ",").replace("|", ".") + " €"
                )
                # Situar l’etiqueta per sobre de totes les barres, amb un fons blanc,
                # per evitar que un import llarg quedi sobre una barra veïna.
                # Enllaçar-la amb la barra seleccionada per mantenir clara l’associació.
                # Alinear-la cap a dins al gener i al desembre per evitar retallar imports llargs.
                eixos.annotate(
                    text, (mes_destacat, valor),
                    xytext=(mes_destacat, max(max(valors), 1) * 1.09),
                    textcoords="data",
                    ha="left" if mes_destacat == 1 else ("right" if mes_destacat == 12 else "center"),
                    va="bottom", fontsize=10,
                    fontweight="bold", color="#172c3c", zorder=6,
                    bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#bdcdd6"},
                    arrowprops={"arrowstyle": "-", "color": "#172c3c", "linewidth": 1.1},
                )

        eixos.set_title(configuracio["titol"], loc="left", pad=16)
        eixos.set_ylabel(configuracio["etiqueta"])
        eixos.set_xlabel("Mes de 2024")
        eixos.yaxis.set_major_formatter(
            FuncFormatter(lambda valor, posicio: f"{valor:,.0f}".replace(",", "."))
        )
        eixos.set_axisbelow(True)
        eixos.grid(axis="y", color="#e4ebef")
        for costat in ("top", "right"):
            eixos.spines[costat].set_visible(False)
        for costat in ("left", "bottom"):
            eixos.spines[costat].set_color("#bdcdd6")

    imatge = BytesIO()
    figura.savefig(imatge, format="png", dpi=120)
    imatge.seek(0)
    return imatge


def crear_grafica_edat_sexe(resum_edats, sexe_seleccionat="", vista="escriptori"):
    """Representar només els sexes inclosos en la selecció."""

    # Separar els colors de sexe dels colors de receptes i import:
    # evitar que el terracota d’homes es confongui amb el verd dels imports.
    # Definir les sèries i els seus colors.
    series = [
        ("Dona", "Dones", "#8060AE"),
        ("Home", "Homes", "#C17A4A"),
    ]

    # Excloure de la representació el sexe eliminat pel filtre.
    if sexe_seleccionat:
        series = [
            serie
            for serie in series
            if serie[0] == sexe_seleccionat
        ]

    if vista not in {"escriptori", "mobil"}:
        raise ValueError("La vista de la gràfica no és vàlida.")
    if vista == "mobil":
        # Conservar els sexes inclosos pel filtre i compartir la mateixa escala.
        return _crear_grafica_mobil(
            [fila["edat"] for fila in resum_edats],
            [(etiqueta, color, [fila[sexe] for fila in resum_edats]) for sexe, etiqueta, color in series],
            "Receptes per edat i sexe", "receptes", [],
            "No hi ha dades amb aquests filtres.",
        )

    # Reduir l'altura si només hi ha una franja seleccionada.
    altura = max(2.4, len(resum_edats) * 0.72 + 1.1)

    figura = Figure(figsize=(10, altura), layout="constrained")
    eixos = figura.subplots()

    if not resum_edats:
        eixos.text(
            0.5,
            0.5,
            "No hi ha dades per a aquesta selecció.",
            ha="center",
            va="center",
            transform=eixos.transAxes,
        )
        eixos.set_axis_off()

    else:
        edats = [fila["edat"] for fila in resum_edats]
        posicions = list(range(len(edats)))

        for index, (sexe, etiqueta, color) in enumerate(series):
            valors = [fila[sexe] for fila in resum_edats]

            # Centrar les barres si només es representa un sexe.
            if len(series) == 1:
                desplacament = 0
                amplada = 0.5
            else:
                desplacament = -0.18 if index == 0 else 0.18
                amplada = 0.32

            barres = eixos.barh(
                [posicio + desplacament for posicio in posicions],
                valors,
                height=amplada,
                label=etiqueta,
                color=color,
            )

            # Mostrar el recompte de cada barra.
            eixos.bar_label(
                barres,
                labels=[
                    f"{quantitat:,}".replace(",", ".")
                    for quantitat in valors
                ],
                padding=4,
                fontsize=9,
            )

        eixos.set_yticks(posicions)
        eixos.set_yticklabels(edats)
        eixos.invert_yaxis()

        # Calcular l'escala només amb les sèries representades.
        maxim = max(
            (
                fila[sexe]
                for fila in resum_edats
                for sexe, etiqueta, color in series
            ),
            default=0,
        )

        eixos.set_xlim(0, max(maxim, 1) * 1.35)

        eixos.xaxis.set_major_formatter(
            FuncFormatter(
                lambda valor, posicio:
                f"{valor:,.0f}".replace(",", ".")
            )
        )

        if sexe_seleccionat == "Dona":
            titol = "Receptes facturades de dones per edat"
        elif sexe_seleccionat == "Home":
            titol = "Receptes facturades d'homes per edat"
        else:
            titol = "Receptes facturades per edat i sexe"

        eixos.set_title(titol)
        eixos.set_xlabel("Nombre de receptes")
        eixos.legend(loc="lower right")

        eixos.set_axisbelow(True)
        eixos.grid(axis="x", alpha=0.2)

        for costat in ("top", "right", "left"):
            eixos.spines[costat].set_visible(False)

    imatge = BytesIO()
    figura.savefig(imatge, format="png", dpi=120)
    imatge.seek(0)

    return imatge


def _crear_grafica_mobil(etiquetes, series, titol, tipus, destacats, missatge_buit):
    """Presentar les mateixes dades en blocs verticals llegibles en mòbil."""
    from textwrap import fill
    from matplotlib.ticker import MaxNLocator

    # Reservar una línia per al nom i dues per cada mesura: valor i barra.
    # Ajustar l'altura al contingut perquè no calgui desplaçar-se lateralment.
    noms = [fill(nom, width=34) for nom in etiquetes]
    blocs = []
    posicio = 0
    for nom in noms:
        altura_nom = len(nom.splitlines()) * 0.30
        altura_bloc = altura_nom + len(series) * 0.68 + 0.30
        blocs.append((posicio, altura_nom, altura_bloc))
        posicio += altura_bloc

    figura = Figure(figsize=(3.4, max(2.0, posicio * 0.48 + 1.15)), layout="constrained")
    eixos = figura.subplots()
    if not etiquetes:
        eixos.text(0.5, 0.5, fill(missatge_buit, 32), ha="center", va="center", transform=eixos.transAxes)
        eixos.set_axis_off()
    else:
        valors = [valor for etiqueta, color, dades in series for valor in dades if valor is not None]
        maxim = max(valors, default=0)
        eixos.set_xlim(0, max(maxim, 1) * 1.03)
        eixos.set_ylim(posicio, -0.10)
        eixos.set_yticks([])
        eixos.set_title(fill(titol, 34), loc="left", fontsize=11, pad=16)

        for index, (nom, bloc) in enumerate(zip(noms, blocs)):
            inici, altura_nom, altura_bloc = bloc
            if index in destacats:
                eixos.axhspan(inici - 0.05, inici + altura_bloc - 0.10, color="#e5f2ef", zorder=0)
            eixos.text(
                0, inici, nom, transform=eixos.get_yaxis_transform(),
                ha="left", va="top", fontsize=10.5,
                fontweight="bold" if index in destacats else "normal", color="#172c3c",
            )
            for numero, (etiqueta, color, dades) in enumerate(series):
                valor = dades[index]
                linia = inici + altura_nom + 0.12 + numero * 0.68
                if valor is None:
                    text = "Sense registres"
                elif tipus == "percentatge":
                    text = "< 0,01 %" if 0 < valor < 0.01 else f"{valor:.2f} %".replace(".", ",")
                elif tipus == "import_integre":
                    text = f"{valor:,.2f}".replace(",", "|").replace(".", ",").replace("|", ".") + " €"
                else:
                    text = f"{valor:,.0f}".replace(",", ".")
                # Col·locar els valors al marge dret, fora de l'extrem de les barres,
                # per evitar retalls quan l’import o el recompte tenen molts dígits.
                eixos.text(0, linia, etiqueta, transform=eixos.get_yaxis_transform(), ha="left", va="top", fontsize=10, color=color)
                eixos.text(1, linia, text, transform=eixos.get_yaxis_transform(), ha="right", va="top", fontsize=10, color="#172c3c")
                if valor is not None:
                    eixos.barh(
                        linia + 0.35, valor, height=0.16, color=color,
                        edgecolor="#172c3c" if index in destacats else "none",
                        linewidth=1.1 if index in destacats else 0, zorder=3,
                    )

        # Especificar les unitats dels eixos curts sense utilitzar notació 1e6.
        divisor = 1
        unitat = "Percentatge (%)" if tipus == "percentatge" else ("Euros" if tipus == "import_integre" else "Receptes")
        if tipus != "percentatge" and maxim >= 1_000_000:
            divisor = 1_000_000
            unitat = "Milions d’euros" if tipus == "import_integre" else "Milions de receptes"
        elif tipus != "percentatge" and maxim >= 1_000:
            divisor = 1_000
            unitat = "Milers d’euros" if tipus == "import_integre" else "Milers de receptes"
        eixos.xaxis.set_major_locator(MaxNLocator(nbins=3))
        eixos.xaxis.set_major_formatter(FuncFormatter(lambda valor, posicio: f"{valor / divisor:g}".replace(".", ",")))
        eixos.tick_params(axis="x", labelsize=9)
        eixos.set_xlabel(unitat, fontsize=10, labelpad=10)
        eixos.set_axisbelow(True)
        eixos.grid(axis="x", color="#edf1f4", linewidth=0.7)
        for costat in ("top", "right", "left"):
            eixos.spines[costat].set_visible(False)
        eixos.spines["bottom"].set_color("#bdcdd6")

    imatge = BytesIO()
    figura.savefig(imatge, format="png", dpi=120)
    imatge.seek(0)
    return imatge
