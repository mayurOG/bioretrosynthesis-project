"""BioRetrosynthesis Streamlit App - Streamlit Cloud Compatible (No X11)"""
import streamlit as st
import pandas as pd
import logging
from typing import Optional
import sys
import os

# Suppress warnings and disable X11 for rdkit
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['RDKIT_NOTHREADS'] = '1'

import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="🔬 Advanced BioRetrosynthesis", layout="wide")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# SAFE IMPORTS WITH GRACEFUL DEGRADATION
# ============================================================================

# Import basic dependencies
try:
    import networkx as nx
    import graphviz
except ImportError as e:
    st.error(f"Missing visualization dependencies: {e}")
    st.stop()

# Try rdkit - handle gracefully if graphics libs missing
RDKIT_AVAILABLE = False
try:
    # Set environment before importing to avoid X11 issues
    os.environ['RDKIT_NOTHREADS'] = '1'
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors
    
    # Try importing Draw - may fail due to X11
    try:
        from rdkit.Chem import Draw
        RDKIT_DRAW_AVAILABLE = True
    except Exception as e:
        logger.warning(f"RDKit Draw unavailable (X11): {e}")
        RDKIT_DRAW_AVAILABLE = False
        # Stub out Draw functions
        class Draw:
            @staticmethod
            def MolToImage(*args, **kwargs):
                return None
    
    RDKIT_AVAILABLE = True
except ImportError as e:
    st.error(f"⚠️ Critical: RDKit not available: {e}")
    st.stop()

# Optional imports
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# Custom modules - import with error handling
MODULES_AVAILABLE = True
try:
    from chemistry_utils import StructureProcessor, ChemistryValidator
    from net_model_utils import load_model, smiles_to_image_base64
    from tbr_opt import RetroEngine, BuildingBlockIndex
    from reaction_rules import ReactionRuleDatabase, ReactionFeasibilityScorer, GreenChemistryFilter
except ImportError as e:
    st.error(f"Failed to load custom modules: {e}")
    logger.exception("Module import failed")
    MODULES_AVAILABLE = False

if not MODULES_AVAILABLE:
    st.stop()

MODEL_PATH = "final_model"
BUILDING_BLOCKS_PATH = "bio_building_block.csv"

# ============================================================================
# SESSION STATE & INITIALIZATION
# ============================================================================

@st.cache_resource
def init_models():
    """Initialize all models and utilities."""
    try:
        with st.spinner("Loading models (this may take 1-2 minutes on first load)..."):
            bundle = load_model(MODEL_PATH)
            blocks = BuildingBlockIndex.from_csv(BUILDING_BLOCKS_PATH)
            engine = RetroEngine(
                bundle["model"],
                bundle["tokenizer"],
                blocks,
                num_beams=3,
                constrained=True,
                batch_size=16,
            )
            
            processor = StructureProcessor()
            validator = ChemistryValidator()
            rule_db = ReactionRuleDatabase()
            
            return {
                "bundle": bundle,
                "blocks": blocks,
                "engine": engine,
                "processor": processor,
                "validator": validator,
                "rule_db": rule_db,
                "loaded": True
            }
    except Exception as e:
        st.error(f"Failed to initialize models: {str(e)}")
        logger.exception("Model initialization error")
        return {"loaded": False, "error": str(e)}

# Initialize models
resources = init_models()

if not resources.get("loaded"):
    st.error(f"Cannot proceed without models: {resources.get('error', 'Unknown error')}")
    st.stop()

model_bundle = resources["bundle"]
building_blocks_index = resources["blocks"]
engine = resources["engine"]
structure_processor = resources["processor"]
chemistry_validator = resources["validator"]
reaction_rules = resources["rule_db"]

# ============================================================================
# UI COMPONENTS
# ============================================================================

st.title("🔬 Advanced BioRetrosynthesis Predictor")
st.write("""
Advanced retrosynthesis prediction supporting **multiple input formats**, 
**reaction validation**, and **green chemistry scoring**.
""")

