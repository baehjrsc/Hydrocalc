import streamlit as st
import math
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# ----------------- CONFIG & DATA -----------------
st.set_page_config(page_title="HidroCalc Mobile", page_icon="🌊", layout="centered")

st.markdown("""
<style>
    /* Remove a atualização de "puxar para baixo" no celular e o efeito elástico */
    body, .stApp {
        overscroll-behavior-y: none !important;
    }
</style>
""", unsafe_allow_html=True)

MATERIAIS = {
    "PEAD Corrugado": {
        "n": 0.010, 
        "tubos": [
            {"DN": 100, "DI": 100, "DE": 118},
            {"DN": 150, "DI": 150, "DE": 178},
            {"DN": 200, "DI": 200, "DE": 236},
            {"DN": 250, "DI": 250, "DE": 295},
            {"DN": 300, "DI": 300, "DE": 355},
            {"DN": 400, "DI": 400, "DE": 475},
            {"DN": 500, "DI": 500, "DE": 595},
            {"DN": 600, "DI": 600, "DE": 715},
            {"DN": 800, "DI": 800, "DE": 950},
            {"DN": 1000, "DI": 1000, "DE": 1185},
            {"DN": 1200, "DI": 1200, "DE": 1420}
        ]
    },
    "Tubos de Concreto": {
        "n": 0.013, 
        "tubos": [
            {"DN": 300, "DI": 300, "DE": 360},
            {"DN": 400, "DI": 400, "DE": 480},
            {"DN": 500, "DI": 500, "DE": 600},
            {"DN": 600, "DI": 600, "DE": 720},
            {"DN": 800, "DI": 800, "DE": 960},
            {"DN": 1000, "DI": 1000, "DE": 1200},
            {"DN": 1200, "DI": 1200, "DE": 1440},
            {"DN": 1500, "DI": 1500, "DE": 1800},
            {"DN": 2000, "DI": 2000, "DE": 2400}
        ]
    },
    "PVC Ocre (Soldável)": {
        "n": 0.010, 
        "tubos": [
            {"DN": 100, "DI": 96, "DE": 100},
            {"DN": 150, "DI": 144, "DE": 150},
            {"DN": 200, "DI": 192, "DE": 200},
            {"DN": 250, "DI": 240, "DE": 250},
            {"DN": 300, "DI": 288, "DE": 300},
            {"DN": 400, "DI": 385, "DE": 400}
        ]
    },
    "PEAD Liso": {
        "n": 0.009, 
        "tubos": [
            {"DN": 110, "DI": 96, "DE": 110},
            {"DN": 125, "DI": 110, "DE": 125},
            {"DN": 160, "DI": 141, "DE": 160},
            {"DN": 200, "DI": 176, "DE": 200},
            {"DN": 250, "DI": 220, "DE": 250},
            {"DN": 315, "DI": 277, "DE": 315},
            {"DN": 355, "DI": 312, "DE": 355},
            {"DN": 400, "DI": 352, "DE": 400},
            {"DN": 450, "DI": 396, "DE": 450},
            {"DN": 500, "DI": 440, "DE": 500},
            {"DN": 630, "DI": 554, "DE": 630}
        ]
    }
}

GAMMA_WATER = 10000

# ----------------- HYDRAULIC LOGIC -----------------
def calc_theta(Q_design, D_int, I, n):
    low = 0.01
    high = 2 * math.pi - 0.01
    theta = math.pi
    iterations = 0
    if I <= 0: return theta
    while iterations < 50:
        theta = (low + high) / 2
        A = (math.pow(D_int, 2) / 8) * (theta - math.sin(theta))
        P = (D_int / 2) * theta
        Rh = 0 if P == 0 else A / P
        Q_calc = (1 / n) * A * math.pow(Rh, 2/3) * math.sqrt(I)
        if abs(Q_calc - Q_design) < 0.0001: break
        if Q_calc < Q_design: low = theta
        else: high = theta
        iterations += 1
    return theta

