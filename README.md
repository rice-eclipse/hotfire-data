# hotfire-data

Tools and notebooks for preprocessing, analyzing, and visualizing engine hotfire thrust, pressure, temperature, and event data.

## Python modules

- `filtering.py` - Defines an `LPF` helper that builds and applies a SciPy FIR low-pass filter to smooth sensor signals.
- `preprocessing.py` - Converts raw hotfire data into processed `data.npz`/`data.csv` files, parses controller logs into `events.csv`, and imports processed data/events for analysis notebooks.
- `visualization.py` - Provides utilities for finding samples by time and plotting sensor data around logged events with optional filtering and multi-curve overlays.

## Notebooks

Each `analysis-*.ipynb` notebook is a hotfire-specific analysis workspace. Most follow the same rough pattern: define the data directory, map raw sensor names to readable labels, map driver IDs to valve/event names, preprocess raw logs/data, import processed data/events, then create ignition-centered plots.

## Usage

### Dependencies
- Install the packages listed in `requirements.txt`
- If you do not wish to affect existing installations on your system, create and run a [Virtual Environment](https://docs.python.org/3/library/venv.html)

### Data requirements
- Data file pulled from the RPi must be named `raw.csv`
- Log file must be named `console.log`
- Place these two files in a `data-raw` folder which is placed in a <hotfire-dir> folder as shown below

```text
<hotfire-dir>/
  data-raw/
    raw.csv
    console.log
```

TODO: Add preprocessing example.

```python
import preprocessing as prep

DATA_DIR = "TODO"
SENSORS = {
    # "raw_sensor_name": "Readable Sensor Name",
}
DRIVERS = {
    # driver_id: {"name": "Valve Name", "False": "Close", "True": "Open"},
}

prep.process_events_quonkboard(DATA_DIR, DRIVERS)
prep.process_data(DATA_DIR, SENSORS)
```

TODO: Add analysis/plotting example.

```python
import preprocessing as prep
import visualization as vis
from filtering import LPF

events = prep.import_events(DATA_DIR)
labels, data = prep.import_data(DATA_DIR, events)

plotter = vis.EventPlotter(data, events, dpi=100)
filter = LPF(fs=300, length=101, cutoff=10, window="blackman")

plotter.plot(
    sensor_id=1,
    event_id=0,
    duration=40,
    filter=filter,
    title="TODO",
    ylabel="TODO",
)
```
