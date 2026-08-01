import os
import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.base import clone
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

from src.features import crear_features_equipo1, crear_features_equipo2

DIR_ARTEFACTOS = "../models/production"
os.makedirs(DIR_ARTEFACTOS, exist_ok=True)

GENERADORES_FEATURES = {
    "Price_Equipo1": crear_features_equipo1,
    "Price_Equipo2": crear_features_equipo2,
}

MODELOS_CANDIDATOS = {
    # Bajamos alpha de 1.0 a 0.1 para permitir mayor amplitud en los picos
    "Ridge": Ridge(alpha=0.1),
    "ElasticNet": ElasticNet(alpha=0.005, l1_ratio=0.7, random_state=42),
    "LightGBM": LGBMRegressor(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=4,
        random_state=42,
        verbose=-1,
    ),
}


def preparar_matrices(df_features, target_col, train_ratio=0.70):
    n_train = int(len(df_features) * train_ratio)
    train_data = df_features.iloc[:n_train]
    test_data = df_features.iloc[n_train:]

    drop_cols = [
        "Price_Equipo1",
        "Price_Equipo2",
        "Price_X",
        "Price_Y",
        "Price_Z",
    ]
    X_train = train_data.drop(columns=drop_cols, errors="ignore")
    y_train = train_data[target_col]

    X_test = test_data[X_train.columns]
    y_test = test_data[target_col]

    scaler = StandardScaler().set_output(transform="pandas")
    X_train_scaled = pd.DataFrame(
        scaler.fit_transform(X_train),
        columns=X_train.columns,
        index=X_train.index,
    )
    X_test_scaled = pd.DataFrame(
        scaler.transform(X_test),
        columns=X_test.columns,
        index=X_test.index,
    )

    return X_train_scaled, X_test_scaled, y_train, y_test, scaler


def evaluar_metricas(y_true, y_pred):
    mse = mean_squared_error(y_true, y_pred)
    return {
        "RMSE": np.sqrt(mse),
        "MAE": mean_absolute_error(y_true, y_pred),
        "MAPE (%)": mean_absolute_percentage_error(y_true, y_pred) * 100,
        "MSE": mse,
    }


def validacion_cruzada_ts(modelo, X_train, y_train, n_splits=3):
    tscv = TimeSeriesSplit(n_splits=n_splits)
    mapes = []
    for train_idx, val_idx in tscv.split(X_train):
        X_tr, y_tr = X_train.iloc[train_idx], y_train.iloc[train_idx]
        X_val, y_val = X_train.iloc[val_idx], y_train.iloc[val_idx]
        modelo.fit(X_tr, y_tr)
        preds = modelo.predict(X_val)
        mapes.append(mean_absolute_percentage_error(y_val, preds) * 100)
    return np.mean(mapes)


def orquestar_pipeline(
    df_base: pd.DataFrame,
    targets: list = ["Price_Equipo1", "Price_Equipo2"],
    train_ratio: float = 0.70,
):
    reporte = []
    artefactos = {}

    for target in targets:
        df_features = GENERADORES_FEATURES[target](df_base)
        features_utilizadas = [
            c
            for c in df_features.columns
            if c
            not in [
                "Price_Equipo1",
                "Price_Equipo2",
                "Price_X",
                "Price_Y",
                "Price_Z",
            ]
        ]

        X_tr, X_te, y_tr, y_te, scaler = preparar_matrices(
            df_features, target, train_ratio
        )

        mejor_mape = float("inf")
        mejor_modelo = None
        nombre_ganador = ""
        metricas_ganador = {}

        for nombre, modelo_base in MODELOS_CANDIDATOS.items():
            modelo = clone(
                modelo_base
            )
            mape_cv = validacion_cruzada_ts(modelo, X_tr, y_tr)
            modelo.fit(X_tr, y_tr)
            preds = modelo.predict(X_te)
            metricas = evaluar_metricas(y_te, preds)

            reporte.append(
                {
                    "Target": target,
                    "Modelo": nombre,
                    **metricas,
                    "CV Train MAPE (%)": mape_cv,
                }
            )

            if metricas["MAPE (%)"] < mejor_mape:
                mejor_mape = metricas["MAPE (%)"]
                mejor_modelo = modelo
                nombre_ganador = nombre
                metricas_ganador = metricas

        # Empaquetado de producción
        paquete = {
            "target": target,
            "modelo_nombre": nombre_ganador,
            "modelo_obj": mejor_modelo,
            "scaler_obj": scaler,
            "feature_names": features_utilizadas,
            "metricas_test": metricas_ganador,
            "X_train": X_tr,
            "X_test": X_te,
            "y_test": y_te,
            "preds_test": mejor_modelo.predict(X_te),
        }

        ruta = os.path.join(DIR_ARTEFACTOS, f"pipeline_{target}.joblib")
        joblib.dump(paquete, ruta)

        artefactos[target] = paquete

    df_benchmark = pd.DataFrame(reporte).sort_values(
        by=["Target", "MAPE (%)"]
    )
    return df_benchmark, artefactos