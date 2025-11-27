import pika
import random
import time
import json

# --- CONFIGURACIÓN ---
USUARIO = 'guest'
PASSWORD = 'guest'
HOST = 'localhost' # Como el productor está en el servidor, usamos localhost
# ---------------------

class ScenarioProducer:
    def __init__(self, config_file, function_file):
        self.config = self.load_config(config_file)
        self.function = self.load_function(function_file)
        
        # Conexión autenticada
        credentials = pika.PlainCredentials(USUARIO, PASSWORD)
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=HOST, credentials=credentials)
        )
        self.channel = self.connection.channel()
        self.scenarios_generated = 0
        self.setup_queues()

    def load_config(self, config_file):
        config = []
        with open(config_file, 'r') as f:
            for line in f:
                parts = line.strip().split(';')
                if len(parts) >= 3:
                    name, dist, *params = parts
                    config.append({
                        'name': name,
                        'distribution': dist,
                        'parameters': [float(p) for p in params]
                    })
        return config

    def load_function(self, function_file):
        with open(function_file, 'r') as f:
            return f.read()

    def setup_queues(self):
        self.channel.queue_declare(queue='function_queue', durable=True)
        self.channel.queue_declare(queue='scenario_queue', arguments={
            'x-message-ttl': 1000,
            'x-max-length': 1
        })
        self.channel.queue_declare(queue='results_queue')
        self.channel.queue_declare(queue='stats_queue')
        
        # Publicar función inicial
        self.channel.basic_publish(
            exchange='',
            routing_key='function_queue',
            body=self.function,
            properties=pika.BasicProperties(delivery_mode=2)
        )

    def generate_scenario(self):
        scenario = {}
        for var in self.config:
            if var['distribution'] == 'uniform':
                scenario[var['name']] = random.uniform(*var['parameters'])
            elif var['distribution'] == 'normal':
                scenario[var['name']] = random.normalvariate(*var['parameters'])
            elif var['distribution'] == 'choice':
                scenario[var['name']] = random.choice(var['parameters'])
        return scenario

    def send_stats(self):
        stats_message = {
            'type': 'scenarios_generated',
            'count': self.scenarios_generated,
            'timestamp': time.time()
        }
        self.channel.basic_publish(
            exchange='',
            routing_key='stats_queue',
            body=json.dumps(stats_message)
        )

    def run(self):
        last_function_sent = 0
        function_interval = 3
        last_stats_sent = 0
        stats_interval = 1

        print("Productor iniciado. Generando escenarios...")

        while True:
            current_time = time.time()

            if current_time - last_function_sent > function_interval:
                self.channel.basic_publish(
                    exchange='',
                    routing_key='function_queue',
                    body=self.function,
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                last_function_sent = current_time

            if current_time - last_stats_sent > stats_interval:
                self.send_stats()
                last_stats_sent = current_time

            scenario = self.generate_scenario()
            self.scenarios_generated += 1
            
            self.channel.basic_publish(
                exchange='',
                routing_key='scenario_queue',
                body=json.dumps(scenario)
            )
            print(f"Generado #{self.scenarios_generated}: {scenario}")
            time.sleep(2) # Ajusta esto para ir más rápido o lento

if __name__ == "__main__":
    producer = ScenarioProducer('model.txt', 'function.txt')
    producer.run()