if not RDKIT_DRAW_AVAILABLE:
    st.info("ℹ️ Running in text-only mode (molecule visualization unavailable)")

# ============================================================================
# SIDEBAR CONFIGURATION
# ============================================================================

with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Input format section
    st.subheader("Input Format")
    st.caption("Supports: SMILES, InChI, Chemical Names, CAS #, Molecular Formula")
    
    # Model settings
    st.subheader("Model Settings")
    constrained = st.toggle(
        "Grammar-constrained decoding",
        value=True,
        help="Masks logits for syntactically valid SMILES only",
    )
    num_beams = st.slider("Beam width", 1, 10, 3, help="Predictions per level")
    batch_size = st.slider("Batch size", 1, 32, 16, help="Molecules per generate() call")
    use_cache = st.toggle("Cache predictions", value=True)
    
    # Search settings
    st.subheader("Search Settings")
    max_depth_sidebar = st.slider("Max recursion depth", 1, 10, 5)
    
    # Validation & filtering
    st.subheader("Validation & Filtering")
    validate_lipinski = st.checkbox("Lipinski's Rule of Five check", value=True)
    green_chemistry = st.checkbox("Green chemistry scoring", value=True)
    
    # Cache management
    st.subheader("Cache Management")
    if st.button("🗑️ Clear prediction cache", use_container_width=True):
        try:
            engine.cache.clear()
            st.toast("✓ Cache cleared")
        except Exception as e:
            st.warning(f"Could not clear cache: {e}")

# ============================================================================
# MAIN INPUT SECTION
# ============================================================================

col1, col2 = st.columns([3, 1])

with col1:
    user_input = st.text_input(
        "Enter target molecule",
        placeholder="SMILES (CC(=O)O) | InChI | Name (acetic acid) | Formula (C2H4O2) | CAS (64-19-7)",
        key="molecule_input"
    )

with col2:
    max_depth = st.number_input("Max depth", 1, 10, 5)

# ============================================================================
# INPUT PROCESSING & VALIDATION
# ============================================================================

def show_chemical_properties(structure):
    """Display detailed chemical properties."""
    if not structure.validity:
        st.error(f"❌ Invalid: {structure.error_message}")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Molecular Weight", f"{structure.molecular_weight:.2f}" if structure.molecular_weight else "—")
    with col2:
        st.metric("LogP", f"{structure.logp:.2f}" if structure.logp else "—")
    with col3:
        st.metric("H-Bond Donors", structure.hbd if structure.hbd is not None else "—")
    with col4:
        st.metric("H-Bond Acceptors", structure.hba if structure.hba is not None else "—")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Rotatable Bonds", structure.rotatable_bonds if structure.rotatable_bonds is not None else "—")
    with col2:
        st.metric("Aromatic Rings", structure.aromatic_rings if structure.aromatic_rings is not None else "—")
    with col3:
        st.metric("Molecular Formula", structure.molecular_formula if structure.molecular_formula else "—")
    with col4:
        st.metric("Source", structure.source)
    
    # Lipinski compliance
    if validate_lipinski and structure.validity:
        try:
            lipinski_result = chemistry_validator.check_lipinski_compliance(
                Chem.MolFromSmiles(structure.smiles)
            )
            if lipinski_result["violations"]:
                st.warning(f"⚠️ Lipinski violations: {', '.join(lipinski_result['violations'])}")
            else:
                st.success("✓ Complies with Lipinski's Rule of Five")
        except Exception as e:
            st.caption(f"Could not check Lipinski compliance")


# ============================================================================
# PREDICTION & ANALYSIS
# ============================================================================

