import pandas as pd
def guardar_productos_en_csv(productos):
    if productos:
        df = pd.DataFrame(productos)
        df.to_csv("productos_carrefour.csv", index=False, encoding="utf-8")
        print(f"✅ Se guardaron {len(df)} productos en productos_carrefour.csv")
    else:
        print("❌ No se extrajeron productos")
