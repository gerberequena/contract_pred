# Modelos Entrenados

## Archivos:
- `criticality_model.pkl`: Modelo RandomForest entrenado
- `feature_engineer.pkl`: Objeto SOWFeatureEngineering para transformar datos
- `criticality_model_metrics.json`: Métricas del modelo

## Cómo usar:
```python
import joblib
import pandas as pd

# 1. Cargar modelo y feature engineer
model = joblib.load('models/criticality_model.pkl')
fe = joblib.load('models/feature_engineer.pkl')

# 2. Cargar CSV nuevo
df = pd.read_csv('data/synthetic_sows_fieldglass.csv')

# 3. Transformar datos
X = fe.engineer_features(df)

# 4. Predecir criticidad
predictions = model.predict(X)

# 5. Añadir predicciones al DataFrame
df['Predicted_Criticality'] = predictions

# 6. Ejemplo de output
print(df[['SOW ID', '# Days before expiration', 'Active SOW workers', 'Predicted_Criticality']].head())
```

## Clases de Criticidad:
- `CRÍTICO`: ≤30 días + workers >0
- `ALTO`: ≤30 días sin workers, o 31-60 días con >5 workers
- `MEDIO`: 31-90 días
- `BAJO`: >90 días