if st.button("🚀 Predict Retrosynthesis", type="primary", use_container_width=True):
    if not user_input.strip():
        st.warning("Please enter a molecule (SMILES, name, formula, etc.)")
    else:
        try:
            # Step 1: Process input
            with st.spinner("🔄 Processing input..."):
                structure = structure_processor.process_input(user_input.strip())
            
            if not structure.validity:
                st.error(f"❌ {structure.error_message}")
                st.stop()
            
            # Show input analysis
            st.subheader("📊 Input Molecule Analysis")
            show_chemical_properties(structure)
            
            st.write(f"**Input SMILES:** `{structure.smiles}`")
            
            # Step 2: Run prediction
            with st.spinner("⏳ Running multi-step retrosynthesis (this may take a minute)..."):
                engine.constrained = constrained
                engine.num_beams = num_beams
                engine.batch_size = batch_size
                
                pathway, stats = engine.predict(
                    structure.smiles,
                    max_depth=max_depth,
                    use_cache=use_cache,
                )
            
            if not pathway:
                st.error("❌ No valid retrosynthesis pathway found")
                st.stop()
            
            st.success("✅ Prediction complete!")
            
            # Show statistics
            col1, col2, col3, col4 = st.columns(4)
            try:
                stats_dict = stats.as_dict()
            except:
                stats_dict = {}
            
            col1.metric("Steps found", len(pathway))
            col2.metric("Molecules scored", stats_dict.get("molecules_scored", "—"))
            col3.metric("Avg batch size", stats_dict.get("avg_batch_size", "—"))
            col4.metric("Time (s)", stats_dict.get("wall_seconds", "—"))
            
            # Step 3: Analyze reactions
            st.subheader("🧪 Retrosynthesis Steps")
            
            for i, step in enumerate(pathway, 1):
                with st.expander(f"Step {i}: {step['product'][:50]}...", expanded=(i==1)):
                    st.write(f"**Product SMILES:** `{step['product']}`")
                    st.write(f"**Depth:** {step['depth']}")
                    
                    # Show reactants
                    st.write("**Reactants:**")
                    for j, reactant in enumerate(step['reactants'], 1):
                        st.code(reactant, language="text")
                    
                    # Reaction analysis
                    if step['reactants']:
                        try:
                            feasibility_score, factors = ReactionFeasibilityScorer.score_reaction(
                                step['reactants'],
                                step['product']
                            )
                            
                            green_score = GreenChemistryFilter.score_green_chemistry(
                                step['reactants'],
                                step['product']
                            )
                            
                            col_a1, col_a2 = st.columns(2)
                            with col_a1:
                                st.metric("Feasibility Score", f"{feasibility_score:.2f}")
                            with col_a2:
                                st.metric("Green Chemistry Score", f"{green_score:.2f}")
                        except Exception as e:
                            st.caption("Reaction analysis unavailable")
            
            # Step 4: Visualize pathway (text-based)
            st.subheader("🧬 Retrosynthesis Pathway")
            
            pathway_text = "Target Product\n"
            for i, step in enumerate(pathway, 1):
                pathway_text += f"    ↓ (Step {i})\n"
                for reactant in step['reactants']:
                    pathway_text += f"{reactant}\n"
            
            st.code(pathway_text, language="text")
            
            # Step 5: Summary diagnostics
            with st.expander("📋 Full Diagnostics & Pathway Data"):
                try:
                    if stats_dict:
                        st.json(stats_dict)
                    
                    st.subheader("Pathway Summary")
                    pathway_df = pd.DataFrame([
                        {
                            "Step": i,
                            "Product": step["product"][:50],
                            "Reactants": " + ".join([r[:30] for r in step["reactants"]]),
                            "Depth": step["depth"]
                        }
                        for i, step in enumerate(pathway, 1)
                    ])
                    st.dataframe(pathway_df, use_container_width=True)
                except Exception as e:
                    st.caption("Could not display diagnostics")
        
        except Exception as e:
            st.error(f"Prediction failed: {str(e)}")
            logger.exception("Prediction error")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.caption("Model: QLoRA-fine-tuned ReactionT5v2 | Data: KEGG/MetaCyc/USPTO-NPL | UI: Streamlit")
st.caption("Developed by Mayur Nhavalde")
