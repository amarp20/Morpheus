from app import mongo
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Acepta conexiones externas si lo deseas: host='0.0.0.0'
    app.run(debug=True, host='0.0.0.0')
