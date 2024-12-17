import asyncio
import aiofiles
import audible
import sys
import os
from pathlib import Path
import aiocsv
from loguru import logger
import concurrent.futures

# Loguru configuration
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("audible_download.log", rotation="500 MB", level="INFO")

AUTH_FILE = "Michael.json"
CSV_FILE = 'audiobooks/audible_library.csv'
DOWNLOAD_DIR = 'audiobooks/downloaded'

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
            logger.info(f"{entry[1]} is already in the library.")
            return False

        async with aiofiles.open(csv_file, 'a', encoding='utf-8', newline='') as f:
            writer = aiocsv.AsyncWriter(f)
            await writer.writerow(entry)
            logger.info(f"Added {entry[1]} to the library.")
        return True
    except Exception as e:
        logger.error(f"Error adding entry to CSV: {e}")
        return False

async def download_book(book, output_dir):
    """Download a book"""
    book_title = book['title']
    book_asin = book['asin']
    
    try:
        logger.info(f"Starting download for {book_title}...")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Create subprocess with standard output and error
        process = await asyncio.create_subprocess_exec(
            'audible', 'download', 
            '-o', output_dir, 
            '-a', book_asin, 
            '--aax-fallback', 
            '--filename-mode', 'unicode',
            '-y',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        if process.returncode == 0:
            logger.success(f"Successfully downloaded {book_title}")
            return True
        else:
            logger.error(f"Download failed for {book_title} with code {process.returncode}")
            return False
    
    except asyncio.TimeoutError:
        logger.error(f"Download timed out for {book_title}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error downloading {book_title}: {e}")
        return False
    
async def decrypt_book(book, output_dir, acctivation_bytes):
    pass

async def main():
    """Async main download workflow."""
    try:
        # Ensure directories exist
        await ensure_directory(os.path.dirname(CSV_FILE))
        await ensure_directory(DOWNLOAD_DIR)

        # Authenticate and get client
        async with authenticate() as client_wrapper:
            library = await client_wrapper.get_library()

            if not library.get('items'):
                logger.warning("No books found in library.")
                return

            # Create tasks for concurrent processing
            tasks = []
            for book in library['items']:
                book_entry = [
                    book['asin'], 
                    book['title'], 
                    book['purchase_date'], 
                    book['runtime_length_min']
                ]
                
                # Create a task that adds to CSV and downloads
                task = asyncio.create_task(process_book(book_entry, book))
                tasks.append(task)

            # Wait for all tasks to complete
            await asyncio.gather(*tasks)

    except Exception as e:
        logger.exception(f"An error occurred in the main workflow: {e}")

async def process_book(book_entry, book):
    """Process a single book: add to CSV and download."""
    if await add_entry(CSV_FILE, book_entry):
        await download_book(book, DOWNLOAD_DIR)

if __name__ == "__main__":
    # Use asyncio to run the main coroutine
    asyncio.run(main())