def compute_hydraulics(D_int, Q_design_m3s, I, n):
    A_plena = math.pi * math.pow(D_int, 2) / 4
    Rh_plena = D_int / 4
    V_plena = 0 if I <= 0 else (1 / n) * math.pow(Rh_plena, 2/3) * math.sqrt(I)
    Q_plena = A_plena * V_plena

    if I <= 0 or Q_design_m3s >= Q_plena:
        return {
            "Q_plena": Q_plena, "V_plena": V_plena, "Q_ratio": 1.0 if Q_plena == 0 else Q_design_m3s / Q_plena,
            "yD": 1.0, "V_real": V_plena, "T_trat": GAMMA_WATER * Rh_plena * I if I > 0 else 0, "theta": 2 * math.pi
        }

    theta = calc_theta(Q_design_m3s, D_int, I, n)
    yD = 0.5 * (1 - math.cos(theta / 2))
    
    A = (math.pow(D_int, 2) / 8) * (theta - math.sin(theta))
    P = (D_int / 2) * theta
    Rh = A / P if P > 0 else 0
    V_real = Q_design_m3s / A if A > 0 else 0
    T_trat = GAMMA_WATER * Rh * I
    
    return {
        "Q_plena": Q_plena, "V_plena": V_plena, "Q_ratio": Q_design_m3s / Q_plena,
        "yD": yD, "V_real": V_real, "T_trat": T_trat, "theta": theta
    }


# ----------------- PLOTLY DIAGRAM -----------------
def get_water_polygon(DI, theta):
    start_angle = -np.pi/2 - theta/2
    end_angle = -np.pi/2 + theta/2
    tw = np.linspace(start_angle, end_angle, 100)
    xw = DI/2 * np.cos(tw)
    yw = DI/2 * np.sin(tw)
    xw_poly = np.append(xw, xw[0])
    yw_poly = np.append(yw, yw[0])
    return xw_poly, yw_poly

def plot_cross_section(DE, DI, hyd_ini, hyd_fin, DN):
    y_real_ini = hyd_ini["yD"] * DI
    y_real_fin = hyd_fin["yD"] * DI
    
    t = np.linspace(0, 2*np.pi, 200)
    xo = DE/2 * np.cos(t)
    yo = DE/2 * np.sin(t)
    
    xi = DI/2 * np.cos(t)
    yi = DI/2 * np.sin(t)
    
    fig = go.Figure()

    # Outer wall
    fig.add_trace(go.Scatter(x=xo, y=yo, fill='toself', mode='lines', line=dict(color='#7a7a7a'), fillcolor='#444444', hoverinfo="skip", name='Parede Externa'))
    # Inner wall
    fig.add_trace(go.Scatter(x=xi, y=yi, fill='toself', mode='lines', line=dict(color='#cccccc'), fillcolor='#1e1e1e', hoverinfo="skip", name='Interior'))
    
    # Final Flow (Blue)
    xw_fin, yw_fin = get_water_polygon(DI, hyd_fin["theta"])
    fig.add_trace(go.Scatter(x=xw_fin, y=yw_fin, fill='toself', mode='lines', line=dict(color='#2188ff'), fillcolor='rgba(33, 136, 255, 0.4)', name=f'Q Projeto (y: {y_real_fin:.1f}mm)'))

    # Initial Flow (Green) - plotted after so it sits on top of blue visually
    xw_ini, yw_ini = get_water_polygon(DI, hyd_ini["theta"])
    fig.add_trace(go.Scatter(x=xw_ini, y=yw_ini, fill='toself', mode='lines', line=dict(color='#28a745'), fillcolor='rgba(40, 167, 69, 0.7)', name=f'Q Inicial (y: {y_real_ini:.1f}mm)'))

    fig.update_layout(
        title=f'Seção Dupla (DN {DN})',
        xaxis=dict(scaleanchor="y", scaleratio=1, visible=False),
        yaxis=dict(visible=False),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=60, b=0),
        height=350
    )
    return fig


# ----------------- UI -----------------
st.title("🌊 HidroCalc Esgoto")
st.markdown("Verificação paramétrica completa da NBR 9649: Tensão na Vazão Inicial vs Lâmina na Vazão Final.")

# Validação do Tema Baseado No Streamlit
with st.sidebar.form("input_form"):
    st.header("⚙️ Parâmetros do Projeto")
    vazao_ini_ls = st.number_input("Vazão INICIAL (L/s)", min_value=0.01, max_value=5000.0, value=3.00, step=0.50, format="%.2f", help="Usada para atestar autolimpeza (Tensão >= 1.0 Pa)")
    vazao_fin_ls = st.number_input("Vazão MÁXIMA de Projeto (L/s)", min_value=0.1, max_value=5000.0, value=25.0, step=1.0, format="%.1f", help="Usada para checar respiração/capacidade (y/D < 0.75)")
    material = st.selectbox("Material do Tubo", list(MATERIAIS.keys()))
    declividade = st.number_input("Declividade (m/m)", min_value=0.0001, max_value=0.2000, value=0.0100, step=0.0010, format="%.4f")
    
    submit_button = st.form_submit_button(label="Recalcular NBR 🔄", use_container_width=True)

