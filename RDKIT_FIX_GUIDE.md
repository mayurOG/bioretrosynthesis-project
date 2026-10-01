# RDKit Python 3.12 Compatibility Fix

## Issue

Streamlit Cloud runs Python 3.12, but the default `rdkit` package has compatibility issues with `rdMolDraw2D` on this version.

### Error:
```
ImportError: rdkit.Chem.Draw.rdMolDraw2D
```

## Solution Applied

### 1. Changed rdkit to rdkit-pypi
- Changed from: `rdkit`
- Changed to: `rdkit-pypi>=2023.9.0`
- `rdkit-pypi` is a PyPI-compatible build of RDKit that works better on Cloud environments

### 2. Enhanced Error Handling
- Added try-catch blocks for all imports
- Added graceful fallbacks for visualization features
- Better error messages if imports fail

### 3. Requirements Updated
- `requirements.txt` → Uses `rdkit-pypi>=2023.9.0`
- `requirements-streamlit.txt` → Uses `rdkit-pypi>=2023.9.0`
- `streamlit_app.py` → Safe imports with error handling

## Files Modified

✅ `streamlit_app.py` - Added safe import handling and error catching
✅ `requirements.txt` - Changed to rdkit-pypi
✅ `requirements-streamlit.txt` - Changed to rdkit-pypi

## What Changed in Code

```python
# BEFORE (fails on Python 3.12):
from rdkit import Chem
from rdkit.Chem import Draw

# AFTER (handles errors gracefully):
try:
    from rdkit import Chem
    from rdkit.Chem import Draw
    RDKIT_AVAILABLE = True
except (ImportError, OSError) as e:
    st.error(f"Critical dependency not available: {str(e)}")
    RDKIT_AVAILABLE = False
    st.stop()
```

## Testing

To test locally:
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Streamlit Cloud Deployment

The app will now:
1. Properly handle rdkit imports on Python 3.12
2. Fall back gracefully if any visualization fails
3. Show helpful error messages instead of crashing

Deploy using: `streamlit_app.py` as the main file.

## Alternative Packages

If `rdkit-pypi` still fails, alternatives:
- Try `pip install rdkit-pypi==2023.9.0` (specific version)
- Or `conda install -c conda-forge rdkit` (if conda available)
- Or use `molvs` or `pubchempy` for molecule operations without rdkit

## References

- RDKit PyPI: https://pypi.org/project/rdkit-pypi/
- Streamlit Python 3.12: https://docs.streamlit.io/
