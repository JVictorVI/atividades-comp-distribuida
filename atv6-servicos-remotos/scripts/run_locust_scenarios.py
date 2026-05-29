import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCUST_FILE = ROOT / "locustfile.py"
RESULTS_DIR = Path(os.getenv("LOCUST_RESULTS_DIR", ROOT / "results"))
DURATION = os.getenv("LOCUST_DURATION", "1m")
SPAWN_RATE = int(os.getenv("LOCUST_SPAWN_RATE", "100"))
USER_COUNTS = [
    int(value.strip())
    for value in os.getenv("LOCUST_USER_COUNTS", "50,250,500").split(",")
    if value.strip()
]

CLASSES = {
    "RestApiUser": "rest",
    "GraphqlApiUser": "graphql",
    "SoapApiUser": "soap",
    "GrpcMusicUser": "grpc",
}
TECHNOLOGY_FILTER = [
    value.strip().lower()
    for value in os.getenv("LOCUST_TECHNOLOGIES", "").split(",")
    if value.strip()
]


def scenario_name(users):
    names = {
        50: "carga-leve",
        250: "carga-media",
        500: "carga-alta",
    }
    return names.get(users, f"usuarios-{users}")


def run():
    if SPAWN_RATE <= 0:
        raise SystemExit("LOCUST_SPAWN_RATE deve ser maior que zero")

    selected_classes = {
        class_name: technology
        for class_name, technology in CLASSES.items()
        if not TECHNOLOGY_FILTER or technology in TECHNOLOGY_FILTER
    }
    if not selected_classes:
        valid = ", ".join(CLASSES.values())
        requested = ", ".join(TECHNOLOGY_FILTER)
        raise SystemExit(f"LOCUST_TECHNOLOGIES invalido: {requested}. Valores aceitos: {valid}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    for class_name, technology in selected_classes.items():
        for users in USER_COUNTS:
            scenario = scenario_name(users)
            prefix = RESULTS_DIR / f"locust-{technology}-{scenario}-u{users}"
            command = [
                sys.executable,
                "-m",
                "locust",
                "-f",
                str(LOCUST_FILE),
                class_name,
                "--headless",
                "-u",
                str(users),
                "-r",
                str(SPAWN_RATE),
                "-t",
                DURATION,
                "--csv",
                str(prefix),
                "--csv-full-history",
                "--only-summary",
            ]

            print(
                f"Executando {technology} | {scenario} | users={users} | "
                f"spawn-rate={SPAWN_RATE} | duration={DURATION}",
                flush=True,
            )
            subprocess.run(command, cwd=ROOT, check=True)

    print(f"Bateria Locust concluida. Arquivos gerados em {RESULTS_DIR}")


if __name__ == "__main__":
    try:
        run()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
