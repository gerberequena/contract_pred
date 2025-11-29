import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# NO fijar seed para tener variedad en cada ejecución
# Si quieres resultados reproducibles, descomenta las siguientes líneas:
# np.random.seed(42)
# random.seed(42)

# Listas para generar datos realistas
SUPPLIERS = [
    "Accenture", "TCS", "Infosys", "Wipro", "Cognizant",
    "Capgemini", "Deloitte", "PWC", "KPMG", "EY",
    "Tech Solutions Inc", "Global IT Services", "DataCore Systems",
    "CloudMasters Ltd", "Digital Innovations", "Agile Consulting"
]

BUSINESS_UNITS = [
    "Technology", "Finance", "Operations", "Marketing",
    "Human Resources", "Sales", "Customer Service", "Product",
    "Engineering", "Data & Analytics"
]

PRIMARY_LOB = [
    "IT Infrastructure", "Application Development", "Data Engineering",
    "Cybersecurity", "Cloud Services", "Business Intelligence",
    "Project Management", "Quality Assurance", "DevOps",
    "Digital Transformation", "AI/ML Services"
]

SOW_TITLES = [
    "Software Development Services",
    "Data Engineering Team Augmentation",
    "Cloud Migration Support",
    "Cybersecurity Assessment and Remediation",
    "Business Intelligence Dashboard Development",
    "Mobile App Development",
    "Infrastructure Maintenance and Support",
    "QA Testing Services",
    "DevOps Pipeline Implementation",
    "SAP Implementation Services",
    "Salesforce Customization",
    "Network Security Enhancement",
    "Data Analytics Consulting",
    "UX/UI Design Services",
    "Technical Support Tier 2/3"
]

SOW_OWNERS = [
    "John Martinez", "Sarah Chen", "Michael Rodriguez", "Emily Johnson",
    "David Kim", "Lisa Anderson", "Robert Garcia", "Jennifer Lee",
    "William Brown", "Maria Santos", "James Wilson", "Patricia Davis",
    "Carlos Hernandez", "Amanda Taylor", "Daniel Moore"
]

SOW_STATUS = ["Active", "Active", "Active", "Active", "Pending Renewal"]

CURRENCIES = ["USD", "USD", "USD", "EUR", "GBP"]


def generate_sow_id(year, index):
    """Genera un SOW ID realista"""
    return f"SOW-{year}-{str(index).zfill(4)}"


def generate_contract_id(year, index):
    """Genera un Contract ID realista"""
    return f"CNT-{year}-{str(index).zfill(4)}"


def generate_realistic_workers(days_to_expire, budget):
    """
    Genera número de workers basado en lógica de negocio:
    - Contratos grandes (>500k) tienden a tener más workers
    - Contratos ya expirados tienen MUY BAJA probabilidad de tener workers
    - Contratos activos normales tienen más workers
    """
    # Si ya expiró, casi nunca tiene workers (solo 5% probabilidad)
    if days_to_expire < 0:
        return 0 if random.random() > 0.05 else random.randint(1, 2)
    
    # Contratos activos - asignar workers según budget
    if budget > 500000:
        return random.randint(10, 50)
    elif budget > 200000:
        return random.randint(5, 20)
    elif budget > 50000:
        return random.randint(1, 10)
    else:
        return random.randint(0, 5)


