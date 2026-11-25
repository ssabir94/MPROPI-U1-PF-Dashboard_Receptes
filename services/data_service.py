import csv
import os
from decimal import Decimal, InvalidOperation
from functools import lru_cache


def convertir_enter(valor):
    """Convertir un enter amb possibles punts de milers."""

    # Eliminar els espais dels extrems i els separadors de milers.
    text = valor.strip().replace(".", "")
    nombre = int(text)

    # Comprovar que el recompte no sigui negatiu.
    if nombre < 0:
        raise ValueError("El recompte no pot ser negatiu.")

    return nombre


def convertir_import(valor):
    """Convertir un import del format català a Decimal."""

    # Transformar, per exemple, '3.853,14' en '3853.14'.
    text = valor.strip().replace(".", "").replace(",", ".")
    # Utilitzar Decimal per sumar i dividir imports amb precisió decimal,
    # sense introduir les aproximacions binàries pròpies de float.
    nombre = Decimal(text)

    # Acceptar imports zero i impedir valors negatius o no finits.
    if not nombre.is_finite() or nombre < 0:
        raise ValueError("L'import ha de ser un nombre finit no negatiu.")

    return nombre


# Reutilitzar el CSV preparat per evitar rellegir-lo per a cada gràfica.
# Reiniciar el servidor si es modifica el CSV, perquè la memòria cau és del procés.
# Tractar els diccionaris retornats com a dades compartides: no modificar-los en filtrar.
@lru_cache(maxsize=1)
def carregar_dades():
    """Llegir i preparar el CSV una vegada per procés."""

    # Localitzar la carpeta principal del projecte.
    carpeta_projecte = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    # Construir la ruta al CSV.
    ruta_csv = os.path.join(
        carpeta_projecte,
        "data",
        "receptes_catsalut_barcelona_ciutat_2024.csv",
    )

    registres = []

    # Utilitzar utf-8-sig per acceptar també un CSV amb marca BOM:
    # evitar que aquesta marca quedi afegida al nom de la primera columna.
    # Llegir el fitxer sense modificar-ne el contingut.
    with open(ruta_csv, mode="r", encoding="utf-8-sig", newline="") as fitxer:
        lector = csv.DictReader(fitxer)

        # Començar a la fila 2 perquè la primera conté les capçaleres.
        for fila_csv, registre in enumerate(lector, start=2):
            try:
                # Convertir el període a nombres enters.
                registre["any"] = int(registre["any"])
                registre["mes"] = int(registre["mes"])

                # Verificar el període i la regió acordats.
                if registre["any"] != 2024:
                    raise ValueError("L'any ha de ser 2024.")

                if not 1 <= registre["mes"] <= 12:
                    raise ValueError("El mes ha d'estar entre 1 i 12.")

                if registre["regió sanitària"] != "BARCELONA CIUTAT":
                    raise ValueError("La regió ha de ser BARCELONA CIUTAT.")

                # Convertir les quantitats a enters.
                for camp in ("nombre de receptes", "nombre d'envasos"):
                    registre[camp] = convertir_enter(registre[camp])

                # Convertir els imports amb precisió decimal.
                for camp in ("import íntegre", "import aportació CatSalut"):
                    registre[camp] = convertir_import(registre[camp])

            except (ValueError, InvalidOperation, TypeError, AttributeError, KeyError) as error:
                # Identificar la fila problemàtica sense inventar valors.
                raise ValueError(
                    f"No s'ha pogut preparar la fila {fila_csv}: {error}"
                ) from error

            registres.append(registre)

    return registres

def calcular_resum(registres):
    """Calcular els indicadors globals dels registres rebuts."""

    # Sumar la columna de receptes perquè cada fila ja és un recompte agregat:
    # no confondre el nombre de registres amb el nombre de receptes.
    # Sumar les quantitats de totes les files.
    total_receptes = sum(
        registre["nombre de receptes"] for registre in registres
    )

    total_envasos = sum(
        registre["nombre d'envasos"] for registre in registres
    )

    # Iniciar les sumes monetàries amb Decimal per mantenir el tipus.
    import_integre = sum(
        (registre["import íntegre"] for registre in registres),
        Decimal("0"),
    )

    aportacio_catsalut = sum(
        (registre["import aportació CatSalut"] for registre in registres),
        Decimal("0"),
    )

    # Agrupar els resultats en un diccionari.
    return {
        "total_registres": len(registres),
        "total_receptes": total_receptes,
        "total_envasos": total_envasos,
        "import_integre": import_integre,
        "aportacio_catsalut": aportacio_catsalut,
    }

