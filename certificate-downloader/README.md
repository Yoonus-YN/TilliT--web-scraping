# USDA Certificate Downloader

A Python tool that automatically downloads certificate PDFs from USDA Organic Integrity certificate pages.

## Features

- Automatically clicks "Print Certificate"
- Downloads the certificate PDF
- Supports multiple URLs
- Handles JavaScript content using Playwright
- Includes error handling

## Setup

1. Clone the repository

2. Create a virtual environment

python -m venv venv

Activate:

Windows:
venv\Scripts\activate

Mac/Linux:
source venv/bin/activate


3. Install dependencies

pip install -r requirements.txt


4. Install Playwright browser

playwright install


## Usage

### Method 1: Download by URLs list

Add certificate URLs to:

urls.txt

Example:

https://organic.ams.usda.gov/integrity/CP/OPP?cid=87&nopid=6903966799

Run the tool:

python cli.py


### Method 2: Interactive Terminal (Recommended)

Run the interactive downloader:

    python download_by_nop.py

You will see a prompt:

    Enter NOP ID (or S to stop):

- Type a **NOP ID** (e.g. `6903966799`) → the certificate is automatically downloaded
- Type **S** → stop and exit

You can download multiple certificates in one session. All files are saved to `TilliT/downloads/`.


## Output

Downloaded certificates will be saved in the:

downloads/

folder.