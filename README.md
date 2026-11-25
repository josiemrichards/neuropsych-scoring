# neuroscore - automatic scoring of neuropsychological tests

Automatic, validated scoring of four widely used neuropsychological
instruments, with normative adjustment and **equivalent scores** (the
Italian ES 0-4 system) driven by editable configuration files.

| Test | What is scored |
|---|---|
| **MoCA** (Montreal Cognitive Assessment) | 7 domains, total /30, education point reported separately |
| **MMSE** (Mini-Mental State Examination) | 6 domains, total /30 |
| **FAB** (Frontal Assessment Battery) | 6 subtests, total /18 |
| **RAVLT** (Rey Auditory Verbal Learning Test) | immediate recall /75, delayed recall, learning, interference, forgetting, retention, recognition |

## Why

Hand-scoring screening tests is slow and error-prone: wrong conversions
(serial 7s, fluency), sums, or the wrong row of a correction table. This tool:

- **validates every item** (range, missing values, non-numeric entries) and
  explains exactly what is wrong;
- **converts raw performance into points** where scoring rules are
  error-prone (MoCA serial 7s, letter tapping and fluency; FAB fluency);
- applies **normative adjustment** for age and education, using either a
  regression formula or a correction grid;
- assigns **equivalent scores** (ES 0 = impaired ... ES 4);
- processes a whole spreadsheet at once and writes **one report per patient**.

## Quick start

```bash
git clone https://github.com/<your-username>/neuropsych-scoring.git
cd neuropsych-scoring
pip install -e ".[dev]"

# score the example (simulated) patients
neuroscore score data/example_patients.csv \
    --norms norms/demo_norms.json \
    --output results.csv \
    --reports reports/
```

Output:

```
WARNING: Norm set 'DEMO norms' contains DEMO values: results are not valid for clinical use.
Scored 7 patients -> results.csv
1 patient(s) with errors: see the *_error columns.
Reports written to reports/
```

Excerpt of `reports/SIM002.md`:

| Score | Raw | Adjusted | Equivalent score |
|---|---|---|---|
| **total** / 30 | 16 | 18.1 | ES 1 - borderline |
| visuospatial_executive | 3 | - | - |
| delayed_recall | 1 | - | - |

Patient `SIM007` contains a deliberate mistake (MoCA repetition = 4, maximum
is 2): it is reported in the `moca_error` column instead of stopping the batch.

## Input format

One row per patient. Create an empty template with every column:

```bash
neuroscore template -o my_patients.csv              # all tests
neuroscore template -o my_patients.csv -i moca fab  # only some tests
```

- Demographics: `patient_id`, `age`, `education_years`, `sex`.
- Items: `<test>_<item>`, e.g. `moca_naming`, `ravlt_t3`.
- Leave all columns of a test empty if it was not administered.
- Both `,` and `;` separators are accepted (Excel in Italian uses `;`).

Raw performance columns (converted automatically):

| Column | Rule |
|---|---|
| `moca_serial7_correct` | correct subtractions 0-5 -> 4-5 = 3 pts, 2-3 = 2, 1 = 1, 0 = 0 |
| `moca_letters_errors` | errors -> 1 pt if <= 1 |
| `moca_fluency_words` | words in 1 min -> 1 pt if >= 11 |
| `fab_fluency_words` | words -> >9 = 3, 6-9 = 2, 3-5 = 1, <3 = 0 |

## Norms

Normative values are **not hard-coded**: they live in JSON files under
`norms/`, so they can be copied from the original publication and checked
line by line. See [`norms/README.md`](norms/README.md) for the format.

> **The included `demo_norms.json` contains invented numbers** to demonstrate
> the format. Results based on it are labelled `DEMO - not for clinical use`.
> To use the tool with patients, create a norms file from the published
> Italian norms and verify it against the worked examples of the paper.

## Use as a library

```python
import pandas as pd
from neuroscore import NormSet, score_table

norms = NormSet.from_json("norms/my_norms.json")
results = score_table(pd.read_csv("patients.csv"), norms=norms)
```

## Project structure

```
src/neuroscore/
  instruments/   one module per test (items, ranges, conversions)
  norms.py       regression / grid adjustment and equivalent scores
  scoring.py     batch scoring of a table
  report.py      per-patient Markdown report
  cli.py         command-line interface
norms/           normative data files (JSON)
data/            simulated example patients
tests/           49 unit and end-to-end tests
```

Adding a test = one new file in `instruments/` that lists its items.

## Tests

```bash
pytest
```

## Disclaimer

This software supports, and does not replace, clinical judgement. Scores must
be reviewed by a qualified professional. All example data are simulated.
Test materials (MoCA, MMSE, ...) are copyrighted by their authors and are not
included.

## License

MIT
