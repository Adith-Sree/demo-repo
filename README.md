# Design of Machine Elements: coding assignment

A Python program that designs three machine elements from user inputs, using a
materials database and the ISO metric thread database, and outputs standard sizes:

| Option | Element | Inputs | Output |
|---|---|---|---|
| Coding 1 | Power transmission shaft | Shaft configuration (bearings + loads) or Mmax/Mmin, fluctuating torque, FoS, material, max diameter, max twist | Standard shaft diameter + material, with fatigue/yield FoS and twist |
| Coding 2 | Rigid flanged coupling (static) | Torque (or power + speed), materials, max diameter, max twist | Shaft, hub, key, flange and bolt dimensions |
| Coding 3 | Bolted joint (fluctuating) | Axial or shear load (min/max), number of bolts, grip, FoS | Standard ISO bolt (size, pitch, length, property class), preload and torque |

It needs only Python 3.10 or newer, with no extra packages.

## Quick start

```bash
python main.py
```

The menu lets you pick a design. Every prompt shows a default in `[brackets]`;
press Enter to accept it or type your own value. At the end the full calculation
sheet is printed and can be saved as a Markdown report.

Run a saved scenario without prompts:

```bash
python main.py --input examples/shaft_beam.json --report reports/shaft.md
```

Run the tests (21 checks, including textbook cross-checks):

```bash
python -m unittest discover -s tests -v
```

## Documentation

* [docs/WALKTHROUGH.md](docs/WALKTHROUGH.md): the full walkthrough. It covers the end-to-end pipeline, the theory and formulas for each step, worked examples, the databases, validation, a demo script and viva questions.
* [docs/sample_reports/](docs/sample_reports/): calculation reports generated from the files in `examples/`.

## Layout

```
main.py              entry point
mdesign/             the package (databases, fatigue formulas, three design modules, CLI)
examples/            input files for each design
tests/               validation tests
docs/                walkthrough and sample reports
```
