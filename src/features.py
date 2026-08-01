import pandas as pd


def crear_features_equipo1(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["Z_lag1"] = data["Price_Z"].shift(1)
    data["Z_lag2"] = data["Price_Z"].shift(2)
    data["X_lag1"] = data["Price_X"].shift(1)
    data["X_lag2"] = data["Price_X"].shift(2)
    data["Z_mean_6m"] = (
        data["Price_Z"].rolling(window=6).mean().shift(1)
    )
    data["Eq1_lag1"] = data["Price_Equipo1"].shift(1)
    return data.dropna()


def crear_features_equipo2(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["Z_lag0"] = data["Price_Z"]
    data["Y_lag0"] = data["Price_Y"]
    data["Eq2_lag1"] = data["Price_Equipo2"].shift(1)
    return data.dropna()