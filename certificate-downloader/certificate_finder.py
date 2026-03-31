import os

def find_certificate(nop_id, directory="downloads"):
    """
    Search for a certificate file in the specified directory based on the provided NOP ID.

    Args:
        nop_id (str): The NOP ID to search for.
        directory (str): The directory to search in. Defaults to "downloads".

    Returns:
        str: The path to the certificate file if found, otherwise None.
    """
    for root, _, files in os.walk(directory):
        for file in files:
            if nop_id in file:  # Check if the NOP ID is part of the file name
                return os.path.join(root, file)
    return None

if __name__ == "__main__":
    nop_id = input("Enter the NOP ID to search for: ")
    result = find_certificate(nop_id)

    if result:
        print(f"Certificate found: {result}")
    else:
        print("Certificate not found.")