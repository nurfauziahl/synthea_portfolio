import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import seaborn as sns
import os
from dotenv import load_dotenv

# --- KONFIGURASI & SETUP ---
def get_db_connection():
    """Memuat env var dan membuat koneksi ke database."""
    load_dotenv()
    
    DB_USER = os.getenv('DB_USER')
    DB_PASS = os.getenv('DB_PASS')
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT')
    DB_NAME = os.getenv('DB_NAME')

    print("✅ Mencoba terhubung ke Database...")
    if not DB_PASS:
        print("❌ ERROR: Password tidak ditemukan di file .env!")
        return None

    db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    try:
        engine = create_engine(db_url)
        connection = engine.connect()
        print("✅ Koneksi Sukses!")
        return connection
    except Exception as e:
        print(f"❌ Koneksi Gagal: {e}")
        return None

def ensure_directory_exists(path):
    """Memastikan folder output tersedia."""
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

# --- FUNGSI ANALISIS 1: TOP MEDICATIONS ---
def analyze_top_medications(conn):
    print("\n💊 ANALISIS 1: Top 10 High-Cost Medications")
    
    query = """
    SELECT 
        medication_description as medication_name,
        SUM(total_cost) as total_spend
    FROM mart.medications
    GROUP BY 1
    ORDER BY 2 DESC
    LIMIT 10;
    """
    df = pd.read_sql(query, conn)
    
    # Visualisasi
    plt.figure(figsize=(12, 6))
    sns.barplot(data=df, x='total_spend', y='medication_name', hue='medication_name', palette='viridis', legend=False)
    plt.title('Top 10 High-Cost Medications', fontsize=14, fontweight='bold')
    plt.xlabel('Total Spend ($)')
    plt.tight_layout()
    
    output_path = 'output/visualization/python_top_medications.jpg'
    ensure_directory_exists(output_path)
    plt.savefig(output_path)
    print(f"   🎉 Grafik disimpan: {output_path}")

    # Business Insight
    top_drug = df.iloc[0]['medication_name']
    top_val = df.iloc[0]['total_spend']
    print(f"\n🧠 BUSINESS INTERPRETATION:")
    print(f"   - The cost driver is dominated by '{top_drug}' (${top_val:,.0f}).")
    print("   - Strategy: Negotiate volume discounts for this specific SKU.")

# --- FUNGSI ANALISIS 2: CORRELATION ---
def analyze_correlation(conn):
    print("\n📈 ANALISIS 2: Age vs. Cost Correlation")
    
    query = """
    SELECT 
        DATE_PART('year', AGE(p."BIRTHDATE"::DATE)) as age,
        SUM(m.total_cost) as total_medication_cost
    FROM mart.medications m
    JOIN raw.patients p ON m.patient_id = p."Id"
    GROUP BY 1
    """
    df = pd.read_sql(query, conn)
    correlation = df['age'].corr(df['total_medication_cost'])
    
    # Visualisasi
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x='age', y='total_medication_cost', alpha=0.6, color='blue')
    plt.title(f'Correlation: Age vs Cost (r={correlation:.2f})', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.5)
    
    output_path = 'output/visualization/python_age_cost_correlation.jpg'
    ensure_directory_exists(output_path)
    plt.savefig(output_path)
    print(f"   🎉 Grafik disimpan: {output_path}")
    
    # Business Insight
    print(f"\n🧠 BUSINESS INTERPRETATION (r = {correlation:.2f}):")
    if abs(correlation) < 0.2:
        print("   - Patient age is NOT a strong predictor of medication cost.")
        print("   - Insight: High costs are likely driven by acute, event-based treatments rather than chronic aging conditions.")
    else:
        print("   - There is a noticeable correlation between age and spending.")

