import streamlit as st
import pandas as pd
import plotly.express as px
from rdkit import Chem
from rdkit.Chem import Draw, Descriptors, QED, rdMolDescriptors
import io

st.set_page_config(page_title="PhysicsChemV2", page_icon="🧬", layout="wide")

st.markdown("""
<style>
html, body, [class*="css"] { background-color: #0a0a0f; color: #e0e0e0; }
</style>
""", unsafe_allow_html=True)

st.title("🧬 PhysicsChemV2")
st.markdown("---")

def mol_to_image(smiles: str):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Draw.MolToImage(mol, size=(400, 300))

def get_properties(smiles: str) -> dict:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {}
    return {
        "MW": round(Descriptors.MolWt(mol), 2),
        "LogP": round(Descriptors.MolLogP(mol), 2),
        "HBD": rdMolDescriptors.CalcNumHBD(mol),
        "HBA": rdMolDescriptors.CalcNumHBA(mol),
        "QED": round(QED.qed(mol), 3),
        "TPSA": round(Descriptors.TPSA(mol), 2),
        "Rotatable Bonds": rdMolDescriptors.CalcNumRotatableBonds(mol),
    }

with st.sidebar:
    st.markdown("### 🔬 Molecule Input")
    smiles = st.text_input("SMILES", value="CCOc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCC")
    target = st.selectbox("Target", ["EGFR", "HIV Protease", "HIV Integrase", "BACE1", "COVID Mpro"])
    analyze_btn = st.button("⚡ Analyze", use_container_width=True)

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### Molecular Structure")
    if smiles:
        img = mol_to_image(smiles)
        if img:
            st.image(img, use_container_width=True)
        else:
            st.error("Invalid SMILES")

with col2:
    st.markdown("### Molecular Properties")
    if smiles:
        props = get_properties(smiles)
        if props:
            for k, v in props.items():
                st.metric(k, v)

if analyze_btn and smiles:
    st.markdown("---")
    st.markdown("### Analysis Results")
    props = get_properties(smiles)
    ro5 = all([
        props.get("MW", 999) <= 500,
        props.get("LogP", 999) <= 5,
        props.get("HBD", 999) <= 5,
        props.get("HBA", 999) <= 10,
    ])
    st.success(f"✅ Lipinski Ro5: {'PASS' if ro5 else 'FAIL'}")
    st.info(f"QED Score: {props.get('QED', 'N/A')} ({'Drug-like' if props.get('QED', 0) > 0.5 else 'Needs optimization'})")

if __name__ == "__main__":
    pass
