# ProcessSim
ProcessSim is a simulation library which can simulate processes with fixed steps. It can be fully controlled by any control systems build by the modeller. Futhermore, the model includes an experimental layer for parrallel and sequential simulation experiments. 

## Install the Required Dependencies
Install the Python 3 packages listed in the following table. There are two ways to install the required dependencies. Firstly, use the
`requirements.txt` to install packages easily using `pip`. Secondly, you
can download packages manually.

| Package | Version |
| --: | --: |
| `numpy` | 1.19.1 |
| `pandas` | 1.1.0 |
| `simpy` | 4.0.1 |

## Use
The model settings can be changes are stored in `control_pannel.py`. That file includes two classes. The first class `ModelPanel` contains the basic settigns which cannot be changed during simulations. The second class `PolicyPanel` are options which can be changed at any point during the simulation. Alternativly, one can specificy additional functionality in `customized_settings.py` and aplly the setting Customized in the correct settingsfields in `control_pannel.py`. 

## Documentation
