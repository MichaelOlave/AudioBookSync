import asyncio
import aiofiles
import audible
import json
import sys
import os
from pathlib import Path
import aiocsv
from loguru import logger
import concurrent.futures

# Loguru configuration
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>",
)
logger.add("logs/{time}.log", rotation="500 MB", level="INFO", format="<green>  {time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
)

AUTH_FILE = "Michael.json"
# AUDIBLE_LIBRARY_CSV_FILE = 'audiobooks/audible_library.csv' 
AUDIBLE_LIBRARY_CSV_FILE = 'audiobooks/test_library.csv' 
LOCAL_LIBRARY_CSV_FILE = 'audiobooks/local_library.csv'
DOWNLOAD_DIR = 'audiobooks/downloaded'
DECRYPTED_DIR = 'audiobooks/decrypted'
ACC_BYTES = os.getenv('ACTIVATION_BYTES', 'c3f80507')

# Encrypted formats audible-cli can hand us. aax is unlocked with the account
# wide activation bytes, aaxc with a per file key/iv from its .voucher file.
ENCRYPTED_EXTENSIONS = ('.aax', '.aaxc')

_ffmpeg_aaxc_support = None

def sync_get_library(client):
    """Synchronous method to get library"""
    return client.get(
        "1.0/library",
        num_results=2,
        response_groups="product_desc, product_attrs",
        sort_by="-PurchaseDate"
    )

