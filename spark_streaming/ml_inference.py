"""
ml_inference.py — Member 2, Task 2.3 (Flight Data)
ML-based anomaly detection for flight tracking data.
"""

import json
import logging
import os
from typing import Optional, Tuple

import joblib
import pandas as pd
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, lit, pandas_udf
from pyspark.sql.types import BooleanType, DoubleType, StringType

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Model Loading
# ═══════════════════════════════════════════════════════════════════════════

_BASE   = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_BASE)

MODEL_PATH    = os.path.join(_PARENT, "models", "flight_anomaly_detector.pkl")
SCALER_PATH   = os.path.join(_PARENT, "models", "flight_scaler.pkl")
FEATURES_PATH = os.path.join(_PARENT, "models", "flight_features.json")


class ModelLoader:
    """Singleton model loader."""
    
    _instance = None
    _model = None
    _scaler = None
    _features = None
    _loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load(self) -> Tuple[Optional[object], Optional[object], Optional[list]]:
        """Load model artefacts (cached)."""
        if self._loaded:
            return self._model, self._scaler, self._features
        
        try:
            self._model   = joblib.load(MODEL_PATH)
            self._scaler  = joblib.load(SCALER_PATH)
            
            with open(FEATURES_PATH) as f:
                self._features = json.load(f)
            
            logger.info(f"✅ ML model loaded: {MODEL_PATH}")
            logger.info(f"   Features: {self._features}")
            
            self._loaded = True
            
        except FileNotFoundError:
            logger.warning(
                f"⚠️  Model files not found. Run: python models/train_model.py\n"
                "   ML predictions will use safe defaults."
            )
            self._loaded = True
            
        except Exception as e:
            logger.error(f"❌ Error loading model: {e}", exc_info=True)
            self._loaded = True
        
        return self._model, self._scaler, self._features


_loader = ModelLoader()
_model, _scaler, _feature_names = _loader.load()


# ═══════════════════════════════════════════════════════════════════════════
# Pandas UDFs
# ═══════════════════════════════════════════════════════════════════════════

@pandas_udf(DoubleType())
def udf_anomaly_score(
    velocity: pd.Series,
    baro_altitude: pd.Series,
    vertical_rate: pd.Series,
    hour: pd.Series,
    day_of_week: pd.Series,
) -> pd.Series:
    """Compute flight anomaly score (0-1)."""
    if _model is None:
        return pd.Series([0.0] * len(velocity))
    
    try:
        X = pd.DataFrame({
            "velocity":      velocity.fillna(0.0),
            "baro_altitude": baro_altitude.fillna(0.0),
            "vertical_rate": vertical_rate.fillna(0.0),
            "hour":          hour.fillna(0).astype(int),
            "day_of_week":   day_of_week.fillna(1).astype(int),
        })
        
        X_scaled = _scaler.transform(X)
        raw_scores = _model.score_samples(X_scaled)
        
        # Normalize to 0-1
        scores = pd.Series(raw_scores)
        if scores.std() > 0:
            normalized = (-scores - (-scores).min()) / ((-scores).max() - (-scores).min())
        else:
            normalized = pd.Series([0.5] * len(scores))
        
        return normalized.clip(0.0, 1.0)
        
    except Exception as e:
        logger.error(f"Error in udf_anomaly_score: {e}")
        return pd.Series([0.5] * len(velocity))


@pandas_udf(BooleanType())
def udf_is_anomaly(
    velocity: pd.Series,
    baro_altitude: pd.Series,
    vertical_rate: pd.Series,
    hour: pd.Series,
    day_of_week: pd.Series,
) -> pd.Series:
    """Binary anomaly classification."""
    if _model is None:
        return pd.Series([False] * len(velocity))
    
    try:
        X = pd.DataFrame({
            "velocity":      velocity.fillna(0.0),
            "baro_altitude": baro_altitude.fillna(0.0),
            "vertical_rate": vertical_rate.fillna(0.0),
            "hour":          hour.fillna(0).astype(int),
            "day_of_week":   day_of_week.fillna(1).astype(int),
        })
        
        X_scaled = _scaler.transform(X)
        predictions = _model.predict(X_scaled)
        
        return pd.Series(predictions == -1)
        
    except Exception as e:
        logger.error(f"Error in udf_is_anomaly: {e}")
        return pd.Series([False] * len(velocity))


@pandas_udf(StringType())
def udf_anomaly_reason(
    velocity: pd.Series,
    baro_altitude: pd.Series,
    vertical_rate: pd.Series,
    ml_score: pd.Series,
) -> pd.Series:
    """Explain why flight is anomalous."""
    reasons = []
    
    for i in range(len(velocity)):
        if ml_score.iloc[i] < 0.3:
            reasons.append("normal")
            continue
        
        reason_parts = []
        
        # Speed analysis
        if velocity.iloc[i] > 800:
            reason_parts.append("extreme_speed")
        elif velocity.iloc[i] < 50 and baro_altitude.iloc[i] > 1000:
            reason_parts.append("suspiciously_slow")
        
        # Altitude analysis
        if baro_altitude.iloc[i] > 14000:
            reason_parts.append("extreme_altitude")
        elif baro_altitude.iloc[i] < 500 and velocity.iloc[i] > 200:
            reason_parts.append("dangerously_low")
        
        # Vertical rate analysis
        if abs(vertical_rate.iloc[i]) > 20:
            reason_parts.append("extreme_climb_descent")
        
        if reason_parts:
            reasons.append(",".join(reason_parts))
        else:
            reasons.append("statistical_anomaly")
    
    return pd.Series(reasons)


# ═══════════════════════════════════════════════════════════════════════════
# High-level API
# ═══════════════════════════════════════════════════════════════════════════

class FlightMLInference:
    """Task 2.3 — Apply ML predictions to flight data."""

    @staticmethod
    def apply_ml_predictions(df: DataFrame, threshold: float = 0.7) -> DataFrame:
        """Apply flight anomaly detection."""
        if _model is None:
            logger.warning("⚠️  Model not loaded. Using fallback values.")
            return (
                df
                .withColumn("ml_anomaly_score",  lit(0.0))
                .withColumn("ml_is_anomaly",     lit(False))
                .withColumn("ml_anomaly_reason", lit("model_unavailable"))
            )

        logger.info("▶ FlightMLInference.apply_ml_predictions")

        # Required columns check
        required = ["velocity", "baro_altitude", "vertical_rate", "hour", "day_of_week"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        df_with_ml = (
            df
            .withColumn(
                "ml_anomaly_score",
                udf_anomaly_score(
                    col("velocity"),
                    col("baro_altitude"),
                    col("vertical_rate"),
                    col("hour"),
                    col("day_of_week"),
                )
            )
            .withColumn(
                "ml_is_anomaly",
                udf_is_anomaly(
                    col("velocity"),
                    col("baro_altitude"),
                    col("vertical_rate"),
                    col("hour"),
                    col("day_of_week"),
                )
            )
            .withColumn(
                "ml_anomaly_reason",
                udf_anomaly_reason(
                    col("velocity"),
                    col("baro_altitude"),
                    col("vertical_rate"),
                    col("ml_anomaly_score"),
                )
            )
        )

        logger.info("✅ FlightMLInference.apply_ml_predictions — complete")
        return df_with_ml

    @staticmethod
    def get_model_info() -> dict:
        """Return model metadata."""
        if _model is None:
            return {"loaded": False, "reason": "Model files not found"}
        
        return {
            "loaded": True,
            "model_type": type(_model).__name__,
            "features": _feature_names,
            "model_path": MODEL_PATH,
        }