def filtrar_per_mes(registres, mes_text):
    """Retornar els registres del mes seleccionat."""

    # Mostrar tots els mesos si no hi ha cap selecció.
    if mes_text == "":
        return registres

    # Acceptar només els valors previstos al formulari.
    mesos_permesos = {str(mes) for mes in range(1, 13)}

    if mes_text not in mesos_permesos:
        raise ValueError("El mes seleccionat no és vàlid.")

    # Convertir el paràmetre de la URL a enter per comparar-lo.
    mes = int(mes_text)

    return [
        registre
        for registre in registres
        if registre["mes"] == mes
    ]

def obtenir_grups_terapeutics(registres):
    """Obtenir els codis i noms únics dels grups ATC de nivell 1."""

    grups = {}

    for registre in registres:
        codi = registre["codi del grup ATC nivell 1"]
        nom = registre["grup ATC nivell 1"]

        # Desar una única entrada per codi.
        grups[codi] = nom

    # Retornar les parelles de codi i nom ordenades pel nom.
    return sorted(grups.items(), key=lambda grup: grup[1])


def filtrar_dades(
    registres,
    mes_text,
    grup_seleccionat,
    edat_seleccionada="",
    sexe_seleccionat="",
):
    """Aplicar els filtres de mes, grup terapèutic, edat i sexe."""

    # Obtenir els valors permesos de les dades originals.
    codis_permesos = {
        registre["codi del grup ATC nivell 1"]
        for registre in registres
    }

    edats_permeses = {
        registre["grup d'edat"]
        for registre in registres
    }

    sexes_permesos = {
        registre["sexe"]
        for registre in registres
    }

    # Validar les seleccions rebudes des de la URL.
    if grup_seleccionat and grup_seleccionat not in codis_permesos:
        raise ValueError("El grup terapèutic seleccionat no és vàlid.")

    if edat_seleccionada and edat_seleccionada not in edats_permeses:
        raise ValueError("El grup d'edat seleccionat no és vàlid.")

    if sexe_seleccionat and sexe_seleccionat not in sexes_permesos:
        raise ValueError("El sexe seleccionat no és vàlid.")

    # Reutilitzar la validació i el filtre de mes.
    filtrats = filtrar_per_mes(registres, mes_text)

    # Exigir que cada registre compleixi totes les seleccions actives.
    return [
        registre
        for registre in filtrats
        if (
            not grup_seleccionat
            or registre["codi del grup ATC nivell 1"] == grup_seleccionat
        )
        and (
            not edat_seleccionada
            or registre["grup d'edat"] == edat_seleccionada
        )
        and (
            not sexe_seleccionat
            or registre["sexe"] == sexe_seleccionat
        )
    ]

def resumir_per_grup(registres):
    """Agrupar receptes i imports per grup ATC de nivell 1."""

    grups = {}

    for registre in registres:
        codi = registre["codi del grup ATC nivell 1"]

        # Preparar els acumuladors la primera vegada que apareix el grup.
        if codi not in grups:
            grups[codi] = {
                "codi": codi,
                "nom": registre["grup ATC nivell 1"],
                "receptes": 0,
                "import_integre": Decimal("0"),
            }

        # Acumular les mesures de cada registre al seu grup.
        grups[codi]["receptes"] += registre["nombre de receptes"]
        grups[codi]["import_integre"] += registre["import íntegre"]

    # Calcular els percentatges sobre els registres rebuts. A la comparativa,
    # rebre totes les categories del mateix mes, edat i sexe per mantenir
    # el mateix denominador a la gràfica i a la taula.
    # Obtenir els totals de la selecció per calcular els percentatges.
    totals = calcular_resum(registres)

    for grup in grups.values():
        # Calcular el pes del grup dins de les receptes seleccionades.
        if totals["total_receptes"] > 0:
            grup["percentatge_receptes"] = (
                Decimal(grup["receptes"])
                / Decimal(totals["total_receptes"])
                * 100
            )
        else:
            grup["percentatge_receptes"] = Decimal("0")

        # Calcular el pes del grup dins de l'import seleccionat.
        if totals["import_integre"] > 0:
            grup["percentatge_import"] = (
                grup["import_integre"]
                / totals["import_integre"]
                * 100
            )
        else:
            grup["percentatge_import"] = Decimal("0")

        # Dividir la suma d’imports per la suma de receptes per donar a cada
        # recepta el mateix pes; evitar fer la mitjana de les mitjanes de cada fila.
        # Evitar presentar com a zero una mitjana que no es pot calcular.
        if grup["receptes"] > 0:
            grup["import_mitja_recepta"] = (
                grup["import_integre"] / Decimal(grup["receptes"])
            )
        else:
            grup["import_mitja_recepta"] = None

    # Presentar primer els grups amb més receptes.
    return sorted(
        grups.values(),
        key=lambda grup: grup["receptes"],
        reverse=True,
    )

