import pika
import json
import time
import sys

# --- CONFIGURACIÓN ---
# CAMBIA ESTO por la IP de la computadora que tiene RabbitMQ (tu servidor)
RABBITMQ_HOST = '4.tcp.ngrok.io'  # Ejemplo de ngrok, cambia por la IP correcta
RABBITMQ_PORT = 17405             # Cambia por el puerto correcto de ng
USUARIO = 'MonteCarlo'
PASSWORD = '123'
# ---------------------

class MonteCarloConsumer:
    def __init__(self, consumer_id):
        self.consumer_id = consumer_id
        
        # Configurar credenciales y conexión
        credentials = pika.PlainCredentials(USUARIO, PASSWORD)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        
        print(f"Intentando conectar como {USUARIO}...")
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.function_code = None
        self.setup_queues()

    def setup_queues(self):
        try:
            self.channel.queue_declare(queue='function_queue', durable=True)
            self.channel.queue_declare(queue='scenario_queue', arguments={
                'x-message-ttl': 1000,
                'x-max-length': 1
            })
            self.channel.queue_declare(queue='results_queue')
            print(f"Consumidor {self.consumer_id}: Conexión exitosa y colas listas.")
        except pika.exceptions.ChannelClosedByBroker as e:
            print(f"Error de permisos o configuración: {e}")
            raise

    def load_function(self):
        method_frame, _, body = self.channel.basic_get('function_queue')
        if method_frame:
            self.function_code = body.decode()
            self.channel.basic_ack(method_frame.delivery_tag)
            print(f"Consumidor {self.consumer_id} cargó la función")
            return True
        return False

    def process_scenario(self, scenario):
        try:
            local_scope = {}
            exec(self.function_code, globals(), local_scope)
            for key, value in local_scope.items():
                if callable(value):
                    return value(**scenario)
            if 'funcion_ejemplo' in local_scope:
                return local_scope['funcion_ejemplo'](**scenario)
            return None
        except Exception as e:
            print(f"Error ejecutando función: {e}")
            return None

    def run(self):
        if not self.load_function():
            print(f"Consumidor {self.consumer_id}: Esperando función del servidor...")
            # Reintentar cargar función un par de veces si falla al inicio
            retry = 0
            while not self.load_function() and retry < 5:
                time.sleep(2)
                retry += 1
            if not self.function_code:
                print("No se pudo cargar la función. Asegúrate de que el Productor esté corriendo.")
                return

        print(f"Consumidor {self.consumer_id} LISTO y procesando...")
        
        while True:
            try:
                method_frame, _, body = self.channel.basic_get('scenario_queue')
                if method_frame:
                    scenario = json.loads(body)
                    result = self.process_scenario(scenario)
                    self.channel.basic_ack(method_frame.delivery_tag)
                    
                    if result is not None:
                        self.channel.basic_publish(
                            exchange='',
                            routing_key='results_queue',
                            body=json.dumps({
                                'consumer_id': self.consumer_id,
                                'result': result,
                                'scenario': scenario,
                                'timestamp': time.time()
                            })
                        )
                        print(f" [x] Procesado: {result}")
                else:
                    time.sleep(0.01) # Pequeña pausa para no saturar CPU si está vacío
            except Exception as e:
                print(f"Error en ciclo principal: {e}")
                time.sleep(1)

if __name__ == "__main__":
    # Usa el nombre de la PC o un argumento como ID
    import socket
    hostname = socket.gethostname()
    consumer_id = sys.argv[1] if len(sys.argv) > 1 else f"Node-{hostname}"
    
    try:
        consumer = MonteCarloConsumer(consumer_id)
        consumer.run()
    except Exception as e:
        print(f"FATAL: {e}")