def generate_synthetic_sows(n_sows=150, add_criticals=True):
    """
    Genera dataset sintético de SOWs simulando data real de Fieldglass
    Si add_criticals=True, ajusta la distribución para tener más casos críticos
    """
    data = []
    
    today = datetime.now()
    
    # Si queremos casos críticos, ajustamos n_sows
    if add_criticals:
        n_sows = n_sows - 4  # Restar los 4 casos críticos que añadiremos después
    
    for i in range(n_sows):
        year = random.choice([2023, 2024, 2025])
        sow_id = generate_sow_id(year, i + 1)
        contract_id = generate_contract_id(year, i + 1)
        
        # Generar fechas de inicio y fin de forma más controlada
        # Queremos que la mayoría de contratos estén en un rango útil para el análisis
        contract_duration_days = random.choice([180, 270, 365, 545, 730])
        
        # Distribuir los contratos de forma más inteligente:
        # 80% expiran en el futuro (31 a +365 días desde hoy)
        # 15% expiran pronto (1 a 30 días)
        # 5% expiraron recientemente (-10 a 0 días) - MUY POCOS
        distribution = random.random()
        
        if distribution < 0.80:  # 80% - Contratos normales en el futuro
            days_to_expiration = random.randint(31, 365)
        elif distribution < 0.95:  # 15% - Contratos próximos a expirar
            days_to_expiration = random.randint(1, 30)
        else:  # 5% - Contratos recién expirados (SOLO unos pocos)
            days_to_expiration = random.randint(-10, 0)
        
        # Calcular end_date basado en days_to_expiration
        end_date = today + timedelta(days=days_to_expiration)
        start_date = end_date - timedelta(days=contract_duration_days)
        
        # Calcular días para expiración
        days_before_expiration = days_to_expiration  # Ya lo calculamos arriba
        
        # Generar budget realista
        budget = random.choice([
            random.randint(25000, 100000),
            random.randint(100000, 300000),
            random.randint(300000, 750000),
            random.randint(750000, 2000000)
        ])
        
        # Generar workers
        active_workers = generate_realistic_workers(days_before_expiration, budget)
        
        # Status basado en días de expiración
        if days_before_expiration < 0:
            status = "Expired"
        elif days_before_expiration < 30:
            status = random.choice(["Active", "Pending Renewal", "Active"])
        else:
            status = "Active"
        
        # Construir registro
        sow = {
            "SOW ID": sow_id,
            "# Days before expiration": days_before_expiration,
            "SOW Status": status,
            "SOW title": random.choice(SOW_TITLES),
            "Contract Id": contract_id,
            "Active SOW workers": active_workers,
            "Start Date": start_date.strftime("%Y-%m-%d"),
            "End date": end_date.strftime("%Y-%m-%d"),
            "Latest maximum budget": budget,
            "currency": random.choice(CURRENCIES),
            "supplier": random.choice(SUPPLIERS),
            "Business Unit": random.choice(BUSINESS_UNITS),
            "Primary LOB": random.choice(PRIMARY_LOB),
            "SOW owner": random.choice(SOW_OWNERS)
        }
        
        data.append(sow)
    
    # Crear DataFrame
    df = pd.DataFrame(data)
    
    # Ordenar por días antes de expiración (los más críticos primero)
    df = df.sort_values("# Days before expiration")
    
    return df


def add_critical_cases(df):
    """
    DEPRECATED - Ahora los casos críticos se crean en el main
    Esta función ya no se usa pero se mantiene por compatibilidad
    """
    return df


def generate_statistics(df):
    """Genera estadísticas del dataset para validación"""
    stats = {
        "Total SOWs": len(df),
        "SOWs Críticos (≤30 días)": len(df[df["# Days before expiration"] <= 30]),
        "SOWs con Workers": len(df[df["Active SOW workers"] > 0]),
        "SOWs Críticos con Workers": len(df[(df["# Days before expiration"] <= 30) & (df["Active SOW workers"] > 0)]),
        "Total Workers en Riesgo (≤30 días)": df[df["# Days before expiration"] <= 30]["Active SOW workers"].sum(),
        "Budget Total (USD)": df[df["currency"] == "USD"]["Latest maximum budget"].sum(),
        "Promedio Workers por SOW": df["Active SOW workers"].mean(),
        "SOWs Expirados": len(df[df["# Days before expiration"] < 0])
    }
    
    return stats


