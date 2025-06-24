import os
import signal
import subprocess
import sys
import threading
import time


def run_api(folder, port):
    """Lance une API dans le dossier spécifié sur le port indiqué."""
    print(f"🚀 Démarrage de l'API {folder} sur le port {port}...")

    try:
        # Commande simple uvicorn
        cmd = f"cd {folder} && uvicorn main:app --host 0.0.0.0 --port {port} --log-level warning"

        # Lancer le processus
        subprocess.run(cmd, shell=True)

    except Exception as e:
        print(f"❌ Erreur lors du démarrage de l'API {folder}: {str(e)}")

def signal_handler(signum, frame):
    """Gestionnaire pour Ctrl+C"""
    print("\n🛑 Arrêt demandé. Fermeture des APIs...")
    sys.exit(0)

def main():
    """Point d'entrée principal"""
    print("=" * 60)
    print("🚀 GESTIONNAIRE D'APIS LIFEN & EASILY")
    print("=" * 60)

    # Gestionnaire de signal pour Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Vérifier que les dossiers existent
    folders = ["easily", "lifen"]
    for folder in folders:
        if not os.path.exists(folder):
            print(f"❌ Le dossier '{folder}' n'existe pas!")
            return

        main_file = os.path.join(folder, "main.py")
        if not os.path.exists(main_file):
            print(f"❌ Le fichier '{main_file}' n'existe pas!")
            return

    print("✅ Tous les fichiers sont présents")
    print("")

    # Liste des APIs à démarrer : (dossier, port)
    apis = [
        ("easily", 8000),
        ("lifen", 8001),
    ]

    # Démarrer chaque API dans un thread séparé
    threads = []
    for folder, port in apis:
        thread = threading.Thread(target=run_api, args=(folder, port))
        thread.daemon = True  # Le thread s'arrêtera quand le programme principal s'arrête
        threads.append(thread)
        thread.start()
        time.sleep(2)  # Attendre entre chaque démarrage

    print("")
    print("🎯 URLs disponibles:")
    print("   - API Easily: http://localhost:8000/docs")
    print("   - API Lifen:  http://localhost:8001/docs")
    print("")
    print("🛑 Appuyez sur Ctrl+C pour arrêter toutes les APIs")
    print("")

    # Garder le programme principal en vie
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()