# --- FUNGSI ANALISIS 3: SEGMENTATION ---
def analyze_segmentation(conn):
    print("\n👥 ANALISIS 3: Patient Segmentation (4-Quadrant)")
    
    query = """
    SELECT 
        p."Id" as patient_id,
        p."FIRST" || ' ' || p."LAST" as patient_name,
        COUNT(DISTINCT e."Id") as total_encounters,
        COALESCE(SUM(m.total_cost), 0) as total_med_cost
    FROM raw.patients p
    LEFT JOIN raw.encounters e ON p."Id" = e."PATIENT"
    LEFT JOIN mart.medications m ON p."Id" = m.patient_id
    GROUP BY 1, 2
    """
    df = pd.read_sql(query, conn)
    
    # Hitung Threshold
    cost_threshold = df['total_med_cost'].quantile(0.75)
    util_threshold = df['total_encounters'].quantile(0.75)
    
    print("\n📐 SEGMENTATION LOGIC:")
    print(f"   - High Cost Threshold : > ${cost_threshold:,.2f} (Top 25%)")
    print(f"   - High Util Threshold : > {util_threshold:.0f} Visits (Top 25%)")

    # Klasifikasi
    def classify(row):
        if row['total_med_cost'] >= cost_threshold and row['total_encounters'] >= util_threshold:
            return 'HighCost - HighUtil'
        elif row['total_med_cost'] >= cost_threshold:
            return 'HighCost - LowUtil'
        elif row['total_encounters'] >= util_threshold:
            return 'LowCost - HighUtil'
        else:
            return 'LowCost - LowUtil'

    df['segment'] = df.apply(classify, axis=1)
    
    # Visualisasi
    plt.figure(figsize=(10, 6))
    sns.countplot(
        data=df, x='segment', hue='segment', legend=False,
        order=['HighCost - HighUtil', 'HighCost - LowUtil', 'LowCost - HighUtil', 'LowCost - LowUtil'],
        palette='magma'
    )
    plt.title('Patient Segmentation Distribution', fontsize=14)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    
    output_path = 'output/visualization/python_patient_segmentation.jpg'
    ensure_directory_exists(output_path)
    plt.savefig(output_path)
    print(f"   🎉 Grafik disimpan: {output_path}")
    
    # Simpan List Prioritas ke Excel
    print("\n🚨 EXPORTING HIGH PRIORITY LIST:")
    high_priority = df[df['segment'] == 'HighCost - HighUtil'].sort_values(by='total_med_cost', ascending=False)
    
    # Pastikan folder ada
    excel_path = "output/analysis/python_high_priority_patients.xlsx"
    ensure_directory_exists(excel_path)
    
    high_priority.to_excel(excel_path, index=False)
    print(f"   📁 Excel Client-Ready saved to: {excel_path}")
    print(f"   ℹ️  Total High Priority Patients: {len(high_priority)}")

# --- FUNGSI ANALISIS 4: COST CONCENTRATION ---
def analyze_cost_concentration(conn):
    print("\n💰 ANALISIS 4: Cost Concentration Index")
    
    query = """
    SELECT 
        medication_description, 
        SUM(total_cost) as total_cost
    FROM mart.medications
    GROUP BY 1
    ORDER BY 2 DESC
    """
    df = pd.read_sql(query, conn)
    total_spend = df['total_cost'].sum()
    
    top_1_share = (df.iloc[0]['total_cost'] / total_spend) * 100
    top_5_share = (df.head(5)['total_cost'].sum() / total_spend) * 100
    
    print("\n📊 TABLE: Cost Concentration")
    print("=" * 45)
    print(f"{'Metric':<20} | {'% Share':<20}")
    print("-" * 45)
    print(f"{'Top 1 Drug':<20} | {top_1_share:.2f}%")
    print(f"{'Top 5 Drugs':<20} | {top_5_share:.2f}%")
    print("=" * 45)
    
    print("\n🧠 BUSINESS INTERPRETATION:")
    print("   - Extreme Pareto Distribution detected.")
    print("   - Risk Mitigation: Ensure supply chain stability for the Top 5 drugs.")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    connection = get_db_connection()
    if connection:
        analyze_top_medications(connection)
        analyze_correlation(connection)
        analyze_segmentation(connection)
        analyze_cost_concentration(connection)
        connection.close()
        print("\n✅ All Analyses Completed Successfully.")
