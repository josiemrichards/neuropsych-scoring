# Norms file format

Norms are kept out of the code on purpose: you copy the coefficients and
cut-offs from the original publication into a JSON file, and the code does the
rest. `demo_norms.json` shows the format with **invented values**: it flags
every result as `DEMO - not for clinical use`.

To use real norms, create a new file (for example `norms/it_norms.json`),
set `"is_demo": false` and fill in one entry per score.

## One entry

```json
{
  "instrument": "moca",
  "score": "total",
  "source": "Author et al., year, journal",
  "range": [0, 30],
  "clip": true,
  "correction": { ... },
  "equivalent_scores": [c0, c1, c2, c3]
}
```

| Field | Meaning |
|---|---|
| `instrument` | `moca`, `mmse`, `fab`, `ravlt` |
| `score` | `total`, a subscale (e.g. `delayed_recall`) or a derived score |
| `source` | full reference, always fill it in |
| `range`, `clip` | if `clip` is true, the adjusted score is kept inside `range` |
| `lower_is_better` | `true` for errors or times (cut-offs then go in decreasing order) |
| `equivalent_scores` | upper bounds (inclusive) of ES 0, ES 1, ES 2, ES 3 on the adjusted score. ES 0 = outer tolerance limit, above `c3` = ES 4 |

## Two types of correction

**Regression formula** (most Italian norms):

```
adjusted = raw - sum( coef * (transform(x) - center) )
```

```json
"correction": {
  "type": "regression",
  "terms": [
    {"variable": "age", "transform": "log100minus", "coef": 0.0, "center": 0.0},
    {"variable": "education_years", "transform": "sqrt", "coef": 0.0, "center": 0.0}
  ]
}
```

Transforms: `identity`, `log`, `sqrt`, `square`, `log100minus` = log(100 - x).
`center` is the mean of the transformed variable in the normative sample.
Check the sign convention of your source: some papers give the correction to
add directly, others the regression coefficient.

**Correction grid** (age band x education band):

```json
"correction": {
  "type": "table",
  "age_bands": [[50, 59], [60, 69]],
  "education_bands": [[0, 5], [6, 8], [9, 13], [14, 30]],
  "values": [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]]
}
```

`values[i][j]` is the amount **added** to the raw score for age band `i` and
education band `j`.

**No correction:** `"correction": {"type": "none"}`.

## Before using a norms file with patients

Check a few published worked examples by hand (most papers include a table of
adjusted scores): enter them in a CSV and verify the output matches.
