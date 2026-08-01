import os
from pathlib import Path
import joblib
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
import numpy as np
import pandas as pd

# ==============================================================================
# 1. CONFIGURACIÓN DE RUTAS Y DATOS BASE
# ==============================================================================
ROOT_DIR = Path(__file__).resolve().parent.parent

DIR_MODELS = ROOT_DIR / "models" / "production"
PATH_DATOS = ROOT_DIR / "data" / "processed" / "df_mensual.parquet"


# ==============================================================================
# IMPORTACIÓN SEGURA DE LA API KEY (LOCAL / NUBE)
# ==============================================================================
try:
    # 1. Intenta importar desde tu archivo local src/config.py
    from src.config import API_KEY
except ImportError:
    # 2. Si estás en la nube y no existe config.py, léela de las variables de entorno
    API_KEY = os.getenv("API_KEY")
    

def _cargar_paquete(equipo: str):
    """Carga el pipeline .joblib correspondiente al equipo seleccionado."""
    # Construcción dinámica de la ruta usando DIR_MODELS:
    ruta_pipeline = DIR_MODELS / f"pipeline_{equipo}.joblib"

    # Verificación de seguridad antes de intentar cargar
    if not ruta_pipeline.exists():
        raise FileNotFoundError(
            f"❌ No se encontró el modelo para '{equipo}' en:\n{ruta_pipeline}"
        )

    return joblib.load(ruta_pipeline)


# ==============================================================================
# 2. HERRAMIENTAS INTERNAS (CUANTITATIVAS)
# ==============================================================================
@tool
def tool_simular_pronostico(
    equipo: str,
    shock_z: float = 0.0,
    shock_x: float = 0.0,
    shock_y: float = 0.0,
    meses: int = 6,
) -> str:
    """Ejecuta una simulación econométrica recursiva I(0) a 'meses' meses hacia el futuro
    para el equipo indicado ('Price_Equipo1' o 'Price_Equipo2'), aplicando shocks en USD
    a los insumos. Retorna los precios esperados y el intervalo de confianza al 95%.
    
   
    """
    paquete = _cargar_paquete(equipo)
    df_hist = pd.read_parquet(PATH_DATOS)
    ultimo_precio = df_hist[equipo].iloc[-1]
    fechas = pd.date_range(
        start=df_hist.index[-1] + pd.DateOffset(months=1),
        periods=meses,
        freq="MS",
    )

    residuos = paquete["y_test"] - paquete["preds_test"]
    sigma_error = np.std(residuos)

    simulacion_deltas = []
    df_temp = df_hist.copy()

    for step in range(meses):
        d_z_val = df_temp["Price_Z"].diff().iloc[-1] + shock_z
        d_x_val = df_temp["Price_X"].diff().iloc[-1] + shock_x
        d_y_val = df_temp["Price_Y"].diff().iloc[-1] + shock_y
        last_delta_eq = (
            df_hist[equipo].diff().iloc[-1]
            if step == 0
            else simulacion_deltas[-1]
        )

        fila_features = {}
        for feat in paquete["feature_names"]:
            if feat == "Z_lag0":
                fila_features[feat] = d_z_val
            elif feat == "X_lag0":
                fila_features[feat] = d_x_val
            elif feat == "Y_lag0":
                fila_features[feat] = d_y_val
            elif feat == "Z_lag1":
                fila_features[feat] = df_temp["Price_Z"].diff().iloc[-1]
            elif feat == "Z_lag2":
                fila_features[feat] = df_temp["Price_Z"].diff().iloc[-2]
            elif feat == "X_lag1":
                fila_features[feat] = df_temp["Price_X"].diff().iloc[-1]
            elif feat == "X_lag2":
                fila_features[feat] = df_temp["Price_X"].diff().iloc[-2]
            elif "lag1" in feat and ("Equipo" in feat or "Eq" in feat):
                fila_features[feat] = last_delta_eq
            else:
                fila_features[feat] = 0.0

        X_step = pd.DataFrame([fila_features])[paquete["feature_names"]]
        X_step_scaled = pd.DataFrame(
            paquete["scaler_obj"].transform(X_step), columns=X_step.columns
        )
        delta_pred = paquete["modelo_obj"].predict(X_step_scaled)[0]
        simulacion_deltas.append(delta_pred)

        nuevo_idx = df_temp.index[-1] + pd.DateOffset(months=1)
        nueva_fila = pd.DataFrame(
            {
                "Price_Z": [df_temp["Price_Z"].iloc[-1] + d_z_val],
                "Price_X": [df_temp["Price_X"].iloc[-1] + d_x_val],
                "Price_Y": [df_temp["Price_Y"].iloc[-1] + d_y_val],
                equipo: [df_temp[equipo].iloc[-1] + delta_pred],
            },
            index=[nuevo_idx],
        )
        df_temp = pd.concat([df_temp, nueva_fila])

    niveles = ultimo_precio + np.cumsum(simulacion_deltas)
    margen_error = 1.96 * sigma_error * np.sqrt(np.arange(1, meses + 1))

    df_res = pd.DataFrame(
        {
            "Mes": fechas.strftime("%Y-%m"),
            "Precio_Esperado_USD": np.round(niveles, 2),
            "Limite_Inf_95%": np.round(niveles - margen_error, 2),
            "Limite_Sup_95%": np.round(niveles + margen_error, 2),
        }
    )
    return (
        f"Resultado simulación {equipo}:\n" + df_res.to_string(index=False)
    )


