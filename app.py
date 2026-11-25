# Coordinar les peticions web des d’aquest fitxer i delegar els càlculs
# als serveis per mantenir separades les rutes, les dades i les gràfiques.
from flask import Flask, abort, render_template, request, send_file

from services.data_service import (
    carregar_dades,
    calcular_resum,
    obtenir_grups_terapeutics,
    obtenir_opcions_poblacio,
    filtrar_dades,
    resumir_per_grup,
    ordenar_grups,
    paginar_registres,
    resumir_per_mes,
    resumir_per_edat_sexe,
    preparar_contextos,
    obtenir_destacats_mensuals,
    comptar_incidencies_import,
)
from services.graph_service import (
    crear_grafica_grups,
    crear_grafica_mensual,
    crear_grafica_edat_sexe,
)


# Crear l'aplicació Flask.
app = Flask(__name__)


@app.route("/")
def dashboard():
    # Utilitzar paràmetres GET per conservar els filtres a la URL
    # i permetre tornar a obrir o compartir la mateixa consulta.
    # Recuperar els filtres i les opcions de presentació.
    mes_seleccionat = request.args.get("mes", "")
    grup_seleccionat = request.args.get("grup", "")
    edat_seleccionada = request.args.get("edat", "")
    sexe_seleccionat = request.args.get("sexe", "")
    ordre = request.args.get("ordre", "receptes")
    sentit = request.args.get("sentit", "desc")
    pagina_text = request.args.get("pagina", "1")
    mesura_mensual = request.args.get("mesura_mensual", "receptes")

    # Validar l'opció de presentació rebuda.
    if mesura_mensual not in {"receptes", "import_integre"}:
        abort(400, description="La mesura seleccionada no és vàlida.")

    registres = carregar_dades()
    grups = obtenir_grups_terapeutics(registres)
    opcions_poblacio = obtenir_opcions_poblacio(registres)

    try:
        # Preparar separadament els totals filtrats i les dades comparades:
        # evitar comparar una categoria només amb ella mateixa o un sol mes.
        contextos = preparar_contextos(
            registres, mes_seleccionat, grup_seleccionat,
            edat_seleccionada, sexe_seleccionat,
        )
        registres_filtrats = contextos["seleccio"]
        comparacio_grups = resumir_per_grup(contextos["categories"])
        resum_comparacio = calcular_resum(contextos["categories"])
        resum_mensual = resumir_per_mes(contextos["mesos"])
        destacats_mensuals = obtenir_destacats_mensuals(resum_mensual, mesura_mensual)

        comparacio_grups = ordenar_grups(
            comparacio_grups,
            ordre,
            sentit,
        )

        # Limitar només les files visibles, sense reduir els totals
        # als 25 registres de la pàgina actual.
        paginacio = paginar_registres(
            registres_filtrats,
            pagina_text,
        )

    except ValueError as error:
        abort(400, description=str(error))

    resum = calcular_resum(registres_filtrats)

    # Passar els resultats a Jinja i deixar la presentació a la plantilla.
    # Mantenir l’escapament automàtic dels valors dins de l’HTML.
    return render_template(
        "dashboard.html",
        titol="Radiografia de la dispensació farmacèutica",
        resum=resum,
        resum_comparacio=resum_comparacio,
        destacats_mensuals=destacats_mensuals,
        incidencies_import=comptar_incidencies_import(registres),
        paginacio=paginacio,
        mes_seleccionat=mes_seleccionat,
        grup_seleccionat=grup_seleccionat,
        edat_seleccionada=edat_seleccionada,
        sexe_seleccionat=sexe_seleccionat,
        grups=grups,
        edats=opcions_poblacio["edats"],
        sexes=opcions_poblacio["sexes"],
        comparacio_grups=comparacio_grups,
        ordre=ordre,
        sentit=sentit,
        mesura_mensual=mesura_mensual,
    )


@app.route("/grafica-grups.png")
def grafica_grups():
    # Comparar totes les categories i ressaltar la seleccionada.
    # Rebre la vista com una opció de presentació, sense canviar els filtres ni els càlculs.
    grup_seleccionat = request.args.get("grup", "")
    registres = carregar_dades()
    try:
        contextos = preparar_contextos(
            registres, request.args.get("mes", ""), grup_seleccionat,
            request.args.get("edat", ""), request.args.get("sexe", ""),
        )
        comparacio = resumir_per_grup(contextos["categories"])
        imatge = crear_grafica_grups(
            comparacio, grup_seleccionat,
            vista=request.args.get("vista", "escriptori"),
        )
    except ValueError as error:
        abort(400, description=str(error))
    # Enviar al navegador el PNG generat al backend; indicar max_age=0 per demanar
    # la revalidació de la imatge en lloc de reutilitzar-la sense comprovar-la.
    return send_file(imatge, mimetype="image/png", max_age=0)


@app.route("/grafica-mensual.png")
def grafica_mensual():
    # Mantenir el context anual i ressaltar el mes del filtre global.
    registres = carregar_dades()
    mes_seleccionat = request.args.get("mes", "")
    try:
        contextos = preparar_contextos(
            registres, mes_seleccionat, request.args.get("grup", ""),
            request.args.get("edat", ""), request.args.get("sexe", ""),
        )
        resum_mensual = resumir_per_mes(contextos["mesos"])
        imatge = crear_grafica_mensual(
            resum_mensual, request.args.get("mesura_mensual", "receptes"),
            mes_seleccionat,
            vista=request.args.get("vista", "escriptori"),
        )
    except ValueError as error:
        abort(400, description=str(error))
    return send_file(imatge, mimetype="image/png", max_age=0)


@app.route("/grafica-edat-sexe.png")
def grafica_edat_sexe():
    # Recuperar el sexe per filtrar les dades i les sèries visibles.
    sexe_seleccionat = request.args.get("sexe", "")
    registres = carregar_dades()

    try:
        registres_filtrats = filtrar_dades(
            registres,
            request.args.get("mes", ""),
            request.args.get("grup", ""),
            request.args.get("edat", ""),
            sexe_seleccionat,
        )
        resum_edats = resumir_per_edat_sexe(registres_filtrats)
        imatge = crear_grafica_edat_sexe(
            resum_edats, sexe_seleccionat,
            vista=request.args.get("vista", "escriptori"),
        )
    except ValueError as error:
        abort(400, description=str(error))

    return send_file(
        imatge,
        mimetype="image/png",
        max_age=0,
    )
