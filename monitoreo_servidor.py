import psutil
import time
import csv
import requests
from datetime import datetime
from prometheus_client import Gauge, start_http_server


INTERVALO_SEGUNDOS = 10  # Cada cuánto se recolectan las métricas

# 🔹 ENDPOINTS a monitorear (tu sitio principal)
ENDPOINTS = [
    "https://184.168.28.51/index.aspx"
]

ARCHIVO_SALIDA = "metrics.csv"

# UMBRALES DE ALERTA
CPU_WARNING = 80
CPU_CRITICO = 90
RAM_WARNING = 75
RAM_CRITICO = 90
DISCO_WARNING = 80
DISCO_CRITICO = 95
LATENCIA_WARNING = 2
LATENCIA_CRITICA = 5

# ==========================
# MÉTRICAS PROMETHEUS
# ==========================

cpu_gauge = Gauge('system_cpu_percent', 'Uso de CPU (%)')
ram_gauge = Gauge('system_ram_percent', 'Uso de memoria RAM (%)')
disk_gauge = Gauge('system_disk_percent', 'Uso de disco (%)')
net_sent_gauge = Gauge('network_bytes_sent', 'Bytes enviados por la red')
net_recv_gauge = Gauge('network_bytes_recv', 'Bytes recibidos por la red')

endpoint_up = Gauge('endpoint_up', 'Disponibilidad del endpoint (1=OK, 0=Caído)', ['endpoint'])
endpoint_latency = Gauge('endpoint_latency_seconds', 'Latencia del endpoint en segundos', ['endpoint'])

# ==========================
# FUNCIONES DE MONITOREO
# ==========================

def medir_recursos():
    """Mide uso de CPU, memoria, disco y red"""
    cpu = psutil.cpu_percent(interval=1)
    memoria = psutil.virtual_memory().percent
    disco = psutil.disk_usage('/').percent
    red = psutil.net_io_counters()
    enviados = red.bytes_sent
    recibidos = red.bytes_recv

    # Actualizar métricas Prometheus
    cpu_gauge.set(cpu)
    ram_gauge.set(memoria)
    disk_gauge.set(disco)
    net_sent_gauge.set(enviados)
    net_recv_gauge.set(recibidos)

    return cpu, memoria, disco, enviados, recibidos


def verificar_endpoint(url):
    """Verifica si un endpoint está disponible y mide latencia"""
    inicio = time.time()
    try:
        respuesta = requests.get(url, timeout=10, verify=False)
        latencia = time.time() - inicio
        disponible = respuesta.status_code == 200
    except Exception:
        disponible = False
        latencia = None

    # Actualizar métricas Prometheus
    endpoint_up.labels(endpoint=url).set(1 if disponible else 0)
    endpoint_latency.labels(endpoint=url).set(latencia if latencia else 0)

    return disponible, latencia


def registrar_csv(data):
    """Guarda métricas en CSV"""
    encabezado = [
        "Fecha", "CPU (%)", "RAM (%)", "Disco (%)",
        "Bytes Enviados", "Bytes Recibidos", "Endpoint",
        "Disponible", "Latencia (s)"
    ]

    archivo_existe = False
    try:
        with open(ARCHIVO_SALIDA, "r", encoding="utf-8") as _:
            archivo_existe = True
    except FileNotFoundError:
        archivo_existe = False

    with open(ARCHIVO_SALIDA, "a", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        if not archivo_existe:
            writer.writerow(encabezado)
        writer.writerow(data)


def mostrar_alertas(cpu, ram, disco, endpoint, disponible, latencia):
    """Muestra alertas en consola según umbrales"""
    if cpu >= CPU_CRITICO:
        print(f"⚠️ ALERTA CRÍTICA: CPU al {cpu}%")
    elif cpu >= CPU_WARNING:
        print(f"⚠️ Aviso: CPU al {cpu}%")

    if ram >= RAM_CRITICO:
        print(f"⚠️ ALERTA CRÍTICA: RAM al {ram}%")
    elif ram >= RAM_WARNING:
        print(f"⚠️ Aviso: RAM al {ram}%")

    if disco >= DISCO_CRITICO:
        print(f"⚠️ ALERTA CRÍTICA: Disco al {disco}%")
    elif disco >= DISCO_WARNING:
        print(f"⚠️ Aviso: Disco al {disco}%")

    if not disponible:
        print(f"🚫 Endpoint caído: {endpoint}")
    elif latencia and latencia > LATENCIA_CRITICA:
        print(f"⚠️ Latencia crítica en {endpoint}: {latencia:.2f} s")
    elif latencia and latencia > LATENCIA_WARNING:
        print(f"⚠️ Latencia alta en {endpoint}: {latencia:.2f} s")


# ==========================
# BUCLE PRINCIPAL
# ==========================

if __name__ == "__main__":
    print("=== Iniciando Monitor del Servidor ===")
    print("Servidor de métricas Prometheus en: http://0.0.0.0:8000/metrics")
    print("Presiona Ctrl + C para detener...\n")

    # Servidor HTTP accesible desde cualquier IP
    start_http_server(8000)

    try:
        while True:
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cpu, memoria, disco, enviados, recibidos = medir_recursos()

            for endpoint in ENDPOINTS:
                disponible, latencia = verificar_endpoint(endpoint)
                mostrar_alertas(cpu, memoria, disco, endpoint, disponible, latencia)

                datos = [
                    fecha, cpu, memoria, disco, enviados,
                    recibidos, endpoint, disponible,
                    latencia if latencia else "N/A"
                ]
                registrar_csv(datos)

            print(f"[{fecha}] CPU: {cpu}% | RAM: {memoria}% | Disco: {disco}%")
            time.sleep(INTERVALO_SEGUNDOS)

    except KeyboardInterrupt:
        print("\n🟡 Monitoreo finalizado por el usuario.")
