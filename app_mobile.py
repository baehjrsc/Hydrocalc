import streamlit as st
import math
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# ----------------- CONFIG & DATA -----------------
st.set_page_config(page_title="HidroCalc Mobile", page_icon="🌊", layout="centered")

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
def plot_cross_section(DE, DI, yD, theta, DN):
    y_real = yD * DI
    
    t = np.linspace(0, 2*np.pi, 200)
    xo = DE/2 * np.cos(t)
    yo = DE/2 * np.sin(t)
    
    xi = DI/2 * np.cos(t)
    yi = DI/2 * np.sin(t)
    
    start_angle = -np.pi/2 - theta/2
    end_angle = -np.pi/2 + theta/2
    tw = np.linspace(start_angle, end_angle, 100)
    
    xw = DI/2 * np.cos(tw)
    yw = DI/2 * np.sin(tw)
    
    xw_poly = np.append(xw, xw[0])
    yw_poly = np.append(yw, yw[0])

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=xo, y=yo, fill='toself', mode='lines', line=dict(color='#7a7a7a'), fillcolor='#444444', hoverinfo="skip", name='Parede Externa'))
    fig.add_trace(go.Scatter(x=xi, y=yi, fill='toself', mode='lines', line=dict(color='#cccccc'), fillcolor='#1e1e1e', hoverinfo="skip", name='Interior'))
    fig.add_trace(go.Scatter(x=xw_poly, y=yw_poly, fill='toself', mode='lines', line=dict(color='#00b4d8'), fillcolor='rgba(0,180,216,0.6)', name=f'Lâmina: {y_real:.1f}mm'))

    fig.update_layout(
        title=f'Seção Transversal (DN {DN})',
        xaxis=dict(scaleanchor="y", scaleratio=1, visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=30, b=0),
        height=300
    )
    return fig


# ----------------- UI -----------------
st.title("🌊 HidroCalc Condutos")
st.markdown("Cálculo e verificação da **NBR 9649** otimizado para celulares (Android/iOS) direto no navegador.")

# Validação do Tema Baseado No Streamlit
# Entradas em duas colunas ou barra lateral (sidebar sumido no mobile vira um menu hambúrguer)
with st.sidebar.form("input_form"):
    st.header("⚙️ Parâmetros do Projeto")
    vazao_ls = st.number_input("Vazão de Projeto (L/s)", min_value=0.1, max_value=5000.0, value=25.0, step=1.0)
    material = st.selectbox("Material do Tubo", list(MATERIAIS.keys()))
    declividade = st.number_input("Declividade (m/m)", min_value=0.0001, max_value=0.2, value=0.0100, step=0.001)
    
    # Botão de recalcular (muito útil no celular para não travar enquanto digita)
    submit_button = st.form_submit_button(label="Recalcular 🔄", use_container_width=True)

st.sidebar.info(f"O Módulo calculou: Manning (n) = {MATERIAIS[material]['n']:.3f}. Feche o menu lateral no celular para ver os resultados.")

# Calcula
mat_info = MATERIAIS[material]
Q_m3s = vazao_ls / 1000
resultados = []

for prop in mat_info["tubos"]:
    DN = prop["DN"]
    DI_mm = prop["DI"]
    DE_mm = prop["DE"]
    
    hyd = compute_hydraulics(DI_mm / 1000, Q_m3s, declividade, mat_info["n"])
    
    is_ok = True
    if hyd["yD"] > 0.75 or hyd["V_real"] < 0.60 or hyd["V_real"] > 5.0 or hyd["T_trat"] < 1.0 or hyd["Q_ratio"] >= 1.0:
        is_ok = False
        
    status = "⚠️ Atenção (y/D)" if (hyd["yD"] < 0.20 and is_ok) else ("✅ Atende" if is_ok else "❌ Falha")
    
    resultados.append({
        "DN": DN,
        "y/D": round(hyd['yD'], 3),
        "V (m/s)": f"{hyd['V_real']:.2f}",
        "Tensão (Pa)": f"{hyd['T_trat']:.2f}",
        "Engolimento": f"{hyd['Q_ratio']*100:.1f}%",
        "Status": status,
        "_raw": hyd,
        "_props": prop
    })

# DataFrame limpo
df = pd.DataFrame(resultados).drop(columns=["_raw", "_props"])

st.subheader("📊 Resultados por Diâmetro Comercial")
st.dataframe(df, use_container_width=True, hide_index=True)

# Visualização de seçāo
st.subheader("📏 Inspeção Visual Interativa")
tubos_selecionaveis = [f"DN {r['DN']} - {r['Status']}" for r in resultados]

# Pegar o primeiro que "Atende" logo de cara
index_atende = next((i for i, r in enumerate(resultados) if "✅" in r["Status"]), 0)

selecionado = st.selectbox("Escolha um tubo para visualizar interativamente:", tubos_selecionaveis, index=index_atende)

if selecionado:
    idx = tubos_selecionaveis.index(selecionado)
    dados = resultados[idx]
    
    raw = dados["_raw"]
    prop = dados["_props"]
    
    fig = plot_cross_section(prop["DE"], prop["DI"], raw["yD"], raw["theta"], prop["DN"])
    
    # Criamos duas colunas flexíveis
    col1, col2 = st.columns([1.5, 1])
    with col1:
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown(f'''
        **Detalhes Geométricos:**
        - **DN**: {prop["DN"]} mm
        - **DE**: {prop["DE"]} mm
        - **DI**: {prop["DI"]} mm
        
        **Detalhes Hidráulicos:**
        - **Lâmina d'água:** {raw["yD"] * prop["DI"]:.1f} mm
        - **Capacidade Ocupada:** {raw["Q_ratio"]*100:.1f}%
        - **V Real:** {raw["V_real"]:.2f} m/s
        - **Força Trativa:** {raw["T_trat"]:.2f} Pa
        ''')

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>Criado estrategicamente para uso móvel inteligente via Web. 🌐📱</p>", unsafe_allow_html=True)
