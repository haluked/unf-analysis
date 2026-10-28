# unf-analysis

A lightweight desktop tool to analyze Instagram followers and unfollowers locally.

## Features

- Identifies users who do not follow back, fans, and mutual followers
- Tracks lost and new followers across scans
- Uses an isolated browser profile without affecting open browser sessions
- Supports Brave, Google Chrome, and Microsoft Edge via Selenium
- Exports results to CSV and JSON

## Installation

Requires Python 3.10 or newer.

```bash
pip install -r requirements.txt
```

## Usage

Start the application:

```bash
python unf-analysis.py
```

1. Enter your Instagram username.
2. Log in using the browser window or enter credentials.
3. Select an analysis mode and start the scan.
4. View results in the table or export them to CSV/JSON.

## Tests

Run the test suite:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## License

GNU General Public License v3.0. See [LICENSE](LICENSE) for details.