def ordenar_grups(grups, columna, sentit):
    """Ordenar la comparació per una columna permesa."""

    columnes_permeses = {
        "receptes",
        "import_integre",
        "import_mitja_recepta",
        "nom",
    }

    # Validar els paràmetres abans d'utilitzar-los.
    if columna not in columnes_permeses:
        raise ValueError("La columna d'ordenació no és vàlida.")

    if sentit not in {"asc", "desc"}:
        raise ValueError("El sentit d'ordenació no és vàlid.")

    # Separar els grups sense valor calculable per situar-los al final.
    amb_valor = [
        grup for grup in grups
        if grup[columna] is not None
    ]

    sense_valor = [
        grup for grup in grups
        if grup[columna] is None
    ]

    # Utilitzar el codi com a segon criteri si hi ha un empat.
    ordenats = sorted(
        amb_valor,
        key=lambda grup: (grup[columna], grup["codi"]),
        reverse=(sentit == "desc"),
    )

    return ordenats + sense_valor

def obtenir_opcions_poblacio(registres):
    """Obtenir les edats i els sexes disponibles al CSV."""

    # Eliminar les repeticions mitjançant conjunts.
    edats = {registre["grup d'edat"] for registre in registres}
    sexes = {registre["sexe"] for registre in registres}

    # Ordenar les franges pel límit inferior.
    # Situar «Més de 84 anys» després de les franges numèriques.
    edats_ordenades = sorted(
        edats,
        key=lambda edat: (
            int(edat.split("-")[0])
            if edat[0].isdigit()
            else float("inf")
        ),
    )

    return {
        "edats": edats_ordenades,
        "sexes": sorted(sexes),
    }

def paginar_registres(registres, pagina_text, per_pagina=25):
    """Preparar una pàgina de registres i la informació de navegació."""

    # Validar el número de pàgina rebut des de la URL.
    try:
        pagina = int(pagina_text)
    except (ValueError, TypeError):
        raise ValueError("El número de pàgina ha de ser un enter.")

    if pagina < 1:
        raise ValueError("El número de pàgina ha de ser positiu.")

    total_registres = len(registres)

    # Calcular les pàgines necessàries arrodonint cap amunt.
    # Mantenir una pàgina buida si no hi ha resultats.
    total_pagines = max(
        1,
        (total_registres + per_pagina - 1) // per_pagina,
    )

    # Limitar la pàgina sol·licitada a l'última disponible.
    pagina = min(pagina, total_pagines)

    # Calcular els índexs del fragment que s'ha de mostrar.
    inici = (pagina - 1) * per_pagina
    final = inici + per_pagina

    return {
        "registres": registres[inici:final],
        "pagina": pagina,
        "total_pagines": total_pagines,
        "total_registres": total_registres,
        "primer": inici + 1 if total_registres else 0,
        "ultim": min(final, total_registres),
    }

def resumir_per_mes(registres):
    """Acumular les receptes i l'import íntegre de cada mes."""

    mesos = {}

    for registre in registres:
        mes = registre["mes"]

        # Preparar els acumuladors quan apareix un mes.
        if mes not in mesos:
            mesos[mes] = {
                "mes": mes,
                "receptes": 0,
                "import_integre": Decimal("0"),
            }

        # Acumular les mesures dels registres seleccionats.
        mesos[mes]["receptes"] += registre["nombre de receptes"]
        mesos[mes]["import_integre"] += registre["import íntegre"]

    # Retornar els mesos en ordre cronològic.
    return sorted(
        mesos.values(),
        key=lambda resum_mes: resum_mes["mes"],
    )

