# Streamlit Cloud Deployment Guide

## Issues Fixed

1. **Pandas version incompatibility**: Changed from `pandas==3.0.5` (doesn't exist) to `pandas>=1.5.0,<3.0`
2. **NumPy version conflicts**: Changed from `numpy==2.5.3` to `numpy>=1.20.0` for compatibility
3. **Missing dependencies**: Added `torch`, `transformers`, `peft` to requirements.txt
4. **Entry point**: Created `streamlit_app.py` as the main entry point for Streamlit Cloud

## Deployment Steps

### Option 1: Deploy to Streamlit Cloud

1. Push your code to GitHub:
   ```bash
   git add .
   git commit -m "Fix Streamlit deployment issues"
   git push origin main
   ```

2. Go to [Streamlit Cloud](https://streamlit.io/cloud)

3. Click "New app" and select:
   - Repository: `mayurOG/bioretrosynthesis-project`
   - Branch: `main`
   - Main file path: `streamlit_app.py`

4. Click "Deploy"

### Option 2: Deploy Locally (for testing)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run streamlit_app.py
```

## Files Modified

- `requirements.txt` - Fixed version constraints
- `requirements-streamlit.txt` - Fixed version constraints and added missing dependencies
- `.streamlit/config.toml` - Enhanced configuration for Cloud deployment
- `.streamlit/secrets.toml` - Created for secrets management (if needed)
- `streamlit_app.py` - Created as primary entry point

## Key Changes

### requirements.txt
- ✅ Fixed pandas version (was 3.0.5, now >=1.5.0,<3.0)
- ✅ Fixed numpy version (was 2.5.3, now >=1.20.0)
- ✅ Added torch, transformers, peft
- ✅ Added all UI dependencies (networkx, plotly, graphviz)

### Config Enhancements
- Enhanced theme configuration
- Added proper logging
- Configured toolbar mode for minimal UI clutter
- Error details enabled for debugging

## Troubleshooting

### If model loading fails on Cloud:
- Ensure `final_model/` directory is committed to git
- Check that `bio_building_block.csv` is present
- Verify file paths are relative, not absolute

### If dependencies won't install:
- Check Streamlit Cloud logs for specific package errors
- Consider removing/mocking GPU-heavy operations for initial deployment
- Use `--no-cache-dir` for pip (Streamlit Cloud does this automatically)

### Memory Issues:
- Model loading requires ~8GB RAM
- Streamlit Cloud default is 1GB
- Consider model quantization or lazy loading if available

## Notes

- The app requires model files (`final_model/`) and CSV data (`bio_building_block.csv`)
- GPU acceleration requires specific Streamlit Cloud tier
- Consider adding early stopping/timeouts for long-running predictions
- Monitor execution time - Cloud deployments have time limits

## Next Steps

1. Ensure all required files (model, CSV) are in the repo
2. Test locally first: `streamlit run streamlit_app.py`
3. Deploy to Streamlit Cloud
4. Monitor logs for any runtime errors
