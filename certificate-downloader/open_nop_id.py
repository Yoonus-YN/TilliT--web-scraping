import webbrowser

def open_nop_page():
    # Prompt the user to enter the NOP ID
    nop_id = input("Enter the NOP ID: ")

    # Construct the URL
    base_url = "https://organic.ams.usda.gov/integrity/CP/OPP?cid=87&nopid="
    full_url = f"{base_url}{nop_id}"

    # Open the URL in the default web browser
    print(f"Opening webpage: {full_url}")
    webbrowser.open(full_url)

if __name__ == "__main__":
    open_nop_page()