@tool
def tool_consultar_auditoria(equipo: str) -> str:
    """Consulta las métricas de precisión (MAPE Ajustado, RMSE) y detalles de auditoría del modelo econométrico de un equipo."""
    try:
        paquete = _cargar_paquete(equipo)

        if isinstance(paquete, dict):
            # 1. Buscamos primero si el MAPE ajustado ya viene guardado con llaves del Notebook 2
            mape = (
                paquete.get("mape_adj")
                or paquete.get("mape_ajustado")
                or paquete.get("mape_niveles")
                or paquete.get("mape")
                or paquete.get("MAPE")
            )
            rmse = (
                paquete.get("rmse")
                or paquete.get("RMSE")
                or paquete.get("rmse_test")
            )

            # 2. Si no está como llave, calculamos el MAPE AJUSTADO EN NIVELES usando el historial
            if (
                mape is None or rmse is None
            ) and "y_test" in paquete and "preds_test" in paquete:
                y_t = np.array(paquete["y_test"])
                y_p = np.array(paquete["preds_test"])
                error_absoluto = np.abs(y_t - y_p)

                if mape is None:
                    # Cargamos el historial para obtener el nivel medio real del precio (denominador en niveles)
                    df_hist = pd.read_parquet(PATH_DATOS)
                    precio_nivel_medio = df_hist[equipo].mean()

                    # MAPE Ajustado = (Error en delta / Precio en niveles) * 100
                    mape_calc = np.mean(error_absoluto / precio_nivel_medio) * 100
                    mape = f"{mape_calc:.2f}% (Ajustado en niveles)"

                if rmse is None:
                    rmse_calc = np.sqrt(np.mean((y_t - y_p) ** 2))
                    rmse = f"{rmse_calc:.2f} USD"

            # Formateamos los valores finales para el agente
            mape_str = (
                f"{mape:.2f}%"
                if isinstance(mape, (int, float))
                else str(mape)
            )
            rmse_str = (
                f"{rmse:.2f}" if isinstance(rmse, (int, float)) else str(rmse)
            )

            return (
                f"📊 Auditoría Econométrica para {equipo}:\n"
                f"- MAPE Ajustado (Error Porcentual en Niveles): {mape_str}\n"
                f"- RMSE (Raíz del Error Cuadrático Medio): {rmse_str}\n"
                f"- Total de variables predictoras: {len(paquete.get('feature_names', []))}"
            )

        else:
            return f"El archivo cargado para {equipo} es de tipo {type(paquete).__name__}."

    except Exception as e:
        return f"Error al consultar auditoría de {equipo}: {str(e)}"


# ==============================================================================
# 3. HERRAMIENTA EXTERNA (BÚSQUEDA DEL MERCADO)
# ==============================================================================
@tool
def tool_buscar_noticias_mercado(consulta: str) -> str:
    """Busca en internet noticias, contexto económico o tendencias mundiales sobre

    materias primas (acero, cemento, insumos Z, X, Y), maquinaria pesada o el sector de renting.
    """
    search_run = DuckDuckGoSearchRun()
    resultado = search_run.invoke(consulta)
    return resultado[:1000]


# ==============================================================================
# 4. ORQUESTADOR DEL AGENTE COGNITIVO
# ==============================================================================
def _obtener_api_key():
    """Busca la clave en variables de entorno o en src/config.py de forma robusta."""
    # 1. Primero busca si ya está en las variables de entorno del sistema o de Streamlit Cloud
    key = os.getenv("API_KEY") or os.getenv("API_KEY")
    if key:
        return key

    # 2. Si no está en el entorno, intenta leerla desde el archivo local src/config.py
    try:
        from src.config import API_KEY as local_key

        return local_key
    except (ImportError, AttributeError):
        return None


def crear_agente_mercado():
    api_key_activa = _obtener_api_key()

    if not api_key_activa:
        raise ValueError(
            "No se encontró la API_KEY ni en variables de entorno ni en src/config.py"
        )

    # Usamos el parámetro moderno 'api_key' y le pasamos la clave detectada
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        temperature=0.2,
        api_key=api_key_activa,  # <-- 'api_key' en lugar de 'google_api_key'
    )

    herramientas = [
        tool_simular_pronostico,
        tool_consultar_auditoria,
        tool_buscar_noticias_mercado,
    ]

    prompt_sistema = """
    Eres un Agente Cognitivo Senior de Inteligencia de Mercado e Ingeniería Econométrica.
    Tu objetivo es responder a las preguntas del directivo o evaluador combinando RIGOR MATEMÁTICO
    y CONTEXTO MACROECONÓMICO REAL.

    Tus directrices son:
    1. Si te preguntan por un pronóstico, precios futuros o simulaciones, DEBES usar la herramienta 'tool_simular_pronostico'.
    2. Si te preguntan por calidad del modelo, variables importantes o error, usa 'tool_consultar_auditoria'.
    3. Para enriquecer el análisis con tendencias reales, inflación o mercado industrial/renting, usa 'tool_buscar_noticias_mercado'.
    4. Explica siempre tus conclusiones ejecutivamente: contrasta los números del modelo estacionario con los hallazgos de la web.
    """

    return create_react_agent(llm, tools=herramientas, prompt=prompt_sistema)