# MAIN EXECUTION
if __name__ == "__main__":
    print(" Generando datos sintéticos de SOWs...")
    print("-" * 60)
    
    # PRIMERO: Crear los 4 casos críticos
    print("\n Creando 4 casos críticos garantizados para la demo...\n")
    today = datetime.now()
    critical_cases = []
    
    # Caso 1: SOW MUY CRÍTICO con muchos workers (28 días)
    critical_cases.append({
        "SOW ID": "SOW-2024-CRIT-001",
        "# Days before expiration": 28,
        "SOW Status": "Active",
        "SOW title": "Enterprise Data Platform Development",
        "Contract Id": "CNT-2024-CRIT-001",
        "Active SOW workers": 25,
        "Start Date": (today - timedelta(days=337)).strftime("%Y-%m-%d"),
        "End date": (today + timedelta(days=28)).strftime("%Y-%m-%d"),
        "Latest maximum budget": 1500000,
        "currency": "USD",
        "supplier": "Accenture",
        "Business Unit": "Technology",
        "Primary LOB": "Data Engineering",
        "SOW owner": "Sarah Chen"
    })
    print("   ✓ Caso 1: 28 días, 25 workers - CRÍTICO")
    
    # Caso 2: SOW CRÍTICO con workers moderados (15 días)
    critical_cases.append({
        "SOW ID": "SOW-2024-CRIT-002",
        "# Days before expiration": 15,
        "SOW Status": "Active",
        "SOW title": "Cloud Infrastructure Migration",
        "Contract Id": "CNT-2024-CRIT-002",
        "Active SOW workers": 12,
        "Start Date": (today - timedelta(days=350)).strftime("%Y-%m-%d"),
        "End date": (today + timedelta(days=15)).strftime("%Y-%m-%d"),
        "Latest maximum budget": 850000,
        "currency": "USD",
        "supplier": "Deloitte",
        "Business Unit": "Technology",
        "Primary LOB": "Cloud Services",
        "SOW owner": "Michael Rodriguez"
    })
    print("   ✓ Caso 2: 15 días, 12 workers - CRÍTICO")
    
    # Caso 3: SOW YA EXPIRADO con workers (¡COMPLIANCE ISSUE!)
    critical_cases.append({
        "SOW ID": "SOW-2024-CRIT-003",
        "# Days before expiration": -5,
        "SOW Status": "Expired",
        "SOW title": "Cybersecurity Operations Support",
        "Contract Id": "CNT-2024-CRIT-003",
        "Active SOW workers": 8,
        "Start Date": (today - timedelta(days=370)).strftime("%Y-%m-%d"),
        "End date": (today - timedelta(days=5)).strftime("%Y-%m-%d"),
        "Latest maximum budget": 450000,
        "currency": "USD",
        "supplier": "Cognizant",
        "Business Unit": "Technology",
        "Primary LOB": "Cybersecurity",
        "SOW owner": "Jennifer Lee"
    })
    print("   ✓ Caso 3: -5 días (EXPIRADO), 8 workers - COMPLIANCE ISSUE!")
    
    # Caso 4: SOW crítico SIN workers (menos prioritario pero importante)
    critical_cases.append({
        "SOW ID": "SOW-2024-CRIT-004",
        "# Days before expiration": 20,
        "SOW Status": "Active",
        "SOW title": "Software License Management",
        "Contract Id": "CNT-2024-CRIT-004",
        "Active SOW workers": 0,
        "Start Date": (today - timedelta(days=345)).strftime("%Y-%m-%d"),
        "End date": (today + timedelta(days=20)).strftime("%Y-%m-%d"),
        "Latest maximum budget": 75000,
        "currency": "USD",
        "supplier": "Tech Solutions Inc",
        "Business Unit": "Finance",
        "Primary LOB": "IT Infrastructure",
        "SOW owner": "David Kim"
    })
    print("   ✓ Caso 4: 20 días, 0 workers - MEDIO")
    
    # Crear DataFrame de casos críticos
    df_critical = pd.DataFrame(critical_cases)
    
    # SEGUNDO: Generar el resto de SOWs (146 para llegar a 150 total)
    print("\n Generando 146 SOWs adicionales...")
    df_regular = generate_synthetic_sows(n_sows=146, add_criticals=False)
    
    # TERCERO: Combinar (críticos primero)
    df = pd.concat([df_critical, df_regular], ignore_index=True)
    
    # CUARTO: Ordenar por criticidad
    df = df.sort_values(
        by=["# Days before expiration", "Active SOW workers"],
        ascending=[True, False]
    ).reset_index(drop=True)
    
    # Guardar CSV
    output_file = "synthetic_sows_fieldglass.csv"
    df.to_csv(output_file, index=False)
    
    print(f" Dataset generado: {output_file}")
    print(f" Total de registros: {len(df)}")
    print("-" * 60)
    
    # Mostrar estadísticas
    print("\n ESTADÍSTICAS DEL DATASET:\n")
    stats = generate_statistics(df)
    for key, value in stats.items():
        if "Budget" in key:
            print(f"   {key}: ${value:,.0f}")
        elif "Promedio" in key:
            print(f"   {key}: {value:.1f}")
        else:
            print(f"   {key}: {value}")
    
    print("\n" + "-" * 60)
    print(" TOP 25 CASOS MÁS CRÍTICOS:\n")
    critical = df.head(25)
    print(critical[["SOW ID", "# Days before expiration", "Active SOW workers", "SOW Status", "SOW title"]].to_string(index=False))
    
    print("\n" + "-" * 60)
    print("  CASOS CON COMPLIANCE ISSUE (Expirados con Workers):\n")
    compliance_issues = df[(df["# Days before expiration"] < 0) & (df["Active SOW workers"] > 0)]
    if len(compliance_issues) > 0:
        print(compliance_issues[["SOW ID", "# Days before expiration", "Active SOW workers", "SOW owner"]].to_string(index=False))
    else:
        print("    No hay casos de compliance activos")
    
