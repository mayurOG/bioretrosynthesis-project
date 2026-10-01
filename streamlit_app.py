import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
from rdkit import Chem
from rdkit.Chem import Draw
import graphviz
import logging
from typing import Optional

# Advanced modules
from chemistry_utils import StructureProcessor, ChemistryValidator
from net_model_utils import load_model, smiles_to_image_base64
from tbr_opt import RetroEngine, BuildingBlockIndex
from reaction_rules import ReactionRuleDatabase, ReactionFeasibilityScorer, GreenChemistryFilter

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_PATH = "final_model"
BUILDING_BLOCKS_PATH = "bio_building_block.csv"

# ============================================================================
# SESSION STATE & INITIALIZATION
# ============================================================================

@st.cache_resource
def init_models():
    """Initialize all models and utilities."""
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
    }

# Initialize
resources = init_models()
model_bundle = resources["bundle"]
building_blocks_index = resources["blocks"]
engine = resources["engine"]
structure_processor = resources["processor"]
chemistry_validator = resources["validator"]
reaction_rules = resources["rule_db"]

# ============================================================================
# UI COMPONENTS
# ============================================================================

st.set_page_config(page_title="🔬 Advanced BioRetrosynthesis", layout="wide")

st.title("🔬 Advanced BioRetrosynthesis Predictor")
st.write("""
Advanced retrosynthesis prediction supporting **multiple input formats**, 
**multi-model consensus**, **reaction validation**, and **green chemistry scoring**.
""")

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
        help="Masks logits for syntactically valid SMILES only (~14% slower)",
    )
    num_beams = st.slider("Beam width", 1, 10, 3, help="Predictions per level")
    batch_size = st.slider("Batch size", 1, 32, 16, help="Molecules per generate() call")
    use_cache = st.toggle("Cache predictions", value=True)
    
    # Search settings
    st.subheader("Search Settings")
    max_depth = st.slider("Max recursion depth", 1, 10, 5)
    
    # Validation & filtering
    st.subheader("Validation & Filtering")
    validate_lipinski = st.checkbox("Lipinski's Rule of Five check", value=True)
    green_chemistry = st.checkbox("Green chemistry scoring", value=True)
    require_high_confidence = st.checkbox("Require high confidence", value=False)
    confidence_threshold = st.slider(
        "Confidence threshold",
        0.0, 1.0, 0.6,
        disabled=not require_high_confidence,
        help="Filter predictions below this confidence"
    )
    
    # Cache management
    st.subheader("Cache Management")
    if st.button("🗑️ Clear prediction cache", use_container_width=True):
        engine.cache.clear()
        st.toast("✓ Cache cleared")

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

def render_molecule(smiles, caption):
    """Render molecule image or SMILES code."""
    img = smiles_to_image_base64(smiles)
    if img:
        st.image(img, caption=caption, width=200)
    else:
        st.code(smiles, language=None)
        st.caption(f"{caption} (not renderable)")


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
        lipinski_result = chemistry_validator.check_lipinski_compliance(
            Chem.MolFromSmiles(structure.smiles)
        )
        if lipinski_result["violations"]:
            st.warning(f"⚠️ Lipinski violations: {', '.join(lipinski_result['violations'])}")
        else:
            st.success("✓ Complies with Lipinski's Rule of Five")


# ============================================================================
# PREDICTION & ANALYSIS
# ============================================================================

if st.button("🚀 Predict Retrosynthesis", type="primary", use_container_width=True):
    if not user_input.strip():
        st.warning("Please enter a molecule (SMILES, name, formula, etc.)")
    else:
        # Step 1: Process input
        with st.spinner("🔄 Processing input..."):
            structure = structure_processor.process_input(user_input.strip())
        
        if not structure.validity:
            st.error(f"❌ {structure.error_message}")
            st.stop()
        
        # Show input analysis
        st.subheader("📊 Input Molecule Analysis")
        show_chemical_properties(structure)
        
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
        stats_dict = stats.as_dict()
        col1.metric("generate() calls", stats_dict["generate_calls"])
        col2.metric("Molecules scored", stats_dict["molecules_scored"])
        col3.metric("Avg batch size", stats_dict["avg_batch_size"])
        col4.metric("Wall time (s)", stats_dict["wall_seconds"])
        
        # Step 3: Analyze reactions
        st.subheader("🧪 Retrosynthesis Steps")
        
        for i, step in enumerate(pathway, 1):
            with st.expander(f"Step {i}: {step['product']}", expanded=(i==1)):
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    render_molecule(step['product'], f"Product")
                
                with col2:
                    st.write(f"**Product SMILES:** `{step['product']}`")
                    st.write(f"**Depth:** {step['depth']}")
                    
                    # Show reactants
                    st.write("**Reactants:**")
                    for j, reactant in enumerate(step['reactants'], 1):
                        col_r1, col_r2 = st.columns([1, 3])
                        with col_r1:
                            render_molecule(reactant, f"R{j}")
                        with col_r2:
                            st.code(reactant)
                    
                    # Reaction analysis
                    if step['reactants']:
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
                            st.metric("Feasibility Score", f"{feasibility_score:.2f}", delta=f"{(feasibility_score-0.7)*100:+.0f}%")
                        with col_a2:
                            st.metric("Green Chemistry Score", f"{green_score:.2f}")
                        
                        if factors:
                            st.caption(f"Factors: {', '.join(factors.values())}")
        
        # Step 4: Visualize pathway
        st.subheader("🧬 Retrosynthesis Tree Visualization")
        
        dot = graphviz.Digraph()
        dot.attr(rankdir='TB', size='10,8')
        dot.attr('node', shape='box', style='rounded,filled', fillcolor='lightblue')
        
        added = set()
        for step in pathway:
            product = step["product"][:30] + "..." if len(step["product"]) > 30 else step["product"]
            
            if product not in added:
                dot.node(product, product, shape='box')
                added.add(product)
            
            for reactant in step["reactants"]:
                reactant_label = reactant[:30] + "..." if len(reactant) > 30 else reactant
                if reactant_label not in added:
                    dot.node(reactant_label, reactant_label, shape='ellipse', fillcolor='lightgreen')
                    added.add(reactant_label)
                dot.edge(product, reactant_label)
        
        st.graphviz_chart(dot)
        
        # Step 5: Summary diagnostics
        with st.expander("📋 Full Diagnostics & Pathway Data"):
            st.json(stats_dict)
            
            st.subheader("Pathway JSON")
            pathway_df = pd.DataFrame([
                {
                    "Step": i,
                    "Product": step["product"],
                    "Reactants": " + ".join(step["reactants"]),
                    "Depth": step["depth"]
                }
                for i, step in enumerate(pathway, 1)
            ])
            st.dataframe(pathway_df, use_container_width=True)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.caption("Model: QLoRA-fine-tuned ReactionT5v2  •  Data: KEGG/MetaCyc/USPTO-NPL  •  UI: Streamlit")
st.caption("Developed and Maintained by Mayur Nhavalde")
st.caption("Based on original work by Suyash Utekar  •  Source: https://github.com/SuyashUtekar/TransBioRetro")
st.caption(
    "**Advanced features:** Multi-format input parsing (SMILES/InChI/Name/CAS/Formula), "
    "Lipinski compliance checking, reaction rule validation, green chemistry scoring, "
    "advanced retrosynthesis engine with batched search and canonical caching."
)