def resumir_per_edat_sexe(registres):
    """Agrupar les receptes per sexe i cinc franges de presentació."""

    # Definir quines franges originals formen cada agrupació.
    franges = {
        "0-19 anys": [
            "0-1 any", "2-3 anys", "4-5 anys", "6-7 anys",
            "8-9 anys", "10-11 anys", "12-13 anys",
            "14-15 anys", "16-17 anys", "18-19 anys",
        ],
        "20-39 anys": [
            "20-24 anys", "25-29 anys",
            "30-34 anys", "35-39 anys",
        ],
        "40-59 anys": [
            "40-44 anys", "45-49 anys",
            "50-54 anys", "55-59 anys",
        ],
        "60-79 anys": [
            "60-64 anys", "65-69 anys",
            "70-74 anys", "75-79 anys",
        ],
        "80 anys o més": [
            "80-84 anys", "Més de 84 anys",
        ],
    }

    # Relacionar cada franja original amb la seva agrupació.
    equivalencies = {
        edat: franja
        for franja, edats in franges.items()
        for edat in edats
    }

    acumulats = {}

    for registre in registres:
        edat_original = registre["grup d'edat"]
        sexe = registre["sexe"]

        # Impedir que una categoria desconeguda quedi fora del recompte.
        if edat_original not in equivalencies:
            raise ValueError(f"Franja d'edat desconeguda: {edat_original}")

        if sexe not in {"Dona", "Home"}:
            raise ValueError(f"Valor de sexe desconegut: {sexe}")

        franja = equivalencies[edat_original]

        if franja not in acumulats:
            acumulats[franja] = {
                "Dona": 0,
                "Home": 0,
                "edats_originals": set(),
            }

        # Sumar les receptes sense modificar els registres originals.
        acumulats[franja][sexe] += registre["nombre de receptes"]
        acumulats[franja]["edats_originals"].add(edat_original)

    resultat = []

    # Mantenir l'ordre de les cinc agrupacions.
    for franja in franges:
        if franja not in acumulats:
            continue

        dades = acumulats[franja]
        edats_incloses = dades["edats_originals"]

        # Mostrar l'edat exacta si la selecció només conté una franja original.
        etiqueta = (
            next(iter(edats_incloses))
            if len(edats_incloses) == 1
            else franja
        )

        resultat.append({
            "edat": etiqueta,
            "Dona": dades["Dona"],
            "Home": dades["Home"],
        })

    return resultat

def preparar_contextos(
    registres, mes_seleccionat, grup_seleccionat,
    edat_seleccionada="", sexe_seleccionat="",
):
    """Distingir la selecció exacta dels dos àmbits de comparació."""
    # Validar tots els filtres, inclosos els que s'amplien a les comparatives.
    seleccio = filtrar_dades(
        registres, mes_seleccionat, grup_seleccionat,
        edat_seleccionada, sexe_seleccionat,
    )
    # Ampliar només la dimensió que es compara; mantenir les altres.
    # Retirar el filtre de categoria únicament a la comparativa de categories:
    # conservar el mes, l’edat i el sexe per comparar dades equivalents.
    categories = (
        filtrar_dades(registres, mes_seleccionat, "", edat_seleccionada, sexe_seleccionat)
        if grup_seleccionat else seleccio
    )
    # Retirar el filtre de mes únicament a la comparativa anual; conservar
    # la categoria, l’edat i el sexe. La ruta utilitzarà el mes per ressaltar-lo.
    mesos = (
        filtrar_dades(registres, "", grup_seleccionat, edat_seleccionada, sexe_seleccionat)
        if mes_seleccionat else seleccio
    )
    return {"seleccio": seleccio, "categories": categories, "mesos": mesos}


def obtenir_destacats_mensuals(resum_mensual, mesura):
    """Localitzar els extrems observats de la mesura, sense atribuir-ne causes."""
    if mesura not in {"receptes", "import_integre"}:
        raise ValueError("La mesura seleccionada no és vàlida.")
    if not resum_mensual:
        return None

    # Conservar tots els mesos empatats als extrems i utilitzar només mesos
    # amb registres; no inventar un mínim zero per a un mes absent del fitxer.
    maxim = max(fila[mesura] for fila in resum_mensual)
    minim = min(fila[mesura] for fila in resum_mensual)
    return {
        "maxim": maxim,
        "minim": minim,
        "mesos_maxim": [fila["mes"] for fila in resum_mensual if fila[mesura] == maxim],
        "mesos_minim": [fila["mes"] for fila in resum_mensual if fila[mesura] == minim],
        "mesos_amb_registres": len(resum_mensual),
    }


def comptar_incidencies_import(registres):
    """Comptar discrepàncies informades sense alterar ni interpretar-ne la causa."""
    return sum(
        registre["import aportació CatSalut"] > registre["import íntegre"]
        for registre in registres
    )
