from pathlib import Path

# Rutas del proyecto

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"


# Nombres de archivos

RAW_FILES = {
    "historico": "historico_equipos.csv",
    "X": "X.csv",
    "y": "y.csv",
    "Z": "Z.csv",
}

PROCESSED_OUTPUT = DATA_PROCESSED_DIR / "predicciones_fases.csv"


# Parámetros para los modelo

RANDOM_SEED = 42
QUANTILES = [0.10, 0.50, 0.90]  # p10 (Límite inf), p50 (Mediana/Esperado), p90 (Límite sup)
TEST_SIZE_MONTHS = 6            # Ventana de evaluación temporal

