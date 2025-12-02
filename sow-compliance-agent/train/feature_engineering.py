"""
Feature Engineering para Clasificador de Criticidad de SOWs
Este script transforma los datos del CSV en features útiles para ML
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from datetime import datetime
import warnings
#warnings.filterwarnings('ignore')

class SOWFeatureEngineering:
    """
    Clase para manejar el feature engineering de SOWs
    """
    
    def __init__(self):
        self.label_encoders = {}
        self.scaler = StandardScaler()
        
    def create_criticality_label(self, df):
        """
        Crea la etiqueta de criticidad basada en reglas de negocio
        
        Reglas:
        - CRÍTICO: ≤30 días Y workers > 0
        - ALTO: 31-60 días Y workers > 5, O ≤30 días sin workers
        - MEDIO: 61-90 días O 31-60 días con pocos workers
        - BAJO: >90 días
        """
        def classify(row):
            days = row['# Days before expiration']
            workers = row['Active SOW workers']
            
            # CRÍTICO: próximo a expirar con workers
            if days <= 30 and workers > 0:
                return 'CRÍTICO'
            
            # ALTO: próximo a expirar sin workers, o mediano plazo con muchos workers
            elif (days <= 30 and workers == 0) or (31 <= days <= 60 and workers > 5):
                return 'ALTO'
            
            # MEDIO: mediano plazo
            elif 31 <= days <= 90:
                return 'MEDIO'
            
            # BAJO: largo plazo
            else:
                return 'BAJO'
        
        df['Criticality'] = df.apply(classify, axis=1)
        return df
    
    def engineer_features(self, df):
        """
        Crea features derivadas útiles para el modelo
        """
        df = df.copy()
        
        # 1. Features temporales
        df['days_to_expire'] = df['# Days before expiration']
        df['is_expired'] = (df['days_to_expire'] < 0).astype(int)
        df['is_critical_window'] = (df['days_to_expire'] <= 30).astype(int)
        df['is_high_priority_window'] = ((df['days_to_expire'] > 30) & 
                                         (df['days_to_expire'] <= 60)).astype(int)
        
        # 2. Features de workers
        df['has_workers'] = (df['Active SOW workers'] > 0).astype(int)
        df['worker_count'] = df['Active SOW workers']
        df['worker_criticality_score'] = df['worker_count'] * df['is_critical_window']
        
        # 3. Features de budget (normalizado)
        df['budget_normalized'] = df['Latest maximum budget'] / 1_000_000  # En millones
        df['budget_per_worker'] = np.where(
            df['worker_count'] > 0,
            df['Latest maximum budget'] / df['worker_count'],
            0
        )
        
        # 4. Ratios y scores compuestos
        df['risk_score'] = (
            (30 - df['days_to_expire']) * df['has_workers'] * 
            (1 + np.log1p(df['worker_count']))
        )
        
        # 5. Features categóricas - Label Encoding
        categorical_cols = ['supplier', 'Business Unit', 'Primary LOB', 'currency']
        
        for col in categorical_cols:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                df[f'{col}_encoded'] = self.label_encoders[col].fit_transform(df[col].astype(str))
            else:
                df[f'{col}_encoded'] = self.label_encoders[col].transform(df[col].astype(str))
        
        return df
    
    def get_feature_columns(self):
        """
        Retorna las columnas que se usan como features para el modelo
        """
        return [
            'days_to_expire',
            'is_expired',
            'is_critical_window',
            'is_high_priority_window',
            'has_workers',
            'worker_count',
            'worker_criticality_score',
            'budget_normalized',
            'budget_per_worker',
            'risk_score',
            'supplier_encoded',
            'Business Unit_encoded',
            'Primary LOB_encoded',
            'currency_encoded'
        ]
    
    def prepare_for_training(self, df):
        """
        Prepara el dataset completo para entrenamiento
        """
        # Crear etiquetas de criticidad
        df = self.create_criticality_label(df)
        
        # Crear features
        df = self.engineer_features(df)
        
        # Obtener features y target
        feature_cols = self.get_feature_columns()
        X = df[feature_cols]
        y = df['Criticality']
        
        #Normalizar features numéricas (opcional pero recomendado)
        X_scaled = self.scaler.fit_transform(X)
        X = pd.DataFrame(X_scaled, columns=feature_cols)
        
        return X, y, df


def load_and_prepare_data(csv_path='/app/data/synthetic_sows_fieldglass.csv'):
    """
    Carga el CSV y prepara los datos para entrenamiento
    """
    print(" Cargando datos...")
    df = pd.read_csv(csv_path)
    print(f"   ✓ {len(df)} registros cargados")
    
    print("\n Aplicando feature engineering...")
    fe = SOWFeatureEngineering()
    X, y, df_processed = fe.prepare_for_training(df)
    
    print(f"   {X.shape[1]} features creadas")
    print(f"   Target variable: {y.name}")
    
    # Mostrar distribución de clases
    print("\n Distribución de Criticidad:")
    print(y.value_counts().sort_index())
    print(f"\n   Porcentajes:")
    print(y.value_counts(normalize=True).sort_index() * 100)
    
    return X, y, df_processed, fe


def explore_features(X, y):
    """
    Explora las features creadas
    """
    print("\n ANÁLISIS DE FEATURES:\n")
    print("-" * 10)
    
    # Features por criticidad
    df_analysis = pd.concat([X, y], axis=1)
    
    print("\n Promedio de features por nivel de criticidad:\n")
    summary = df_analysis.groupby('Criticality')[
        ['days_to_expire', 'worker_count', 'budget_normalized', 'risk_score']
    ].mean()
    print(summary)
    
    print("\n" + "-" * 10)
    print(" Feature engineering completado")
    
    return df_analysis


# MAIN EXECUTION
if __name__ == "__main__":
    print("=" * 60)
    print("  FEATURE ENGINEERING - SOW CRITICALITY CLASSIFIER")
    print("=" * 60)
    
    # Cargar y preparar datos
    X, y, df_processed, fe = load_and_prepare_data('synthetic_sows_fieldglass.csv')
    
    # Explorar features
    df_analysis = explore_features(X, y)
    
    # Guardar datos procesados
    output_file = '/app/data/processed_sows_with_features.csv'
    df_processed.to_csv(output_file, index=False)
