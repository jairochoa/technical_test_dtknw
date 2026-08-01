import pandas as pd


def crear_features_equipo1(df: pd.DataFrame) -> pd.DataFrame:
    """
    Matriz de características exógenas puras en Primera Diferencia (I(0)).
    Eliminamos el rezago autorregresivo (Eq1_lag1) y la media móvil (Z_mean_6m)
    para evitar el efecto sombra y la compresión de amplitud.
    """
    data = df.copy()

    # 1. Diferenciación I(0) - Cambios mensuales en dólares (ΔP)
    d_eq1 = data["Price_Equipo1"].diff(1)
    d_z = data["Price_Z"].diff(1)
    d_x = data["Price_X"].diff(1)
    d_y = data["Price_Y"].diff(1)  # Probemos si Y aporta señal al Equipo 1

    # 2. Target en primera diferencia
    data["Price_Equipo1"] = d_eq1

    # 3. Shocks contemporáneos (Lag 0) para sincronización instantánea
    data["Z_lag0"] = d_z
    data["X_lag0"] = d_x
    data["Y_lag0"] = d_y

    # 4. Rezagos de transmisión de materias primas (Lag 1 y 2)
    data["Z_lag1"] = d_z.shift(1)
    data["Z_lag2"] = d_z.shift(2)
    data["X_lag1"] = d_x.shift(1)
    data["X_lag2"] = d_x.shift(2)

    # Nota: Eliminamos intencionalmente Eq1_lag1 y Z_mean_6m
    return data.dropna()


def crear_features_equipo2(df: pd.DataFrame) -> pd.DataFrame:
    """
    Genera matriz de características para Equipo 2 en Primera Diferencia (I(0)).
    Captura la indexación contemporánea (Lag 0) sobre cambios mensuales en USD.
    """
    data = df.copy()

    # 1. Diferenciación I(0) - Cambios mensuales en dólares (ΔP)
    d_eq2 = data["Price_Equipo2"].diff(1)
    d_z = data["Price_Z"].diff(1)
    d_y = data["Price_Y"].diff(1)

    # 2. Sobreescribimos el target con su primera diferencia (Δ en USD)
    data["Price_Equipo2"] = d_eq2

    # 3. Transmisión contemporánea (Lag 0) de las diferencias
    data["Z_lag0"] = d_z
    data["Y_lag0"] = d_y

    # 4. Inercia autorregresiva de la variación del Equipo 2
    data["Eq2_lag1"] = d_eq2.shift(1)

    return data.dropna()