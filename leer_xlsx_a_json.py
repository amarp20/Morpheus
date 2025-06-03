import pandas as pd

# Cargar los datos desde el archivo Excel
df = pd.read_excel('lista_camas.xlsx')

# Reemplazar valores 'null' (como cadena) por cadena vacía
df.replace("null", "", inplace=True)

# (Opcional) También puedes reemplazar valores None o NaN por ""
df.fillna("", inplace=True)

# Exportar a JSON
df.to_json('listado_camas2.json', orient='records', indent=4)
