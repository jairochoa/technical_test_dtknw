import os
from pathlib import Path
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from app.agent import crear_agente_mercado

# ==============================================================================
# 1. CONFIGURACIÓN DE LA PÁGINA Y RUTAS
# ==============================================================================
st.set_page_config(
    page_title="Simulador de Costos - Equipos de campo", page_icon="🏗️", layout="wide"
)

st.title("🏗️ Simulador Estratégico de Precios de Equipos")
st.markdown(
    "Herramienta de pronóstico a n meses basada en modelos econométricos estacionarios $I(0)$ y análisis de sensibilidad por shocks de insumos."
)

# Rutas absolutas seguras con pathlib
DIR_MODELS = Path(__file__).resolve().parent / "models" / "production"
PATH_DATOS = Path(__file__).resolve().parent / "data" / "processed" / "df_mensual.parquet"


@st.cache_resource
def cargar_recursos(target_name):
    ruta_pipeline = DIR_MODELS / f"pipeline_{target_name}.joblib"
    if not ruta_pipeline.exists():
        st.error(
            f"❌ No se encontró el pipeline en: {ruta_pipeline}. Entrena los modelos primero."
        )
        st.stop()
    paquete = joblib.load(ruta_pipeline)
    df_base = pd.read_parquet(PATH_DATOS)
    return paquete, df_base


# ==============================================================================
# 2. PANEL LATERAL (CONFIGURACIÓN Y SHOCKS)
# ==============================================================================
st.sidebar.header("⚙️ Parámetros de Simulación")
equipo_seleccionado = st.sidebar.selectbox(
    "Selecciona el Equipo a Simular:",
    options=["Price_Equipo1", "Price_Equipo2"],
    index=0,
    key="sidebar_select_equipo",
)

paquete, df_mensual = cargar_recursos(equipo_seleccionado)

st.sidebar.success(f"Modelo Activo: **{paquete['modelo_nombre']}**")
st.sidebar.markdown("---")

horizonte = st.sidebar.slider(
    "Horizonte de Proyección (Meses)",
    min_value=1,
    max_value=12,
    value=6,  # Valor por defecto
    step=1,
)

st.sidebar.markdown("---")

st.sidebar.subheader("🎚️ Sliders de Shock de Insumos (Horizonte n Meses)")
st.sidebar.markdown(
    "Ajusta el impulso mensual adicional (en USD) para cada materia prima:"
)

# Definir qué insumos aplican según el equipo
if equipo_seleccionado == "Price_Equipo1":
    shock_z = st.sidebar.slider(
        "Shock Mensual Materia Prima Z ($)",
        min_value=-50.0,
        max_value=50.0,
        value=0.0,
        step=5.0,
    )
    shock_x = st.sidebar.slider(
        "Shock Mensual Insumo X ($)",
        min_value=-50.0,
        max_value=50.0,
        value=0.0,
        step=5.0,
    )
    shock_y = 0.0
else:
    shock_z = st.sidebar.slider(
        "Shock Mensual Materia Prima Z ($)",
        min_value=-50.0,
        max_value=50.0,
        value=0.0,
        step=5.0,
    )
    shock_y = st.sidebar.slider(
        "Shock Mensual Insumo Y ($)",
        min_value=-50.0,
        max_value=50.0,
        value=0.0,
        step=5.0,
    )
    shock_x = 0.0

# ==============================================================================
# 3. INTERFAZ EN PESTAÑAS (TABS)
# ==============================================================================
tab_simulador, tab_auditoria, tab_agente = st.tabs(
    ["📈 Simulador de Escenarios (varios meses)", "🔍 Auditoría y Coeficientes", "🤖 Agente de Mercado (AI)",]
)

