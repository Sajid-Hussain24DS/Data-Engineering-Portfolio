from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.decorators import task
import pendulum
import requests

LATITUDE = '51.5074'
LONGITUDE = '-0.1278'
POSTGRES_CONN_ID = 'postgres_default'

default_args = {
    'owner': 'airflow',
    'start_date': pendulum.datetime(2026, 3, 4, tz="UTC"),
}

with DAG(
    dag_id='my_new_weather_dag',
    default_args=default_args,
    schedule='@daily',
    catchup=False
) as dag:

    @task()
    def extract_weather_data():
        url = f'https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&current_weather=true'
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch weather data: {response.status_code}")

    @task()
    def transform_weather_data(weather_data):
        current = weather_data['current_weather']
        return {
            'latitude': LATITUDE,
            'longitude': LONGITUDE,
            'temperature': current['temperature'],
            'windspeed': current['windspeed'],
            'winddirection': current['winddirection'],
            'weathercode': current['weathercode']
        }

    @task()
    def load_weather_data(data):
        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        conn = hook.get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS weather_data (
                latitude FLOAT,
                longitude FLOAT,
                temperature FLOAT,
                windspeed FLOAT,
                winddirection FLOAT,
                weathercode INT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            INSERT INTO weather_data (latitude, longitude, temperature, windspeed, winddirection, weathercode)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (data['latitude'], data['longitude'], data['temperature'], data['windspeed'], data['winddirection'], data['weathercode']))
        conn.commit()
        cur.close()

    data = extract_weather_data()
    transformed = transform_weather_data(data)
    load_weather_data(transformed)