"""
Entrenamiento del Clasificador de Criticidad de SOWs
Usa RandomForest para clasificar SOWs en: CRÍTICO, ALTO, MEDIO, BAJO
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Importar el feature engineering
import sys
sys.path.append('.')
from feature_engineering import load_and_prepare_data, SOWFeatureEngineering


class CriticalityClassifier:
    """
    Clasificador de Criticidad de SOWs
    """
    
    def __init__(self, model_type='random_forest'):
        self.model_type = model_type
        self.model = None
        self.feature_engineer = None
        self.training_date = None
        self.metrics = {}
        
    def train(self, X_train, y_train, X_test, y_test):
        """
        Entrena el modelo y evalúa performance
        """
        print("\n Entrenando modelo...")
        print(f"   Tipo: {self.model_type}")
        print(f"   Training set: {X_train.shape[0]} muestras")
        print(f"   Test set: {X_test.shape[0]} muestras")
        
        # Seleccionar modelo
        if self.model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == 'gradient_boosting':
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            )
        
        # Entrenar
        self.model.fit(X_train, y_train)
        print("   Modelo entrenado.")
        
        # Evaluar
        print("\n Evaluando modelo...")
        self._evaluate(X_train, y_train, X_test, y_test)
        
        self.training_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    def _evaluate(self, X_train, y_train, X_test, y_test):
        """
        Evalúa el modelo en train y test set
        """
        # Predicciones
        y_train_pred = self.model.predict(X_train)
        y_test_pred = self.model.predict(X_test)
        
        # Accuracy
        train_acc = accuracy_score(y_train, y_train_pred)
        test_acc = accuracy_score(y_test, y_test_pred)
        
        self.metrics = {
            'train_accuracy': train_acc,
            'test_accuracy': test_acc,
            'train_size': len(X_train),
            'test_size': len(X_test)
        }
        
        print(f"\n   Train Accuracy: {train_acc:.2%}")
        print(f"   Test Accuracy:  {test_acc:.2%}")
        
        # Classification report
        print("\n" + "-" * 10)
        print("CLASSIFICATION REPORT (Test Set):")
        print("-" * 10)
        print(classification_report(y_test, y_test_pred))
        
        # Confusion matrix
        print("-" * 10)
        print("CONFUSION MATRIX (Test Set):")
        print("-" * 10)
        cm = confusion_matrix(y_test, y_test_pred, 
                            labels=['BAJO', 'MEDIO', 'ALTO', 'CRÍTICO'])
        cm_df = pd.DataFrame(
            cm,
            index=['BAJO', 'MEDIO', 'ALTO', 'CRÍTICO'],
            columns=['BAJO', 'MEDIO', 'ALTO', 'CRÍTICO']
        )
        print(cm_df)
        print()
        
        # Feature importance
        if hasattr(self.model, 'feature_importances_'):
            self._print_feature_importance(X_train.columns)
    
    def _print_feature_importance(self, feature_names, top_n=10):
        """
        Muestra las features más importantes
        """
        importances = self.model.feature_importances_
        indices = np.argsort(importances)[::-1][:top_n]
        
        print("-" * 60)
        print(f"TOP {top_n} FEATURES MÁS IMPORTANTES:")
        print("-" * 60)
        for i, idx in enumerate(indices, 1):
            print(f"   {i}. {feature_names[idx]}: {importances[idx]:.4f}")
        print()
    
    def predict(self, X):
        """
        Predice criticidad para nuevos datos
        """
        return self.model.predict(X)
    
    def predict_proba(self, X):
        """
        Predice probabilidades por clase
        """
        return self.model.predict_proba(X)
    
    def save_model(self, filepath='models/criticality_model.pkl'):
        """
        Guarda el modelo entrenado
        """
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        model_package = {
            'model': self.model,
            'model_type': self.model_type,
            'training_date': self.training_date,
            'metrics': self.metrics,
            'feature_names': self.model.feature_names_in_.tolist() if hasattr(self.model, 'feature_names_in_') else None
        }
        
        joblib.dump(model_package, filepath)
        
        # Guardar métricas en JSON
        metrics_file = filepath.replace('.pkl', '_metrics.json')
        with open(metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
    
    @staticmethod
    def load_model(filepath='models/criticality_model.pkl'):
        """
        Carga un modelo previamente entrenado
        """
        model_package = joblib.load(filepath)
        
        classifier = CriticalityClassifier(model_type=model_package['model_type'])
        classifier.model = model_package['model']
        classifier.training_date = model_package['training_date']
        classifier.metrics = model_package['metrics']
        
        print(f"   Entrenado: {classifier.training_date}")
        print(f"   Test Accuracy: {classifier.metrics['test_accuracy']:.2%}")
        
        return classifier


def validate_critical_cases(classifier, df_processed, fe):
    """
    Valida que el modelo identifique correctamente los casos críticos predefinidos
    """
    print("\n" + "-" * 10)
    print(" VALIDACIÓN DE CASOS CRÍTICOS:")
    print("-" * 10)
    
    # Filtrar los 4 casos críticos
    critical_sows = df_processed[df_processed['SOW ID'].str.contains('CRIT', na=False)]
    
    if len(critical_sows) == 0:
        print("  No se encontraron casos críticos en el dataset")
        return
    
    # Preparar features
    feature_cols = fe.get_feature_columns()
    X_critical = critical_sows[feature_cols]
    
    # Predecir
    predictions = classifier.predict(X_critical)
    
    # Mostrar resultados
    results = critical_sows[['SOW ID', 'SOW title', '# Days before expiration', 
                             'Active SOW workers', 'Criticality']].copy()
    results['Predicción'] = predictions
    results['✓'] = results['Criticality'] == results['Predicción']
    
    print("\n" + results.to_string(index=False))
    
    accuracy = (results['✓'].sum() / len(results)) * 100
    print(f"\n    Accuracy en casos críticos: {accuracy:.1f}%")
    
    if accuracy < 75:
        print("     ALERTA: El modelo no está identificando bien los casos críticos")
    else:
        print("    El modelo identifica correctamente los casos críticos")


# MAIN EXECUTION
if __name__ == "__main__":
    print("-" * 10)
    print("  ENTRENAMIENTO - SOW CRITICALITY CLASSIFIER")
    print("-" * 10)
    
    # 1. Cargar y preparar datos
    X, y, df_processed, fe = load_and_prepare_data('/app/data/synthetic_sows_fieldglass.csv')

    # 2. Split train/test
    print("\n Dividiendo datos en train/test...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, 
        test_size=0.2, 
        random_state=42,
        stratify=y  # Mantener proporción de clases
    )
    print(f"   ✓ Train: {len(X_train)} | Test: {len(X_test)}")
    
    # 3. Entrenar modelo
    classifier = CriticalityClassifier(model_type='random_forest')
    classifier.train(X_train, y_train, X_test, y_test)
    classifier.feature_engineer = fe
    
    # 4. Validar con casos críticos
    validate_critical_cases(classifier, df_processed, fe)
    
    # 5. Guardar modelo
    classifier.save_model('/app/models/criticality_model.pkl')

    # 6. Guardar feature engineer
    joblib.dump(fe, '/app/models/feature_engineer.pkl')

    print(" Feature Engineer guardado en: models/feature_engineer.pkl")
    
    print("\n" + "-" * 10)
    print(" ENTRENAMIENTO COMPLETADO")
    print("-" * 10)
    print(f"    Test Accuracy: {classifier.metrics['test_accuracy']:.2%}")
    print(f"   Modelo: models/criticality_model.pkl")