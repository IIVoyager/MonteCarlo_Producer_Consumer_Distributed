from flask import Flask, render_template
from flask_socketio import SocketIO
from collections import defaultdict, deque
from threading import Lock
import pika
import threading
import json
import time
import datetime

# --- CONFIGURACIÓN ---
USUARIO = 'guest'
PASSWORD = 'guest'
HOST = 'localhost'
# ---------------------

app = Flask(__name__)
socketio = SocketIO(app)

class Dashboard:
    def __init__(self):
        self.stats = {
            'scenarios_generated': 0,
            'scenarios_processed': 0,
            'consumer_results': defaultdict(int),
            'all_results': deque(maxlen=1000),
            'consumer_stats': defaultdict(lambda: {
                'start_time': time.time(),
                'results_count': 0,
                'last_result': None,
                'last_scenario': None,
                'last_activity': time.time()
            }),
            'scenario_history': deque(maxlen=100),
            'update_time': time.time()
        }
        self.lock = Lock()

    def start_rabbitmq_consumer(self):
        def connect_rabbitmq():
            credentials = pika.PlainCredentials(USUARIO, PASSWORD)
            
            while True:
                try:
                    connection = pika.BlockingConnection(
                        pika.ConnectionParameters(host=HOST, credentials=credentials)
                    )
                    channel = connection.channel()
                    
                    channel.queue_declare(queue='results_queue')
                    channel.queue_declare(queue='stats_queue')
                    channel.queue_declare(queue='scenario_queue', arguments={
                        'x-message-ttl': 1000,
                        'x-max-length': 1
                    })
                    
                    print("Dashboard conectado a RabbitMQ.")
                    
                    def results_callback(ch, method, properties, body):
                        try:
                            data = json.loads(body)
                            with self.lock:
                                consumer_id = data.get('consumer_id', 'unknown')
                                result = data.get('result', 0)
                                scenario = data.get('scenario', {})
                                timestamp = data.get('timestamp', time.time())
                                
                                self.stats['scenarios_processed'] += 1
                                self.stats['consumer_results'][consumer_id] += 1
                                self.stats['all_results'].append(result)
                                
                                if consumer_id not in self.stats['consumer_stats']:
                                    self.stats['consumer_stats'][consumer_id] = {
                                        'start_time': time.time(),
                                        'results_count': 0,
                                        'last_result': None,
                                        'last_scenario': None,
                                        'last_activity': time.time()
                                    }
                                
                                consumer_stat = self.stats['consumer_stats'][consumer_id]
                                consumer_stat['results_count'] += 1
                                consumer_stat['last_result'] = result
                                consumer_stat['last_scenario'] = scenario
                                consumer_stat['last_activity'] = time.time()
                                
                                self.stats['scenario_history'].append({
                                    'consumer_id': consumer_id,
                                    'result': result,
                                    'scenario': scenario,
                                    'timestamp': timestamp,
                                    'time_str': datetime.datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
                                })
                                
                                self.stats['update_time'] = time.time()
                                socketio.emit('update', self.get_formatted_stats())
                                
                        except Exception as e:
                            print(f"Error procesando mensaje: {e}")
                    
                    def stats_callback(ch, method, properties, body):
                        try:
                            data = json.loads(body)
                            with self.lock:
                                if data.get('type') == 'scenarios_generated':
                                    self.stats['scenarios_generated'] = data.get('count', 0)
                                    self.stats['update_time'] = time.time()
                                    socketio.emit('update', self.get_formatted_stats())
                        except Exception as e:
                            print(f"Error procesando stats: {e}")
                    
                    channel.basic_consume(queue='results_queue', on_message_callback=results_callback, auto_ack=True)
                    channel.basic_consume(queue='stats_queue', on_message_callback=stats_callback, auto_ack=True)
                    channel.start_consuming()
                    
                except Exception as e:
                    print(f"Dashboard desconectado: {e}. Reconectando...")
                    time.sleep(5)

        threading.Thread(target=connect_rabbitmq, daemon=True).start()

    def get_formatted_stats(self):
        current_time = time.time()
        formatted_stats = {
            'scenarios_generated': self.stats['scenarios_generated'],
            'scenarios_processed': self.stats['scenarios_processed'],
            'consumer_results': dict(self.stats['consumer_results']),
            'all_results': list(self.stats['all_results']),
            'consumer_stats': {},
            'scenario_history': list(self.stats['scenario_history'])[-20:],
            'update_time': self.stats['update_time']
        }
        
        for cid, info in self.stats['consumer_stats'].items():
            formatted_stats['consumer_stats'][cid] = {
                'active_time': current_time - info['start_time'],
                'results_count': info['results_count'],
                'last_result': info['last_result'],
                'last_scenario': info['last_scenario'],
                'last_activity': info['last_activity']
            }
        return formatted_stats

dashboard = Dashboard()

@app.route('/')
def index():
    return render_template('dashboard.html')

@socketio.on('connect')
def handle_connect():
    socketio.emit('update', dashboard.get_formatted_stats())

if __name__ == '__main__':
    threading.Thread(target=dashboard.start_rabbitmq_consumer, daemon=True).start()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)