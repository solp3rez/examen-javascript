import requests
from bs4 import BeautifulSoup
import pandas as pd

print("Iniciando extracción de productos de Supermercados DIA...\n")

# URL del sitio DIA (categoría leches descremadas)
url = "https://diaonline.supermercadosdia.com.ar/frescos/leches/leches-descremadas"
headers = {"User-Agent": "Mozilla/5.0"}

# Hacer la solicitud HTTP
response = requests.get(url, headers=headers)
if response.status_code != 200:
    print("Error al acceder al sitio:", response.status_code)
    exit()

# Analizar el HTML con BeautifulSoup
soup = BeautifulSoup(response.text, "html.parser")

# Buscar el contenedor principal de productos (prueba ambas clases posibles)
contenedor = soup.find("div", class_="flex mt0 mb0 pt0 pb8 justify-start vtex-flex-layout-0-x-flexRowContent vtex-flex-layout-0-x-flexRowContent--grid_products items-stretch w-100")

if not contenedor:
    contenedor = soup.find("div", class_="diaio-search-result-0-x-gallery diaio-search-result-0-x-gallery--default flex flex-row flex-wrap items-stretch bn ph1 na4 pl9-l")

if not contenedor:
    print("❌ No se encontró el contenedor principal de productos.")
    exit()

# Buscar los productos dentro del contenedor
productos_html = contenedor.find_all("div", class_="vtex-product-summary-2-x-container")

productos = []

# Recorrer cada producto encontrado
for p in productos_html:
    nombre_tag = p.find("span", class_="vtex-store-components-3-x-productBrand")
    precio_tag = p.find("span", class_="vtex-product-price-1-x-sellingPriceValue")

    if nombre_tag and precio_tag:
        nombre = nombre_tag.text.strip()
        precio = precio_tag.text.strip()
        link_tag = p.find("a", class_="vtex-product-summary-2-x-clearLink")
        url_producto = (
            "https://diaonline.supermercadosdia.com.ar" + link_tag.get("href")
            if link_tag and link_tag.get("href")
            else "N/A"
        )

        productos.append({
            "Supermercado": "DIA",
            "Producto": nombre,
            "Precio": precio,
            "URL": url_producto
        })

# Crear DataFrame
df = pd.DataFrame(productos)

# Guardar en CSV
df.to_csv("productos_dia.csv", index=False)

# Mostrar resultados
print(f"✅ Se extrajeron {len(df)} productos del sitio DIA.")
print("📄 Archivo generado: productos_dia.csv\n")
print(df.head())
