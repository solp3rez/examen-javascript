import time
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
import pandas as pd

# --- CONFIGURACIÓN DEL DRIVER (Sin cambios) ---
def configurar_driver():
    # Opciones del navegador
    firefox_options = Options()
    # Se recomienda no usar --headless mientras se debugea
    # firefox_options.add_argument("--headless")  
    
    # Configura el servicio de geckodriver
    # NOTA: Si esto falla, debes verificar que GeckoDriver esté en esta ruta O en tu PATH.
    service = Service('/usr/local/bin/geckodriver')  
    driver = webdriver.Firefox(service=service, options=firefox_options)
    return driver

# --- FUNCIÓN DE SCRAPING CON SELECTORES CORREGIDOS ---
def obtener_productos_carrefour():
    # Carrefour utiliza clases dinámicas. Usaremos selectores basados en la estructura
    # conocida para apuntar a los elementos de precio y nombre.
    
    url = "https://www.carrefour.com.ar/almacen"
    driver = configurar_driver()
    driver.get(url)
    
    # Esperar que la página cargue, 5 segundos es un buen inicio
    time.sleep(5)
    
    # Desplazamiento (Scroll) para cargar más productos
    # Esto es crucial en sitios como Carrefour que usan "infinite scroll"
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3) # Esperar a que los nuevos productos se carguen

    # Obtener el HTML de la página cargada
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # Búsqueda más precisa del CONTENEDOR DE PRODUCTOS (ejemplo de clase VTEX)
    # Busca el div que contenga todos los productos en la grilla
    productos = soup.find_all("div", class_="vtex-search-result-3-x-galleryItem") 
    
    # Si la clase de arriba no funciona, puedes intentar con una más genérica:
    if not productos:
        productos = soup.find_all("div", class_=lambda x: x and "product-summary" in x)
        
    datos_productos = []
    
    print(f"Productos encontrados para analizar: {len(productos)}")

    for producto in productos:
        try:
            # 1. NOMBRE: Normalmente en un div con clase de nombre o en el atributo 'alt' de la imagen.
            # Buscamos la etiqueta 'img' y obtenemos el atributo 'alt'
            img_tag = producto.find("img", class_="vtex-product-summary-2-x-imageNormal")
            nombre = img_tag['alt'] if img_tag and 'alt' in img_tag.attrs else "Nombre no encontrado"

            # 2. PRECIO: Contenedor con precio final (clase de Carrefour/VTEX)
            # Buscamos el span que contiene el precio
            precio_tag = producto.find("span", class_="valtech-carrefourar-product-price-0-x-sellingPrice")
            precio = precio_tag.text.strip() if precio_tag else "Precio no encontrado"

            # 3. ENLACE: Buscamos la etiqueta 'a' (enlace) y obtenemos el atributo 'href'
            enlace_tag = producto.find("a", href=True)
            enlace = "https://www.carrefour.com.ar" + enlace_tag['href'] if enlace_tag else "Enlace no encontrado"
            
            # Solo añadir si se encontró algo útil
            if nombre != "Nombre no encontrado" and precio != "Precio no encontrado":
                 datos_productos.append({"nombre": nombre, "precio": precio, "enlace": enlace})
                 
        except Exception as e:
            # Capturamos errores específicos que pueden ocurrir si la estructura varía
            # print(f"Error al procesar un producto: {e}") 
            pass # Ignoramos productos que no se pueden parsear

    driver.quit()
    return datos_productos

# --- FUNCIONES RESTANTES (Sin cambios) ---
def guardar_productos_en_csv(productos):
    if productos:
        df = pd.DataFrame(productos)
        df.to_csv("productos_carrefour.csv", index=False, encoding="utf-8")
        print(f"✅ Se guardaron {len(df)} productos en productos_carrefour.csv")
    else:
        print("❌ No se extrajeron productos")

def main():
    productos = obtener_productos_carrefour()
    guardar_productos_en_csv(productos)
    print("\nPrimeros 5 productos extraídos:")
    print(productos[:5])  # Mostrar los primeros 5 productos

if __name__ == "__main__":
    main()