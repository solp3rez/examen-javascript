import time
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
import pandas as pd


# Configura el WebDriver (usando Firefox)
def configurar_driver():
    # Opciones del navegador
    firefox_options = Options()
    # firefox_options.add_argument(
    #     "--headless"
    # )  # Ejecutar sin abrir ventana (modo "headless")

    # Configura el servicio de geckodriver
    # service = Service('/usr/local/bin/geckodriver')  # La ruta de geckodriver
    driver = webdriver.Firefox()
    return driver


# Obtener los productos de Coto usando Selenium
def obtener_productos_coto():
    url = "https://www.cotodigital.com.ar/sitios/cdigi/categoria/catalogo-almac%C3%A9n-golosinas/_/N-1y5dh9i"
    driver = configurar_driver()
    driver.get(url)

    # Esperar que la página cargue
    time.sleep(5)

    # Obtener el HTML de la página cargada
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Buscar todos los productos
    productos = soup.find_all("catalogue-product")
    datos_productos = []

    for producto in productos:
        try:
            nombre = producto.find("h3").text
            precio = producto.find("h4").text
            enlace = "https://www.cotodigital.com.ar" + producto.find("a")["href"]
            datos_productos.append(
                {"nombre": nombre, "precio": precio, "enlace": enlace}
            )
        except Exception as e:
            print(f"Error: {e}")

    # Cerrar el navegador
    driver.quit()

    return datos_productos


# Guardar los productos en un archivo CSV
def guardar_productos_en_csv(productos):
    if productos:
        df = pd.DataFrame(productos)
        df.to_csv("productos_coto.csv", index=False, encoding="utf-8")
        print(f"✅ Se guardaron {len(df)} productos en productos_coto.csv")
    else:
        print("❌ No se extrajeron productos")


# Función principal
def main():
    productos = obtener_productos_coto()
    guardar_productos_en_csv(productos)
    print(productos[:5])  # Mostrar los primeros 5 productos


if __name__ == "__main__":
    main()
