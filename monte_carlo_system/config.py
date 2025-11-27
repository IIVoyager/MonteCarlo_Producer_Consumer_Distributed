import pika
import os

class RabbitMQConfig:
    # Configuración de RabbitMQ - SERVIDOR usa localhost
    HOST = os.getenv('RABBITMQ_HOST', 'localhost') #Cambiar local host para Server
    PORT = int(os.getenv('RABBITMQ_PORT', 5672))
    USERNAME = os.getenv('RABBITMQ_USERNAME', 'myuser')
    PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'mypassword')
    VIRTUAL_HOST = os.getenv('RABBITMQ_VHOST', '/')
    
    # Nombres de colas
    FUNCTION_QUEUE = 'function_queue'
    SCENARIO_QUEUE = 'scenario_queue'
    RESULTS_QUEUE = 'results_queue'
    STATS_QUEUE = 'stats_queue'
    
    @classmethod
    def get_connection_params(cls):
        return pika.ConnectionParameters(
            host=cls.HOST,
            port=cls.PORT,
            virtual_host=cls.VIRTUAL_HOST,
            credentials=pika.PlainCredentials(cls.USERNAME, cls.PASSWORD),
            heartbeat=600,
            blocked_connection_timeout=300
        )