# Radiografia de la dispensació farmacèutica

He desenvolupat un dashboard amb Flask per explorar les receptes facturades al CatSalut a la regió sanitària Barcelona Ciutat durant el 2024.

## Aplicació publicada

https://ssabir1994.pythonanywhere.com

## Objectiu

Analitzar tres preguntes:

- Com es reparteixen les receptes entre edats i sexes?
- Les categories amb més receptes també concentren més import?
- Com canvien les receptes i l’import durant l’any?

## Dades

Font oficial: [Receptes facturades al Servei Català de la Salut](https://analisi.transparenciacatalunya.cat/d/thrd-jj3r).

El fitxer utilitzat conté 128.863 registres agregats de Barcelona Ciutat del 2024. Cada fila correspon a un mes, una franja d’edat, un sexe i un subgrup terapèutic. No representa una persona individual.

El CSV es troba a:

`data/receptes_catsalut_barcelona_ciutat_2024.csv`

## Funcionalitats

- Filtres combinables de mes, categoria, edat i sexe.
- Indicadors de receptes, envasos, import íntegre i aportació del CatSalut.
- Tres gràfiques generades amb Matplotlib.
- Taula de categories amb ordenació per diverses columnes.
- Registres paginats amb detall desplegable.
- Presentació adaptada a escriptori i mòbil.

Els indicadors i els registres respecten els quatre filtres. La comparativa de categories manté totes les categories del mateix període, edat i sexe. La comparativa mensual manté tot el 2024 per a la categoria, edat i sexe seleccionats.

## Organització

- `app.py`: rutes i respostes de l’aplicació.
- `services/data_service.py`: lectura, filtres i càlculs.
- `services/graph_service.py`: gràfiques amb Matplotlib.
- `templates/dashboard.html`: presentació dinàmica amb Jinja.
- `static/styles.css`: estils i adaptació a la pantalla.

## Execució local en Windows

Amb Python 3.10 instal·lat, des de la carpeta del projecte:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app app run --debug
```

Obrir http://127.0.0.1:5000 al navegador.

El hosting també utilitza Python 3.10.