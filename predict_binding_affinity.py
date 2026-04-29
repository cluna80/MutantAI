import rdkit
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors
from rdkit.Chem.Pharm2D import Generate, FPFuncs
from sklearn.ensemble import RandomForestRegressor
import joblib

# Load the pre-trained model
model = joblib.load('egfr_binding_model.pkl')

# Define a function to predict binding affinity
def predict_affinity(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return 'Invalid SMILES'
    fp = Generate.Gen2DFingerprint(mol, FPFuncs)
    prediction = model.predict([fp])[0]
    return prediction

# Example usage
smiles = 'CCOc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCC'
prediction = predict_affinity(smiles)
print(f'Predicted binding affinity for {smiles}: {prediction}')
