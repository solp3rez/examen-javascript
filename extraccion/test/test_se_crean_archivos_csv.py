import sys
import pathlib
from utils import guardar_productos_en_csv

# Agrega la carpeta raíz del proyecto al PYTHONPATH
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.carrefour_scraper import obtener_productos_carrefour
from src.dia_scraper import obtener_productos_dia
from src.coto_scraper import obtener_productos_coto


archivos = [
    "productos_carrefour.csv",
    "productos_coto.csv",
    "productos_dia.csv",
]


def test_verificar_si_se_crean_archivos():
    for archivo in archivos:
        directorio = pathlib.Path("src", archivo)
        assert not directorio.exists()

    productos = obtener_productos_carrefour()
    guardar_productos_en_csv(productos)
    productos = obtener_productos_dia()
    guardar_productos_en_csv(productos)
    productos = obtener_productos_coto()
    guardar_productos_en_csv(productos)

    for archivo in archivos:
        directorio = pathlib.Path("src", archivo)
        assert not directorio.exists()
