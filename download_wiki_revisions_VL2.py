import argparse
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

import os

DATA_DIR = Path("data") # path to data

def download_page_w_revisions(page_title: str, limit: int = 100): # pull data from web (inputs: specific page as string and number of revisions)
    base_url = "https://en.wikipedia.org/w/index.php"
    params = {
        "title": "Special:Export",
        "pages": page_title,
        "limit": min(limit, 1000),  # Wikipedia API limits to 1000 revisions
        "dir": "desc",
        "action": "submit",
    }
    response = requests.post(base_url, data=params)
    response.raise_for_status()
    return response.text


def parse_mediawiki_revisions(xml_content): # format xml output from web to a string per revision
    soup = BeautifulSoup(xml_content, "lxml-xml")
    for revision in soup.find_all("revision"):
        yield str(revision) # yields revision and then continues with the next


def extract_id(revision: str) -> str: # extract id of each revision to uniquely identify each revision
    return str(_extract_attribute(revision, attribute="id"))


def find_timestamp(revision: str) -> datetime: # extract timestamp from each revision to create folder hierarchy
    return parse_timestring(_extract_attribute(revision, attribute="timestamp"))


def _extract_attribute(text: str, attribute: str = "timestamp") -> str: # function to extract attributes from text (eg. to get timestamp or id)
    soup = BeautifulSoup(text, "lxml-xml")
    result = soup.find(attribute)
    if result is None:
        raise ValueError(f"Could not find attribute {attribute} in text")
    return result.text


def parse_timestring(timestring: str) -> datetime: # converts timestampt to datetime object
    return datetime.strptime(timestring, "%Y-%m-%dT%H:%M:%SZ")


def extract_yearmonth(timestamp: datetime) -> str: # convert datetime object to YYYY-MM
    return timestamp.strftime("%Y-%m")


def find_yearmonth(revision: str) -> str: # extract year and month from revision
    return extract_yearmonth(find_timestamp(revision))


def main(page: str, limit: int, data_dir: Path, folders: bool): # download specific page, validate page & save each revision in a folder structure based on year & month
    """
    Downloads the main page (with revisions) for the given page title.
    Organizes the revisions into a folder structure like
    <page_name>/<year>/<month>/<revision_id>.xml
    """
    print(folders)
    print(f"Downloading {limit} revisions of {page} to {data_dir}")
    raw_revisions = download_page_w_revisions(page, limit=limit)
    validate_page(page, page_xml=raw_revisions)
    print("Downloaded revisions. Parsing and saving...")
    for wiki_revision in tqdm(parse_mediawiki_revisions(raw_revisions), total=limit):
        revision_path = construct_path(
            wiki_revision=wiki_revision, page_name=page, save_dir=data_dir
        )
        if not revision_path.exists():
            revision_path.parent.mkdir(parents=True, exist_ok=True)
        revision_path.write_text(wiki_revision)
    
    print(f"Done! {count_revisions(data_dir/page, folders)} revisions downloaded! {folders} ") # You should call count_revisions() here and print the number of revisions
                   # You should also pass an 'update' argument so that you can decide whether
                   # to update and refresh or whether to simply count the revisions.   



def count_revisions(path_to_subfolder, folders): # make in progress

    count = 0
    
    for item in os.listdir(path_to_subfolder):
        item_path = os.path.join(path_to_subfolder, item)
        
        if os.path.isdir(item_path):
                if folders=="True":
                    count += 1
                count += count_revisions(item_path, folders)  # Recursive call for subdirectories
        else:
            count += 1  # Increment count for files
    
    return count



def construct_path(page_name: str, save_dir: Path, wiki_revision: str) -> Path: # build path for data to be saved
    revision_id = extract_id(wiki_revision)
    timestamp = find_timestamp(wiki_revision)
    year = str(timestamp.year)
    month = str(timestamp.month).zfill(2)
    revision_path = save_dir / page_name / year / month / f"{revision_id}.xml"
    return revision_path


def validate_page(page_name: str, page_xml: str) -> None: # verifies that page exists by checking for "page" attribute
    try:
        _ = _extract_attribute(page_xml, attribute="page")
    except ValueError:
        raise ValueError(f"Page {page_name} does not exist")


if __name__ == "__main__": # only run if file is run directly, if imported file (eg. want to use a function) won't run
    parser = argparse.ArgumentParser(
        description="Download Wikipedia page revisions",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("page", type=str, help="Title of the Wikipedia page")
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of revisions to download",
    )
    parser.add_argument("--count_folders", type=str, help="Should count_revisions also count folders?")
    args = parser.parse_args()
    main(page=args.page, limit=args.limit, folders=args.count_folders, data_dir=DATA_DIR)
