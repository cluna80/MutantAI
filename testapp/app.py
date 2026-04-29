import streamlit as st
from rdkit import Chem
from rdkit.Chem import Draw, Descriptors, QED, rdMolDescriptors

st.set_page_config(page_title="TestApp", page_icon="🧬", layout="wide")
st.markdown("<style>html,body,[class*='css']{background:#0a0a0f;color:#e0e0e0}</style>", unsafe_allow_html=True)
st.title("🧬 TestApp")
st.markdown("---")

def mol_to_image(smiles):
    mol = Chem.MolFromSmiles(smiles)
    return Draw.MolToImage(mol, size=(400, 300)) if mol else None

def get_properties(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if not mol: return {}
    return {
        "MW": round(Descriptors.MolWt(mol), 2),
        "LogP": round(Descriptors.MolLogP(mol), 2),
        "HBD": rdMolDescriptors.CalcNumHBD(mol),
        "HBA": rdMolDescriptors.CalcNumHBA(mol),
        "QED": round(QED.qed(mol), 3),
        "TPSA": round(Descriptors.TPSA(mol), 2),
    }

with st.sidebar:
    st.markdown("### 🔬 Input")
    smiles = st.text_input("SMILES", value="CCOc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCC")
    target = st.selectbox("Target", ["EGFR", "HIV Protease", "HIV Integrase", "BACE1", "COVID Mpro"])
    analyze_btn = st.button("⚡ Analyze", use_container_width=True)

col1, col2 = st.columns([1, 1])
with col1:
    st.markdown("### Structure")
    if smiles:
        img = mol_to_image(smiles)
        if img: st.image(img, use_container_width=True)
        else: st.error("Invalid SMILES")
with col2:
    st.markdown("### Properties")
    if smiles:
        for k, v in get_properties(smiles).items():
            st.metric(k, v)

if analyze_btn and smiles:
    props = get_properties(smiles)
    ro5 = props.get("MW",999)<=500 and props.get("LogP",999)<=5
    st.success(f"Lipinski Ro5: {'PASS' if ro5 else 'FAIL'}")
    st.info(f"QED: {props.get('QED','N/A')} ({'Drug-like' if props.get('QED',0)>0.5 else 'Needs work'})")
