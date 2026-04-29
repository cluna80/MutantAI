import rdkit
from rdkit import Chem
from rdkit.Chem import Descriptors, AllChem

# Define the SMILES string for EGFR inhibitor
smiles = 'CCOc1cc2ncnc'

# Convert SMILES to molecule object
mol = Chem.MolFromSmiles(smiles)

# Calculate molecular weight
mw = Descriptors.MolWt(mol)
print(f'Molecular Weight: {mw:.2f}')

# Calculate logP
logp = Descriptors.MolLogP(mol)
print(f'LogP: {logp:.2f}')

# Calculate TPSA (Topological Polar Surface Area)
tpsa = Descriptors.TPSA(mol)
print(f'TPSA: {tpsa:.2f}')

if __name__ == '__main__':
    print('SMILES analysis complete.')
