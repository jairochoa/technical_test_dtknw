import os
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from pathlib import Path

# ==============================================================================
# 1. CONFIGURACIÓN DE LA PÁGINA Y CARGA DE ARTEFACTOS
# ==============================================================================
st.set_page_config(
    page_title="Proyección de Precios - Maquinaria",
    page_icon="🏗️",
    layout="wide",
)

st.title("🏗️ Sistema Inteligente de Proyección de Costos de Maquinaria")
st.markdown(
    "Herramienta analítica para estimar precios de maquinaria basada en insumos industriales y memoria temporal."
)


DIR_MODELS = Path(__file__).resolve().parent / "models" / "production"


@st.cache_resource
def cargar_pipeline(target_name):
    ruta = os.path.join(DIR_MODELS, f"pipeline_{target_name}.joblib")
    if not os.path.exists(ruta):
        st.error(
            f"❌ No se encontró el archivo de producción en: {ruta}. Ejecuta primero tu script de modelado."
        )
        st.stop()
    return joblib.load(ruta)


# ==============================================================================
# 2. PANEL LATERAL (SELECTOR DE EQUIPO)
# ==============================================================================
st.sidebar.header("⚙️ Configuración del Pronóstico")
equipo_seleccionado = st.sidebar.selectbox(
    "Selecciona el Equipo a Modelar:",
    options=["Price_Equipo1", "Price_Equipo2"],
    index=0,
)

paquete = cargar_pipeline(equipo_seleccionado)
st.sidebar.success(f"Modelo Cargado: **{paquete['modelo_nombre']}**")
st.sidebar.info(
    f"Precisión Histórica (MAPE): **{paquete['metricas_test']['MAPE (%)']:.2f}%**"
)

# ==============================================================================
# 3. INTERFAZ EN PESTAÑAS (TABS)
# ==============================================================================
tab_pronostico, tab_auditoria, tab_ia = st.tabs(
    ["📊 Pronosticador Interactivo", "🔍 Explicabilidad y Coeficientes", "🤖 Asistente IA"]
)

# ------------------------------------------------------------------------------
# TAB 1: PRONOSTICADOR
# ------------------------------------------------------------------------------
with tab_pronostico:
    st.subheader(f"Estimación en Dólares para: {equipo_seleccionado}")
    st.markdown(
        "Modifica los valores de las variables (en USD reales) para generar una proyección al instante:"
    )

    # Tomamos el último valor conocido como valor por defecto para no empezar de cero
    ejemplo_input = paquete["X_test"].iloc[[-1]].copy()
    defaults_usd = pd.DataFrame(
        paquete["scaler_obj"].inverse_transform(ejemplo_input),
        columns=ejemplo_input.columns,
    ).iloc[0]

    cols = st.columns(2)
    inputs_usuario = {}

    for idx, feature in enumerate(paquete["feature_names"]):
        col_actual = cols[idx % 2]
        val_default = float(defaults_usd[feature])
        inputs_usuario[feature] = col_actual.number_input(
            label=f"Variable: `{feature}` ($)",
            value=round(val_default, 2),
            step=10.0,
            format="%.2f",
        )

    st.markdown("---")
    if st.button("🚀 Ejecutar Proyección de Precio", type="primary"):
        # Envolver en DataFrame para evitar UserWarnings de scikit-learn
        df_in = pd.DataFrame([inputs_usuario], columns=paquete["feature_names"])
        input_scaled = pd.DataFrame(
            paquete["scaler_obj"].transform(df_in), columns=df_in.columns
        )
        prediccion_usd = paquete["modelo_obj"].predict(input_scaled)[0]

        res_col1, res_col2 = st.columns([1, 2])
        with res_col1:
            st.metric(
                label="Precio Proyectado (USD)",
                value=f"${prediccion_usd:,.2f}",
                delta=f"Margen MAPE: {paquete['metricas_test']['MAPE (%)']:.2f}%",
            )
        with res_col2:
            st.success(
                f"**Pronóstico generado con éxito** utilizando regularización **{paquete['modelo_nombre']}** sobre datos estandarizados."
            )

# ------------------------------------------------------------------------------
# TAB 2: AUDITORÍA Y COEFICIENTES
# ------------------------------------------------------------------------------
with tab_auditoria:
    st.subheader("Auditoría Técnica del Modelo y Motores del Precio")

    col_grafico, col_coefs = st.columns([3, 2])

    with col_grafico:
        st.markdown("**1. Desempeño en el Examen Final (Holdout 30%):**")
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(
            paquete["y_test"].index,
            paquete["y_test"],
            label="Real ($)",
            color="black",
            linewidth=2,
        )
        ax.plot(
            paquete["y_test"].index,
            paquete["preds_test"],
            label=f"Predicción ({paquete['modelo_nombre']})",
            color="#1f77b4",
            linestyle="--",
            linewidth=2,
        )
        ax.set_ylabel("Precio ($)")
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend()
        st.pyplot(fig)

    with col_coefs:
        st.markdown("**2. Importancia de Variables (Pesos del Modelo):**")
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
                pesos.to_frame(name="Importancia (Gini)"),
                use_container_width=True,
            )

# ------------------------------------------------------------------------------
# TAB 3: ASISTENTE IA (LISTO PARA EL SIGUIENTE PASO)
# ------------------------------------------------------------------------------
with tab_ia:
    st.subheader("🤖 Asistente Virtual Inteligente")
    st.info(
        "En el próximo paso conectaremos aquí a nuestro Agente para que analice escenarios conversacionales usando el contexto del modelo."
    )