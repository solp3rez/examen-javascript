import pathlib
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

    obtener_productos_carrefour()
    obtener_productos_dia()
    obtener_productos_coto()
    for archivo in archivos:
        directorio = pathlib.Path("src", archivo)
        assert not directorio.exists() 