# ------------------------------------------------------------------------------
# TAB 1: SIMULADOR RECURSIVO A N MESES CON BANDAS DE CONFIANZA
# ------------------------------------------------------------------------------
with tab_simulador:
    st.subheader(f"Proyección Semestral y Banda de Riesgo: {equipo_seleccionado}")
    st.markdown(
        "Simulación recursiva a n meses con **Intervalo de Confianza (95%)** basado en la volatilidad de los residuos fuera de muestra."
    )

    df_hist = df_mensual.copy()
    ultimo_precio_nivel = df_hist[equipo_seleccionado].iloc[-1]
    fechas_futuras = pd.date_range(
        start=df_hist.index[-1] + pd.DateOffset(months=1),
        periods=horizonte,
        freq="MS",
    )

    # Calcular la desviación estándar de los residuos en Test para estimar el error
    residuos_test = paquete["y_test"] - paquete["preds_test"]
    sigma_error = np.std(residuos_test)


    def ejecutar_simulacion_con_incertidumbre(s_z, s_x, s_y):
        simulacion_deltas = []
        df_temp = df_hist.copy()

        for step in range(horizonte):
            d_z_val = df_temp["Price_Z"].diff().iloc[-1] + s_z
            d_x_val = df_temp["Price_X"].diff().iloc[-1] + s_x
            d_y_val = df_temp["Price_Y"].diff().iloc[-1] + s_y

            if step == 0:
                last_delta_eq = df_hist[equipo_seleccionado].diff().iloc[-1]
            else:
                last_delta_eq = simulacion_deltas[-1]

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
            nuevo_z = df_temp["Price_Z"].iloc[-1] + d_z_val
            nuevo_x = df_temp["Price_X"].iloc[-1] + d_x_val
            nuevo_y = df_temp["Price_Y"].iloc[-1] + d_y_val
            nuevo_eq = df_temp[equipo_seleccionado].iloc[-1] + delta_pred

            nueva_fila = pd.DataFrame(
                {
                    "Price_Z": [nuevo_z],
                    "Price_X": [nuevo_x],
                    "Price_Y": [nuevo_y],
                    equipo_seleccionado: [nuevo_eq],
                },
                index=[nuevo_idx],
            )
            df_temp = pd.concat([df_temp, nueva_fila])

        deltas_arr = np.array(simulacion_deltas)
        niveles = ultimo_precio_nivel + np.cumsum(deltas_arr)

        # Banda de error acumulativa (crece con la raíz cuadrada del paso temporal h)
        pasos = np.arange(1, horizonte + 1)
        margen_error = 1.96 * sigma_error * np.sqrt(pasos)

        limite_superior = niveles + margen_error
        limite_inferior = niveles - margen_error

        return niveles, limite_inferior, limite_superior


    # Ejecutar simulaciones
    niveles_base, _, _ = ejecutar_simulacion_con_incertidumbre(0.0, 0.0, 0.0)
    niveles_shock, inf_shock, sup_shock = ejecutar_simulacion_con_incertidumbre(
        shock_z, shock_x, shock_y
    )

    # Gráfico con bandas de confianza
    fig, ax = plt.subplots(figsize=(10, 4.8))

    hist_reciente = df_hist[equipo_seleccionado].iloc[-6:]
    ax.plot(
        hist_reciente.index,
        hist_reciente,
        label="Histórico Real ($)",
        color="black",
        marker="o",
        linewidth=2,
    )
    ax.plot(
        fechas_futuras,
        niveles_base,
        label="Escenario Base (Inercial)",
        color="gray",
        linestyle="--",
        marker="s",
        linewidth=2,
    )
    ax.plot(
        fechas_futuras,
        niveles_shock,
        label="Escenario con Shock (Esperado)",
        color="#1f77b4",
        linestyle="-",
        marker="o",
        linewidth=2.5,
    )

    # Pintar el cono de incertidumbre (Banda de Confianza 95%)
    ax.fill_between(
        fechas_futuras,
        inf_shock,
        sup_shock,
        color="#1f77b4",
        alpha=0.2,
        label="Banda de Confianza (95%)",
    )

    ax.set_title(
        f"Simulación de Precios con Cono de Riesgo - {equipo_seleccionado}",
        fontsize=12,
        fontweight="bold",
    )
    ax.set_ylabel("Precio Proyectado ($ USD)")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(frameon=True, loc="upper left")
    st.pyplot(fig)

    # Tabla resumen ampliada con los límites de riesgo
    st.markdown("---")
    st.subheader(
        "📋 Resumen Financiero y Límites de Exposición (Escenario con Shock)"
    )
    df_resumen = pd.DataFrame(
        {
            "Mes Proyectado": fechas_futuras.strftime("%Y-%m"),
            "Base ($)": np.round(niveles_base, 2),
            "Shock Esperado ($)": np.round(niveles_shock, 2),
            "Límite Inferior 95% ($)": np.round(inf_shock, 2),
            "Límite Superior 95% ($)": np.round(sup_shock, 2),
            "Impacto Máx. Riesgo ($)": np.round(sup_shock - niveles_base, 2),
        }
    )
    st.dataframe(df_resumen, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 2: AUDITORÍA Y COEFICIENTES
# ------------------------------------------------------------------------------
with tab_auditoria:
    st.subheader("Auditoría del Modelo y Explicabilidad")
    col_g, col_c = st.columns([3, 2])

    with col_g:
        st.markdown("**Desempeño en Conjunto Test (30%):**")
        fig2, ax2 = plt.subplots(figsize=(8, 4))
        ax2.plot(
            paquete["y_test"].index,
            paquete["y_test"],
            label="Real Δ ($)",
            color="black",
        )
        ax2.plot(
            paquete["y_test"].index,
            paquete["preds_test"],
            label=f"Predicción [{paquete['modelo_nombre']}]",
            color="#2ca02c",
            linestyle="--",
        )
        ax2.set_ylabel("Variación Mensual Δ ($)")
        ax2.grid(True, linestyle=":", alpha=0.6)
        ax2.legend()
        st.pyplot(fig2)

    with col_c:
        st.markdown("**Pesos del Modelo (Coeficientes):**")
        modelo = paquete["modelo_obj"]
        if hasattr(modelo, "coef_"):
            pesos = pd.Series(
                modelo.coef_, index=paquete["feature_names"]
            ).sort_values(key=abs, ascending=False)
            st.dataframe(
                pesos.to_frame(name="Peso Estandarizado"),
                use_container_width=True,
            )
        else:
            pesos = pd.Series(
                modelo.feature_importances_, index=paquete["feature_names"]
            ).sort_values(ascending=False)
            st.dataframe(
                pesos.to_frame(name="Importancia"), use_container_width=True
            )

# ------------------------------------------------------------------------------
# TAB 3: AGENTE COGNITIVO DE IA CON MEMORIA Y HERRAMIENTAS
# ------------------------------------------------------------------------------
with tab_agente:
    st.subheader("🤖 Agente Autónomo: Inteligencia Cuantitativa + Mercado")
    st.markdown(
        """
    Este agente de IA **combina de forma autónoma** las simulaciones econométricas del modelo estacionario
    con búsquedas de contexto económico e industrial en internet para responder tus consultas estratégicas.
    """
    )

    # Inicializar historial de conversación en sesión
    if "mensajes_chat" not in st.session_state:
        st.session_state["mensajes_chat"] = [
            {
                "role": "assistant",
                "content": "¡Hola! Soy tu Agente Cognitivo de Precios. Puedes pedirme proyecciones simuladas (ej: *'Simula 6 meses de Equipo 1 con shock de $20 en el insumo Z'*), preguntarme por la calidad matemática del modelo o pedirme que busque tendencias externas del sector para contextualizar.",
            }
        ]

    # Mostrar mensajes del historial
    for m in st.session_state["mensajes_chat"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # Capturar pregunta del usuario
    if pregunta_usuario := st.chat_input("Escribe tu consulta estratégica..."):
        st.session_state["mensajes_chat"].append(
            {"role": "user", "content": pregunta_usuario}
        )
        with st.chat_message("user"):
            st.markdown(pregunta_usuario)

        with st.chat_message("assistant"):
            # Intentar obtener la clave desde la configuración o el entorno
            try:
                from src.config import API_KEY as KEY_ACTIVA
            except ImportError:
                KEY_ACTIVA = os.getenv("API_KEY")

            if not KEY_ACTIVA:
                st.error(
                    "❌ No se encontró la `API_KEY`. Verifica tu archivo `src/config.py` o tus variables de entorno."
                )
            else:
                with st.spinner(
                    "🤖 Percibiendo el entorno, ejecutando modelos e investigando mercado..."
                ):
                    try:

                        agente = crear_agente_mercado()
                        res = agente.invoke({"messages": [("user", pregunta_usuario)]})
                        contenido_crudo = res["messages"][-1].content

                        # 1. Si Gemini devuelve una lista de bloques (formato moderno):
                        if isinstance(contenido_crudo, list):
                            # Extraemos solo el valor 'text' de los bloques que lo contengan
                            fragmentos = [
                                bloque["text"]
                                for bloque in contenido_crudo
                                if isinstance(bloque, dict) and "text" in bloque
                            ]
                            respuesta_texto = "\n".join(fragmentos)
                        # 2. Si devuelve texto plano directo:
                        else:
                            respuesta_texto = str(contenido_crudo)

                        st.markdown(respuesta_texto)
                        st.session_state["mensajes_chat"].append(
                            {"role": "assistant", "content": respuesta_texto}
                        )
                    except Exception as e:
                        st.error(f"Error al procesar con el agente: {e}")