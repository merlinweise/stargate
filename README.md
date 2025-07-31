# STARGATE: Stochastic Parity Game Transformer

This repository contains Python tools for working with **Stochastic Parity Games (SPGs)**, transforming them into **Simple Stochastic Games (SSGs)** and then into **Stochastic Multiplayer Games (SMGs)**, as well as solving them using PRISM-games.

---

## Features

- Convert SPGs (.spg files) to SSGs (.ssg files)
- Convert SSGs to SMGs (.smg files)
- Solve SPGs by transforming to SMGs and checking target reachability
- Supports configurable parameters like epsilon precision and transformation versions
- Handles input/output paths flexibly via command line or global settings
- Debug options to print internal mappings and intermediate data

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/merlinweise/stargate.git
   cd stargate

2. Install dependencies:
    1. PRISM-games (recommending extension from https://github.com/MWeininger/Algorithms-For-Stochastic-Gameshttps://github.com/MWeininger/Algorithms-For-Stochastic-Games)
    2. Install other dependencies listed in requirements.txt
    3. Use Linux System or WSL in Windows
   
## Usage

There are three main command line scripts:
### transform_spg_to_ssg.py
Transform SPG to SSG

    python transform_spg_to_ssg.py [input_file] [output_file] [options]

Converts a .spg file to a .ssg file.

Options include precision --epsilon, overwrite with --force, and input/output directory flags.

### transform_ssg_to_smg.py
Transform SSG to SMG

    python transform_ssg_to_smg.py [input_file] [output_file] [options]

Converts a .ssg file to a .smg file.

Supports versioning of the transformation with --version.

### solve_spg.py
Solve SPG (Full Pipeline)

    python solve_spg.py [input_file] [output_file] [options]

Takes a .spg file, transforms it to .smg and solves for target reachability.

Includes all options from the other scripts plus debug printing.

---

## Configuration

Global configuration options can be set in settings.py, such as:

- Input/output directory paths for Windows and Linux
- Epsilon values for numerical precision
- PRISM solving algorithm path and mode
- Debug flags

**Please edit this file before using STARGATE.**

---

## Development

- Source code is organized inside the src/stargate package.
- Use __init__.py files to define package structure.
- Add new features in separate modules following existing patterns.

---

## Contributing

Feel free to open issues or submit pull requests for improvements, bug fixes, or new features.

---

## Contact

Maintainer: Merlin Weise  
Email: [merlin.weise@rwth-aachen.de]  
GitHub: https://github.com/merlinweise