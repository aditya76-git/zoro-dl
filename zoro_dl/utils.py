import os, requests, subprocess, re, json
from bs4 import BeautifulSoup
script_directory = os.path.dirname(os.path.abspath(__file__))


def setup_environment():
    """
    Set up the environment for the download script.

    This function determines the operating system, sets up the path to the 'N_m3u8DL-RE' executable,
    and adjusts permissions if necessary. It returns the script directory and the path to the
    'N_m3u8DL-RE' executable based on the operating system.

    Returns:
        tuple: A tuple containing the script directory and the path to 'N_m3u8DL-RE' executable.
    """
    if os.name == "nt":
        iswin = "1"
    else:
        iswin = "0"

    if iswin == "0":
        n_m3u8_dl_path = os.path.join(script_directory, "static", "N_m3u8DL-RE")
        os.system(f"chmod 777 {n_m3u8_dl_path}")

    elif iswin == "1":
        n_m3u8_dl_path = os.path.join(script_directory, "static", "N_m3u8DL-RE.exe")

    return script_directory, n_m3u8_dl_path


script_directory, n_m3u8_dl_path = setup_environment()


def is_sub_dub(episode_id):
    """
    Determine if a given episode has both subbed and dubbed versions available.

    This function queries the AniWatch website to check if both subbed and dubbed versions of an episode are available.
    It makes a request to retrieve the episode's server information and looks for the presence of "DUB:" and "SUB:" tags
    in the HTML response. If both are present, it returns 'both', if only "DUB:" is present, it returns 'dub', if only "SUB:"
    is present, it returns 'sub', and if neither are present, it returns 'unknown'.

    Args:
        episode_id (str): The unique identifier of the episode.

    Returns:
        str: A string indicating whether the episode has both subbed and dubbed versions ('both'),
             only a dubbed version ('dub'), only a subbed version ('sub'), or neither ('unknown').
    """
    html = requests.get(
        f"https://aniwatch.to/ajax/v2/episode/servers?episodeId={episode_id}"
    ).json()["html"]

    if "DUB:" in html and "SUB:" in html:
        return "both"
    elif "DUB:" in html:
        return "dub"
    elif "SUB:" in html:
        return "sub"
    else:
        return "unknown"


def get_video_resolution(video_path):
    """
    Retrieve the resolution (width and height) of a video file.

    This function uses 'ffprobe' to analyze the specified video file and extract its resolution.
    It executes a command-line subprocess to gather video stream information, including width and height.
    In case of success, it returns a tuple containing the width and height. If there's an error or the
    resolution cannot be determined, it returns None.

    Args:
        video_path (str): The path to the video file.

    Returns:
        tuple or None: A tuple containing the video width and height if successful, or None if there's an error.
    """
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            video_path,
        ]
        output = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, universal_newlines=True
        )
        width, height = map(int, output.strip().split(","))
        return width, height
    except (subprocess.CalledProcessError, ValueError):
        return None


def extract_zoro_id(url):
    """
    Extract the Zoro ID from a given URL.

    This function takes a URL from the Zoro website and extracts the unique ID associated with the content.
    It uses a regular expression pattern to capture the ID from the URL and returns it. If no match is found,
    it returns None.

    Args:
        url (str): The URL from which to extract the Zoro ID.

    Returns:
        str or None: The extracted Zoro ID if found in the URL, or None if no match is found.
    """
    pattern = r"https?://[^/]+/(?:watch/)?([a-zA-Z0-9-]+)/?"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None



def get_language_code(language_name):
    """
    Get the ISO 639-2 language code for a given language name.

    This function takes a language name and searches for its corresponding ISO 639-2 language code.
    It reads language information from a JSON file and matches the input language name to the stored data.
    If a match is found, it returns the ISO 639-2 code; otherwise, it returns an empty string.

    Args:
        language_name (str): The name of the language.

    Returns:
        str: The ISO 639-2 language code if a match is found, or an empty string if no match is found.
    """

    json_file_path = os.path.join(script_directory, "static", "languages_info.json")

    with open(json_file_path, "r") as json_file:
        language_info = json.load(json_file)

    for code, info in language_info.items():
        if info["en"][0] == language_name:
            return info["639-2"]
    return ""


def colored_text(text, color):
    """
    Format text with ANSI color codes for terminal output.

    This function takes a text and a color name as input and returns the input text formatted with ANSI color codes.
    The available color names are: "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white", and "reset".
    The "reset" color is used to reset the color formatting to the default terminal color.

    Args:
        text (str): The text to be formatted.
        color (str): The color name to apply to the text.

    Returns:
        str: The input text formatted with the specified color.
    """
    colors = {
        "black": "\033[30m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "reset": "\033[0m",
    }
    return f"{colors[color]}{text}{colors['reset']}"


def get_readable_time(seconds: int) -> str:
    """
    Convert a time duration in seconds to a human-readable format.

    This function takes a time duration in seconds and converts it to a human-readable format.
    The format includes days, hours, minutes, and seconds, excluding any zero-value components.

    Args:
        seconds (int): The time duration in seconds.

    Returns:
        str: A human-readable representation of the time duration.
    """
    result = ""
    (days, remainder) = divmod(seconds, 86400)
    days = int(days)
    if days != 0:
        result += f"{days}d"
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours != 0:
        result += f"{hours}h"
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes != 0:
        result += f"{minutes}m"
    seconds = int(seconds)
    result += f"{seconds}s"
    return result