class AsyncAudibleClient:
    """Wrapper for Audible client to ensure proper async context management"""
    def __init__(self, auth):
        self.auth = auth
        self.client = None
        self.executor = concurrent.futures.ThreadPoolExecutor()

    async def __aenter__(self):
        """Async context entry"""
        # Use run_in_executor to run synchronous client creation
        self.client = await asyncio.get_event_loop().run_in_executor(
            self.executor, 
            audible.Client, 
            self.auth
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Async context exit"""
        if self.executor:
            self.executor.shutdown()
        return False

    async def get_library(self):
        """Async method to get library using thread executor"""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, 
            sync_get_library, 
            self.client
        )

def authenticate():
    """Authenticate with Audible."""
    try:
        # Use synchronous Authenticator method
        auth = audible.Authenticator.from_file(AUTH_FILE)
        return AsyncAudibleClient(auth)
    except FileNotFoundError:
        logger.error(f"Authentication file {AUTH_FILE} not found.")
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise

def normalize_filename(filename):
    return ''.join(char for char in filename if char.isalnum() or char.isspace()).strip().lower()

async def ensure_directory(directory):
    """Ensure the directory exists asynchronously."""
    Path(directory).mkdir(parents=True, exist_ok=True)

async def add_entry(csv_file, entry):
    """Add a book entry to CSV if not already present."""
    try:
        async with aiofiles.open(csv_file, 'r', encoding='utf-8', newline='') as f:
            reader = aiocsv.AsyncReader(f)
            existing_entries = [row async for row in reader]

        if any(existing_entry[0] == entry[0] for existing_entry in existing_entries):
            raise NameError(f"{entry[1]} is already in the library.")

        async with aiofiles.open(csv_file, 'a', encoding='utf-8', newline='') as f:
            writer = aiocsv.AsyncWriter(f)
            await writer.writerow(entry)
            logger.info(f"Added {entry[1]} to the library.")
        return True
    except NameError as e:
        logger.warning(e)
        return False
    except Exception as e:
        logger.error(f"Error adding entry to CSV: {e}")
        return False

async def remove_entry(csv_file, asin):
    """Remove a book entry from CSV."""
    try:
        async with aiofiles.open(csv_file, 'r', encoding='utf-8', newline='') as f:
            reader = aiocsv.AsyncReader(f)
            existing_entries = [row async for row in reader]

        if not any(existing_entry[0] == asin for existing_entry in existing_entries):
            raise Exception(f"{asin} is not in the library.")

        async with aiofiles.open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = aiocsv.AsyncWriter(f)
            for entry in existing_entries:
                if entry[0] != asin:
                    await writer.writerow(entry)
            logger.info(f"Removed {asin} from the library.")
        return True
    except Exception as e:
        logger.error(f"Error removing entry from CSV: {e}")
        return False

async def validate_book(book, directory):
    """Validate a book by checking if it exists in the directory."""
    book_asin = book[0]
    book_title = normalize_filename(book[1])

    for item in os.listdir(directory):
        if book_asin in item or book_title in item:
            logger.info(f"{book_title} exists.")
            return True
    return False

async def download_book(book):
    """Download a book"""
    book_asin = book[0]
    book_title = book[1]
    
    try:
        logger.info(f"Starting download for {book_title}...")
        
        await ensure_directory(DOWNLOAD_DIR)
        
        command = [
            'audible', 'download', 
            '-o', DOWNLOAD_DIR, 
            '-a', book_asin, 
            '--aax-fallback', 
            '-f', 'asin_ascii',
            '-y'
        ]

        logger.info(f"Command: {' '.join(command)}")

        process = await asyncio.create_subprocess_exec(
            'audible', 'download', 
            '-o', DOWNLOAD_DIR, 
            '-a', book_asin, 
            '--aax-fallback', 
            '-f', 'asin_ascii',
            '-y',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            if ("No new files downloaded" in stdout.decode().strip()):
                raise Exception(f"No new files downloaded")
            elif await validate_book(book, DOWNLOAD_DIR):
                logger.success(f"{stdout.decode().strip()}")
                return True
            else:
                raise Exception(f"Download failed for {book_title}: {stdout.decode().strip()}")
        else:
            raise Exception(f"Download failed for {book_title} with code {process.returncode} Error output: {stderr.decode().strip()}")
    
    except asyncio.TimeoutError:
        logger.error(f"Download timed out for {book_title}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading {book_title}: {e}")
        return False
    
def find_encrypted_file(book_asin):
    """Locate the downloaded encrypted file for a book.

    Returns a (path, extension) pair, or (None, None) when nothing matches. The
    voucher that accompanies an aaxc download carries the ASIN in its name too,
    so matching on the ASIN alone is not enough to pick the audio file.
    """
    for item in sorted(os.listdir(DOWNLOAD_DIR)):
        if book_asin not in item:
            continue

        extension = os.path.splitext(item)[1].lower()
        if extension in ENCRYPTED_EXTENSIONS:
            return os.path.join(DOWNLOAD_DIR, item), extension

    return None, None

async def ffmpeg_supports_aaxc():
    """Check once whether FFmpeg exposes the aaxc decryption options.

    The audible_key/audible_iv demuxer options landed in FFmpeg 4.4. Probing the
    demuxer help avoids parsing version strings and gives a clear failure up
    front instead of a cryptic error mid decryption.
    """
    global _ffmpeg_aaxc_support

    if _ffmpeg_aaxc_support is None:
        process = await asyncio.create_subprocess_exec(
            'ffmpeg', '-hide_banner', '-h', 'demuxer=mov',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        _ffmpeg_aaxc_support = 'audible_key' in stdout.decode(errors='replace')

    return _ffmpeg_aaxc_support

async def load_voucher(input_file):
    """Read the AES key/iv audible-cli wrote alongside an aaxc download.

    The key is unique to the file and cannot be derived offline, so a missing
    voucher makes the download unusable.
    """
    voucher_file = f"{os.path.splitext(input_file)[0]}.voucher"

    if not os.path.exists(voucher_file):
        raise FileNotFoundError(f"No voucher found at {voucher_file}")

    async with aiofiles.open(voucher_file, 'r', encoding='utf-8') as f:
        voucher = json.loads(await f.read())

    # The nesting has moved between audible-cli releases, so accept the shapes
    # it has used rather than assuming one.
    candidates = [
        voucher.get('content_license', {}).get('license_response'),
        voucher.get('license_response'),
        voucher
    ]

    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get('key') and candidate.get('iv'):
            return candidate['key'], candidate['iv']

    raise ValueError(
        f"No key/iv pair in {voucher_file}. If the license response is still a "
        f"string it was not decrypted, and audible-cli needs to fetch it again."
    )

async def decrypt_book(book):
    """Decrypt a book using FFmpeg"""
    book_asin = book[0]
    book_title = normalize_filename(book[1])

    try:
        logger.info(f"Starting decryption for '{book_title}' ({book_asin})...")

        # Ensure output directory exists
        await ensure_directory(DECRYPTED_DIR)

        input_file, extension = find_encrypted_file(book_asin)

        if not input_file:
            raise Exception(f"No aax or aaxc file found in {DOWNLOAD_DIR} for {book_asin}")

        output_file = os.path.join(DECRYPTED_DIR, f"{book_title}.m4b")

        # aaxc carries its own key, aax is unlocked with the activation bytes.
        if extension == '.aaxc':
            if not await ffmpeg_supports_aaxc():
                raise Exception("FFmpeg 4.4 or newer is required to decrypt aaxc files")

            key, iv = await load_voucher(input_file)
            drm_options = ['-audible_key', key, '-audible_iv', iv]
        else:
            if not ACC_BYTES:
                raise Exception("ACTIVATION_BYTES is not set, cannot decrypt aax files")

            drm_options = ['-activation_bytes', ACC_BYTES]

        # Create and await the FFmpeg subprocess
        process = await asyncio.create_subprocess_exec(
            'ffmpeg',
            *drm_options,
            '-i', input_file,
            '-c', 'copy',
            output_file,
            '-n',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Wait for the process to complete
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"FFmpeg error decrypting '{os.path.basename(input_file)}': {stderr.decode().strip()}")

        if not await validate_book(book, DECRYPTED_DIR):
            raise Exception(f"Decryption failed for '{os.path.basename(input_file)}': {stdout.decode().strip()}")

        logger.success(f"Decrypted: {output_file}")
        return True

    except Exception as e:
        logger.error(f"An error occurred during decryption: {e}")
        return False

async def compare_libraries():
    """Check the local library for existing books."""
    try:
        async with aiofiles.open(LOCAL_LIBRARY_CSV_FILE, 'r', encoding='utf-8', newline='') as f:
            reader = aiocsv.AsyncReader(f)
            local_entries = [row async for row in reader]
            
        async with aiofiles.open(AUDIBLE_LIBRARY_CSV_FILE, 'r', encoding='utf-8', newline='') as f:
            reader = aiocsv.AsyncReader(f)
            audible_entries = [row async for row in reader]

        missing_entries = [entry for entry in audible_entries if entry not in local_entries]

        if missing_entries:
            logger.warning(f"Missing entries: {len(missing_entries)}")
            return missing_entries
        else:
            logger.info("No missing entries found.")
            return []
        
    except FileNotFoundError:
        logger.warning(f"Local library file {LOCAL_LIBRARY_CSV_FILE} not found.")
        return []
    except Exception as e:
        logger.error(f"Error checking local library: {e}")
        return []

async def update_audible_library():
    """Update the Audible library CSV file."""
    try:
        async with authenticate() as client_wrapper:
            library = await client_wrapper.get_library()

            if not library.get('items'):
                raise NameError("No books found in library.")
            
            for book in library['items']:
                book_entry = [
                    book['asin'], 
                    book['title'], 
                    book['purchase_date'], 
                    book['runtime_length_min']
                ]
                await add_entry(AUDIBLE_LIBRARY_CSV_FILE, book_entry)

    except NameError as e:
        logger.warning(e)
    except Exception as e:
        logger.error(f"An error occurred updating the Audible library: {e}")

async def update_local_library():
    """Update the local library CSV file."""
    try:
        missing_entries = await compare_libraries()

        tasks = []
        for entry in missing_entries:
            task = asyncio.create_task(process_book(LOCAL_LIBRARY_CSV_FILE, entry))
            tasks.append(task)
        
        return tasks

    except Exception as e:
        logger.error(f"An error occurred updating the local library: {e}")

async def main():
    """Async main download workflow."""
    try:
        # Ensure directories exist
        await ensure_directory(os.path.dirname(AUDIBLE_LIBRARY_CSV_FILE))
        await ensure_directory(os.path.dirname(LOCAL_LIBRARY_CSV_FILE))

        # Update the Audible library
        # await update_audible_library()

        # Update the local library
        tasks = await update_local_library()

        logger.warning(f"Tasks: {tasks}")

        # Process books
        await asyncio.gather(*tasks)
    except NameError as e:
        logger.warning(e)
    except Exception as e:
        logger.error(f"An error occurred in the main workflow: {e}")

async def process_book(CSV_FILE, book_entry):
    """Process a single book: add to CSV, download, and decrypt."""
    if await add_entry(CSV_FILE, book_entry):
        try:
            if await download_book(book_entry):
                if not await decrypt_book(book_entry):
                    raise Exception("Decryption failed")
            else:
                raise Exception("Download failed")
        except Exception as e:
            logger.error(f"Processing failed for {book_entry[1]}: {e}")
            await remove_entry(CSV_FILE, book_entry[0])

if __name__ == "__main__":
    asyncio.run(main())