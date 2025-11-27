# deploy.py - Script auxiliar para despliegue distribuido
import subprocess
import sys
import argparse
import time

def deploy_consumers(rabbitmq_host, consumer_count=3, start_port=5001):
    """Desplegar múltiples consumidores"""
    processes = []
    
    try:
        for i in range(consumer_count):
            # En una implementación real, aquí se usaría SSH para desplegar en máquinas remotas
            # Por ahora, solo demostramos el concepto localmente
            cmd = [
                'python', 'consumer.py', f'consumer_{i}',
                '--host', rabbitmq_host
            ]
            process = subprocess.Popen(cmd)
            processes.append(process)
            print(f"✅ Iniciado consumidor consumer_{i} conectando a {rabbitmq_host}")
            time.sleep(0.5)  # Pequeño delay entre inicios
        
        print(f"\n🎯 Desplegados {consumer_count} consumidores conectando a {rabbitmq_host}")
        print("⏹️  Presiona Ctrl+C para detener todos los consumidores")
        
        # Mantener el script corriendo
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo consumidores...")
        for process in processes:
            process.terminate()
        for process in processes:
            process.wait()
        print("✅ Todos los consumidores detenidos")

def main():
    parser = argparse.ArgumentParser(description='Despliegue distribuido de Monte Carlo')
    parser.add_argument('host', help='Host de RabbitMQ')
    parser.add_argument('--consumers', type=int, default=3, help='Número de consumidores a desplegar')
    parser.add_argument('--local', action='store_true', help='Desplegar localmente (para prueba)')
    
    args = parser.parse_args()
    
    if args.local:
        print("🚀 Desplegando localmente...")
        deploy_consumers(args.host, args.consumers)
    else:
        print("🌐 Modo distribuido - Ejecute este comando en cada máquina consumidor:")
        print(f"python consumer.py NOMBRE_CONSUMIDOR --host {args.host}")

if __name__ == "__main__":
    main()