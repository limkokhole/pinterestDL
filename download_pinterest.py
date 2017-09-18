#! /usr/bin/env python
import sys
import os
import argparse
from math import ceil
from time import sleep
import urllib.request
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import selenium.webdriver.support.ui as ui
from selenium.webdriver.common.by import By

def find_num_pins(body):
    spans = body.find_elements_by_tag_name("span")
    num_elements = 0
    for span in spans:
        if "Pins" in span.text:
            num_elements = int(span.text.split(" ")[0])
    return num_elements

def find_board_name(board_url):
    name_idx = -1
    if board_url[-1] == "/":
        name_idx = -2
    return board_url.split("/")[name_idx]

def find_all_visible_low_res(body):
    low_res_imgs = body.find_elements(By.XPATH, "//a[@href]")
    low_res_imgs = [link.get_attribute("href") for link in low_res_imgs]
    low_res_imgs = [link for link in low_res_imgs if "/pin/" in link]
    return low_res_imgs

def download_board(high_res_sources, download_folder):
    os.makedirs(download_folder, exist_ok=True)
    board_name = download_folder.split("/")[-1]
    memory_file_name = os.path.join(download_folder, f".cache-{board_name}.txt")
    num_downloads = len(high_res_sources)
    if os.path.isfile(memory_file_name):
        with open(memory_file_name, 'r') as f:
            previously_downloaded = [line.strip() for line in f.readlines()]
    else:
        previously_downloaded = []

    num_already_downloaded = len(previously_downloaded)
    print(f"Ignoring {num_already_downloaded} files, they were already downloaded.")

    for i, source in enumerate(high_res_sources):
        if i % 10 == 0:
            print("Downloading files {} - {}".format(i, min(i + 10, num_downloads)))
        extension = source.split(".")[-1]
        if source not in previously_downloaded:
            urllib.request.urlretrieve(source, os.path.join(download_folder, f"pin_{num_downloads - i + num_already_downloaded}.{extension}"))
            previously_downloaded.append(source)
        else:
            print(f"skipping Pin {i}, already downloaded.")

    with open(memory_file_name, 'w+') as f:
        for source in previously_downloaded:
            f.write(f"{source}\n")

class PinterestDownloader(object):

    def __init__(self, browser_type="chrome"):
        self.browser = None
        if "chrome" in browser_type:
            self.browser = webdriver.Chrome()

    def load_board(self, board_url, download_folder, num_pins=None):
        self.browser.get(board_url)
        sleep(1) # Let the page load bad style

        body = self.browser.find_element_by_tag_name("body")
        board_name = find_board_name(board_url)
        num_pins = find_num_pins(body) if num_pins is None else num_pins
        _download_folder = os.path.join(download_folder, board_name)
        print(f"Will download {num_pins} pins from {board_name} to {_download_folder}")

        low_res_srcs = find_all_visible_low_res(body)
        while len(low_res_srcs) < num_pins:
            self.scroll_down(times=7)
            low_res_srcs = find_all_visible_low_res(body)

        high_res_sources = [self.extract_high_res(low_res_link) for low_res_link in low_res_srcs[:num_pins]]
        download_board(high_res_sources, _download_folder)

    def extract_high_res(self, low_res_link):
        self.browser.get(low_res_link)
        sleep(0.5) # Change to proper wait
        img = self.browser.find_element_by_tag_name("img")
        high_res_source = img.get_attribute("src")
        return high_res_source

    def scroll_down(self, times, sleep_time=0.5):
        scroll_js = "let height = document.body.scrollHeight; window.scrollTo(0, height);"
        for _ in range(times):
            self.browser.execute_script(scroll_js)
            sleep(sleep_time)


def parse_cmd():
    parser = argparse.ArgumentParser(description='Download a pinterest board or tag page.')
    parser.add_argument("link", required=True, dest="link", help="Link to the pinterest page you want to download.")
    parser.add_argument("destination_folder", required=True, dest="dest_folder", help="Folder into which the board will be downloaded.")
    parser.add_argument("-n", "--name", default=None, required=False, dest="board_name",
                        help="The name for the folder the board is downloaded in. If not given, will try to extract board name from pinterest.")
    parser.add_argument("-c", "--count", default=None, required=False, dest="num_pins",
                        help="Download only the first 'c' pins found on the page.")
    args = parser.parse_args()

    if not os.path.isdir(args.dest_folder):
        raise ValueError("The folder you provided does not exist: {}".format(args.dest_folder))
    if args.board_name is not None:
        if os.path.basename(args.dest_folder) == args.board_name:
            args.dest_folder = os.path.dirname(args.dest_folder)

    return args

if __name__ == "__main__":
    arguments = parse_cmd()
    dl = PinterestDownloader()
    dl.load_board(link=arguments.link, dest_folder=arguments.dest_folder,
                  num_pins=arguments.num_pins, board_name=arguments.board_name)
