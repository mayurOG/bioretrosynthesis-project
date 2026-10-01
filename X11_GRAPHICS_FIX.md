# RDKit X11 Graphics Library Fix

## Issue

RDKit's molecule drawing functions require X11 graphics libraries (libXrender.so.1) which are not available in Streamlit Cloud's containerized environment.

### Error:
```
libXrender.so.1: cannot open shared object file: No such file or directory
Failed to load custom modules: libXrender.so.1: cannot open shared object file
```

## Root Cause

RDKit's `Draw` module uses Pillow/Cairo which depend on X11 for rendering. Streamlit Cloud runs in a headless container without graphics libraries.

## Solution Implemented

### 1. Environment Variables (Disable X11)
```python
os.environ['QT_QPA_PLATFORM'] = 'offscreen'  # Disable GUI platform
os.environ['RDKIT_NOTHREADS'] = '1'          # Disable threading in rdkit
```

### 2. Graceful Degradation
- Try to import rdkit core (Chem module) - this works fine
- Attempt to import rdkit.Chem.Draw separately
- If Draw fails, stub it out with a mock class
- App continues in text-only mode instead of crashing

### 3. UI Changes
- Removed molecule image rendering
- Replaced with SMILES string display
- Use text-based pathway visualization instead of graphviz charts
- Show info message when running in text-only mode

## Code Changes

```python
# BEFORE (crashes on Cloud):
from rdkit.Chem import Draw
img = Draw.MolToImage(mol)
st.image(img)

# AFTER (graceful fallback):
try:
    from rdkit.Chem import Draw
    RDKIT_DRAW_AVAILABLE = True
except Exception as e:
    RDKIT_DRAW_AVAILABLE = False
    # Use SMILES text instead

# At startup:
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
```

## Features Preserved

✅ Molecule structure processing (SMILES, InChI, names)
✅ Retrosynthesis prediction (core ML functionality)
✅ Chemical property calculations
✅ Reaction analysis and scoring
✅ Pathway generation and analysis
✅ Data visualization (as text/tables)

## Features Modified

⚠️ Molecule images → Now shows SMILES strings
⚠️ Graphviz visualization → Now shows text-based pathway
⚠️ RDKit Draw → Gracefully unavailable (non-critical)

## Files Modified

✅ `streamlit_app.py` - Updated with X11 workarounds and text-based fallbacks

## Testing

Local testing (with X11):
```bash
streamlit run streamlit_app.py
```

Expected behavior:
- If RDKit Draw available: shows molecule images
- If RDKit Draw unavailable: shows SMILES text instead
- Both cases: full prediction functionality works

## Why This Works on Streamlit Cloud

1. **Headless environment**: `QT_QPA_PLATFORM=offscreen` tells RDKit not to use GUI
2. **Graceful imports**: Try/except prevents app crash if Draw unavailable
3. **Core functionality**: RDKit's chemistry functions work without graphics
4. **Text-based UI**: All essential data shown as text/tables (no images needed)

## Alternative Solutions (Not Implemented)

- ❌ Installing X11 packages: Cloud environment is read-only
- ❌ Using different graphics backend: Would require source rebuild
- ❌ Pre-generating images: Adds complexity and storage
- ✅ Text-based output: Simple, works, user-friendly

## References

- RDKit Chem module: Works without graphics
- Streamlit Cloud limitations: No X11 graphics libraries
- Qt Platform Abstraction: https://doc.qt.io/qt-6/qpa.html