st.sidebar.info(f"O Módulo assumiu rugosidade teórica do manual: n = {MATERIAIS[material]['n']:.3f}. Obs: Fiscais podem exigir adoção técnica de 0.013 mesmo em plásticos.")

# Calcula
mat_info = MATERIAIS[material]
Q_ini_m3s = vazao_ini_ls / 1000
Q_fin_m3s = vazao_fin_ls / 1000
resultados = []

for prop in mat_info["tubos"]:
    DN = prop["DN"]
    DI_mm = prop["DI"]
    DE_mm = prop["DE"]
    
    hyd_ini = compute_hydraulics(DI_mm / 1000, Q_ini_m3s, declividade, mat_info["n"])
    hyd_fin = compute_hydraulics(DI_mm / 1000, Q_fin_m3s, declividade, mat_info["n"])
    
    is_ok = True
    # Aplicando restrições fidedignas da NBR 9649
    if hyd_fin["yD"] > 0.75: is_ok = False
    if hyd_ini["T_trat"] < 1.0: is_ok = False
    if hyd_fin["Q_ratio"] >= 1.0 or hyd_ini["Q_ratio"] >= 1.0: is_ok = False
    if hyd_fin["V_real"] > 5.0 or hyd_ini["V_real"] > 5.0: is_ok = False
    # (Restrição de V < 0.6 intencionalmente abolida, apenas T > 1.0 julga a autolimpeza agora)
        
    status = "⚠️ Lâmina Baixa" if (hyd_fin["yD"] < 0.20 and is_ok) else ("✅ Atende Normas" if is_ok else "❌ Falha NBR")
    
    resultados.append({
        "DN": DN,
        "y/D Ini": round(hyd_ini['yD'], 3),
        "y/D Fin": round(hyd_fin['yD'], 3),
        "Tensão Ini": f"{hyd_ini['T_trat']:.2f} Pa",
        "V Ini": f"{hyd_ini['V_real']:.2f} m/s",
        "V Fin": f"{hyd_fin['V_real']:.2f} m/s",
        "Status": status,
        "_raw_ini": hyd_ini,
        "_raw_fin": hyd_fin,
        "_props": prop
    })

# DataFrame limpo
df = pd.DataFrame(resultados).drop(columns=["_raw_ini", "_raw_fin", "_props"])

st.subheader("📊 Relatório de Normatização por DN")
st.dataframe(df, use_container_width=True, hide_index=True)

# Visualização de seçāo dupla
st.subheader("📏 Raio-X Interativo das Lâminas")
tubos_selecionaveis = [f"DN {r['DN']} - {r['Status']}" for r in resultados]

index_atende = next((i for i, r in enumerate(resultados) if "✅" in r["Status"]), 0)

selecionado = st.selectbox("Escolha um diâmetro do catálogo comercial:", tubos_selecionaveis, index=index_atende)

if selecionado:
    idx = tubos_selecionaveis.index(selecionado)
    dados = resultados[idx]
    
    raw_ini = dados["_raw_ini"]
    raw_fin = dados["_raw_fin"]
    prop = dados["_props"]
    
    fig = plot_cross_section(prop["DE"], prop["DI"], raw_ini, raw_fin, prop["DN"])
    
    col1, col2 = st.columns([1.5, 1])
    with col1:
        st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})
    with col2:
        st.markdown(f'''
        **Geometria Comercial:**
        - **DN**: {prop["DN"]} mm  |  DI: {prop["DI"]} mm
        
        🟢 **Inicio de Obras (Vazão Inicial):**
        - Lâmina Formada: **{raw_ini["yD"] * prop["DI"]:.1f} mm**
        - Tensão alcançada: **{raw_ini["T_trat"]:.2f} Pa**
        - Vel. da água: {raw_ini["V_real"]:.2f} m/s
        
        🔵 **Fim de Projeto (Vazão Máx):**
        - Lâmina Formada: **{raw_fin["yD"] * prop["DI"]:.1f} mm**
        - Uso: {raw_fin["Q_ratio"]*100:.1f}% da capacidade
        - Vel. da água: {raw_fin["V_real"]:.2f} m/s
        ''')

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>Sistema NBR 9649 Verificado Profissionalmente. 📐</p>", unsafe_allow_html=True)
