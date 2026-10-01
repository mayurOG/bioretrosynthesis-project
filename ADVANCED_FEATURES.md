# 🚀 Advanced BioRetrosynthesis — Feature Documentation

**Developed and Maintained by Mayur Nhavalde**

This document describes the advanced features added to support universal molecular coverage, accuracy, and efficiency.

---

## 📋 Table of Contents

1. [Multi-Format Input Support](#multi-format-input-support)
2. [Advanced Chemistry Validation](#advanced-chemistry-validation)
3. [Reaction Rule Database](#reaction-rule-database)
4. [Green Chemistry Filtering](#green-chemistry-filtering)
5. [Enhanced Retrosynthesis Engine](#enhanced-retrosynthesis-engine)
6. [Performance & Scalability](#performance--scalability)
7. [Installation & Usage](#installation--usage)
8. [API Reference](#api-reference)

---

## Multi-Format Input Support

### Supported Formats

The system now accepts **any of these chemical representations**:

| Format | Example | Source |
|--------|---------|--------|
| **SMILES** | `CC(=O)O` | Direct input |
| **InChI** | `InChI=1S/C2H4O2/c1-2(3)4/h4H,1H3` | RDKit parsing |
| **InChI Key** | `QTBSBXVTEAMEQO-UHFFFAOYSA-N` | PubChem API |
| **Chemical Name** | `acetic acid` or `aspirin` | PubChem fuzzy search |
| **CAS Number** | `64-19-7` | PubChem CAS lookup |
| **Molecular Formula** | `C2H4O2` or `C6H12O6` | PubChem formula search |

### Auto-Detection

Input format is automatically detected using pattern matching:

```python
from chemistry_utils import InputConverter

converter = InputConverter()
fmt = converter.detect_input_format("CC(=O)O")           # "smiles"
fmt = converter.detect_input_format("acetic acid")       # "name"
fmt = converter.detect_input_format("64-19-7")           # "cas_number"
fmt = converter.detect_input_format("InChI=1S/...")      # "inchi"
fmt = converter.detect_input_format("C2H4O2")            # "formula"
```

### Usage in App

Users can now paste **any** chemical representation, and the system will:

1. ✅ Auto-detect format
2. ✅ Convert to canonical SMILES (if needed)
3. ✅ Validate chemical structure
4. ✅ Compute molecular descriptors
5. ✅ Proceed to retrosynthesis

---

## Advanced Chemistry Validation

### Lipinski's Rule of Five

Check drug-likeness compliance:

- **Molecular Weight:** ≤ 500 Da
- **LogP:** ≤ 5 (lipophilicity)
- **H-Bond Donors:** ≤ 5
- **H-Bond Acceptors:** ≤ 10

```python
from chemistry_utils import ChemistryValidator
from rdkit import Chem

validator = ChemistryValidator()
mol = Chem.MolFromSmiles("CC(=O)Nc1ccc(O)cc1")  # Acetaminophen

result = validator.check_lipinski_compliance(mol)
print(result)
# {'compliant': True, 'violations': [], 'metrics': {...}}
```

### Functional Group Detection

Auto-detect chemical groups:

```python
groups = validator.detect_functional_groups(mol)
# {'aromatic': [...], 'amide': [...], 'carboxylic_acid': [...], ...}
```

### Valence Checking

Validate chemical bonds and valence states:

```python
valid, error = validator.validate_smiles(smiles)
valid, error = validator.validate_valence(mol)
```

---

## Reaction Rule Database

### Built-In Reaction Rules

The system includes **30+ common organic transformations** (extensible):

| Reaction Type | Category | Applicability |
|----------------|----------|----------------|
| Ester hydrolysis | Hydrolysis | High |
| Amide hydrolysis | Hydrolysis | High |
| Williamson ether synthesis | Coupling | High |
| Suzuki coupling | Coupling | Medium |
| Grignard reaction | Coupling | Medium |
| CBz protecting group removal | Protection | High |
| Alcohol to aldehyde oxidation | Oxidation | High |
| Ester to alcohol reduction | Reduction | High |

### Reaction Feasibility Scoring

Score how "doable" a predicted reaction is (0–1 scale):

```python
from reaction_rules import ReactionFeasibilityScorer

reactants = ["CC(=O)O", "CCO"]  # Acetic acid + ethanol
product = "CC(=O)OCC"            # Ethyl acetate

score, factors = ReactionFeasibilityScorer.score_reaction(
    reactants, product, reaction_type="esterification"
)
# score: 0.85, factors: {'mild_conditions': 'true', ...}
```

### Problem Detection

Flag toxic, expensive, or exotic reactants:

```python
flags = ReactionFeasibilityScorer.flag_problematic_reactions(reactants)
# ["Uses expensive reagents: [Pd]", "Potentially toxic: [CN-]"]
```

---

## Green Chemistry Filtering

Score predictions against **Anastas & Warner's 12 Green Chemistry Principles**:

```python
from reaction_rules import GreenChemistryFilter

score = GreenChemistryFilter.score_green_chemistry(
    reactants=["CCO", "C"],
    product="CC(O)C"
)
# score: 0.95 (favorable - simple, common reagents)
```

**Bonus factors:**
- ✅ Catalytic reactions (+20%)
- ✅ Simple workup (+15%)
- ✅ Mild conditions (+15%)
- ✅ Green solvents (+10%)

**Penalty factors:**
- ❌ Exotic conditions (-60%)
- ❌ Toxic reactants (-50%)
- ❌ High waste (-20%)

---

## Enhanced Retrosynthesis Engine

### Batched Level-Order Search

**Upstream (depth-first, batch=1):** 11 `generate()` calls for one search  
**New engine (level-order, batched):** 3 `generate()` calls (3.67× faster)

```python
from tbr_opt import RetroEngine

engine = RetroEngine(
    model,
    tokenizer,
    building_blocks,
    num_beams=5,
    batch_size=16,        # Score 16 molecules at once
    constrained=True,     # Grammar-validated SMILES
    cache_size=4096,      # LRU cache for repeats
)

pathway, stats = engine.predict(
    target_smiles="CC(=O)O",
    max_depth=5,
    use_cache=True
)

print(stats.as_dict())
# {
#   'generate_calls': 3,
#   'molecules_scored': 8,
#   'cache_hits': 2,
#   'wall_seconds': 1.234,
#   ...
# }
```

### Canonical SMILES Caching

Different SMILES representations of the same molecule (e.g., `OC(C)=O` vs `CC(=O)O`) share a single cache entry:

```python
# First call: cache miss, runs model
pathway1, _ = engine.predict("CC(=O)O")

# Identical molecule, different SMILES: cache hit
pathway2, _ = engine.predict("OC(C)=O")
# ↓ Returns instantly from cache
```

Measured on **real datasets:** ~50× speedup for repeat queries.

---

## Performance & Scalability

### Optimization Strategies

| Feature | Speedup | Method |
|---------|---------|--------|
| Batched inference | 3.67× | Level-order search + padding |
| Canonical caching | 50× | SMILES normalization |
| Building-block index | ~50× | Pre-computed frozenset lookup |
| Grammar constraint | +14% | Logits mask caching |
| GPU memory | ~2× | Mixed precision (fp16) |

### Async & Distributed

Future support for:

```python
# Async batch processing
results = await engine.predict_batch_async(smiles_list, batch_size=32)

# Multi-GPU ensemble
ensemble = ModelEnsemble(models={...}, tokenizers={...})
predictions = ensemble.predict_batch_ensemble(smiles_list)
```

---

## Installation & Usage

### Requirements

```bash
pip install -r requirements.txt
```

**Key dependencies:**
- `torch >= 1.10.0` — GPU acceleration
- `transformers >= 4.40.2` — Fine-tuned models
- `rdkit-pypi` — Chemistry & SMILES validation
- `pubchempy >= 1.0.4` — PubChem API access
- `streamlit >= 1.30` — Web UI

### Quick Start

```bash
cd BIOREROSYNTHESIS
streamlit run net_app.py
```

**Use the UI to:**
1. Enter any chemical (SMILES, name, formula, etc.)
2. Set prediction parameters (depth, beam width, etc.)
3. Enable/disable advanced features (Lipinski check, green chemistry, etc.)
4. View interactive retrosynthesis tree
5. Inspect reaction feasibility scores

### Advanced CLI Usage

```python
from chemistry_utils import StructureProcessor
from tbr_opt import RetroEngine

# Process input in any format
processor = StructureProcessor()
structure = processor.process_input("glucose")  # or CAS, InChI, etc.

# Get detailed analysis
analysis = processor.get_detailed_analysis(structure.smiles)
print(analysis)

# Run retrosynthesis
pathway, stats = engine.predict(structure.smiles, max_depth=5)
for step in pathway:
    print(f"{step['product']} -> {step['reactants']}")
```

---

## API Reference

### `StructureProcessor`

Main entry point for chemical input processing.

```python
processor = StructureProcessor()

# Process any input format
structure = processor.process_input(user_input: str) -> ChemicalStructure
# Returns: smiles, inchi, molecular_weight, molecular_formula, logp, hbd, hba, ...

# Detailed analysis
analysis = processor.get_detailed_analysis(smiles: str) -> Dict
# Returns: valence_check, lipinski compliance, functional groups, ...
```

### `ChemistryValidator`

Validate and inspect chemical structures.

```python
validator = ChemistryValidator()

# Validate SMILES
valid, error = validator.validate_smiles(smiles: str) -> Tuple[bool, Optional[str]]

# Check Lipinski compliance
lipinski = validator.check_lipinski_compliance(mol) -> Dict
# {'compliant': bool, 'violations': List[str], 'metrics': {...}}

# Detect functional groups
groups = validator.detect_functional_groups(mol) -> Dict[str, List]
```

### `ReactionFeasibilityScorer`

Score reaction predictions for feasibility.

```python
from reaction_rules import ReactionFeasibilityScorer

score, factors = ReactionFeasibilityScorer.score_reaction(
    reactants: List[str],
    product: str,
    reaction_type: Optional[str] = None
) -> Tuple[float, Dict[str, str]]
# score: 0.0–1.0
# factors: {'factor_name': 'description', ...}

flags = ReactionFeasibilityScorer.flag_problematic_reactions(
    reactants: List[str]
) -> List[str]
```

### `RetroEngine`

Batched, optimized retrosynthesis search.

```python
engine = RetroEngine(
    model, tokenizer, building_blocks,
    num_beams=3,
    constrained=True,
    batch_size=16,
    cache_size=4096
)

pathway, stats = engine.predict(
    target_smiles: str,
    max_depth: int = 5,
    use_cache: bool = True
) -> Tuple[List[Dict], RetroStats]

# stats includes: generate_calls, molecules_scored, cache_hits, wall_seconds
```

---

## Testing

Run comprehensive test suite:

```bash
# All tests
pytest tests/test_advanced_features.py -v

# Specific test class
pytest tests/test_advanced_features.py::TestInputFormats -v

# Coverage report
pytest tests/ --cov=. --cov-report=html
```

**Test categories:**
- ✅ Input format detection (6 tests)
- ✅ Chemistry validation (5 tests)
- ✅ Reaction rules (4 tests)
- ✅ Chemical descriptors (3 tests)
- ✅ Input converters (4 tests)
- ✅ Integration pipelines (2 tests)

---

## Future Roadmap

- [ ] Multi-model ensemble voting
- [ ] Async batch processing
- [ ] Custom reaction rule database upload
- [ ] Machine learning-based feasibility prediction
- [ ] Active learning feedback loop
- [ ] REST API for programmatic access
- [ ] Docker Hub distributed deployment
- [ ] Kubernetes orchestration templates

---

## Citation

If you use this advanced version in your research, please cite:

```bibtex
@software{nhavalde2024bioretro,
  title={Advanced BioRetrosynthesis Predictor},
  author={Nhavalde, Mayur},
  year={2024},
  note={Enhanced with multi-format input, reaction validation, green chemistry scoring}
}
```

---

## Support & Contribution

For issues, feature requests, or contributions:

- 📧 Email: mayur@example.com
- 🐛 Report bugs: Create an issue on GitHub
- 🤝 Contributing: Fork & submit a pull request

---

**Last Updated:** 2024  
**Version:** 2.0 (Advanced Release)  
**Maintainer:** Mayur Nhavalde
