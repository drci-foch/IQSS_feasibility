import subprocess
import threading
import time


def run_api(folder, port):
    """Lance une API dans le dossier spécifié sur le port indiqué."""
    print(f"Démarrage de l'API dans {folder} sur le port {port}...")
    subprocess.run(
        f"cd {folder} && uvicorn main:app --host 0.0.0.0 --port {port}", shell=True
    )


if __name__ == "__main__":
    # Liste des APIs à démarrer : (dossier, port)
    apis = [
        ("easily", 8000),
        ("lifen", 8001),
        # Ajoutez d'autres APIs si nécessaire
    ]

    # Démarrer chaque API dans un thread séparé
    threads = []
    for folder, port in apis:
        thread = threading.Thread(target=run_api, args=(folder, port))
        thread.daemon = (
            True  # Le thread s'arrêtera quand le programme principal s'arrête
        )
        threads.append(thread)
        thread.start()
        time.sleep(1)  # Attendre un peu entre chaque démarrage

    # Garder le programme principal en vie
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Arrêt des APIs...")
