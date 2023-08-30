import requests, uuid, subprocess, os, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from .utils import (
    extract_zoro_id,
    colored_text,
    is_sub_dub,
    get_language_code,
    n_m3u8_dl_path,
    get_video_resolution,
    get_readable_time,
)
from .anime_api import AnimeAPI


def download_file(url, save_path):
    """
    Download a file from a given URL and save it to the specified path.

    This function performs an HTTP GET request to download the file from the provided URL.
    The file is saved to the specified local path.

    Args:
        url (str): The URL of the file to download.
        save_path (str): The local path where the downloaded file should be saved.
    """
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
    else:
        print("Failed to download the file.")


class ZORO:
    """
    A class to handle Processing and Downloading anime episodes from ZORO.
    """

    def __init__(
        self,
        url,
        season="1",
        episode=None,
        resolution="1080p",
        dl_type="both",
        group_tag="NOGRP",
    ):
        """
        Initialize the ZORO class with required parameters.

        Args:
            url (str): The URL from ZORO that needs to be processed.
            season (str, optional): The season which will be added to the filename. Defaults to "1".
            episode (str or None, optional): Episodes to be downloaded. Can be a range of episodes (e.g., "1-5"), a single episode (e.g., "10"), or None to download the complete season. Defaults to None.
            resolution (str, optional): The resolution for downloading (e.g., "1080p"). Defaults to "1080p".
            dl_type (str, optional): Download type: "sub", "dub", or "both". Defaults to "both". "sub" will download in JPN Audio with All Available Subtitles, "dub" will download in ENG Audio with All Available Subtitles and "both" with download in JPN-ENG with All Available Subtitles. Make sure to verify the series which you want to DL in "both",If it has same duration in both sub and dub player on ZORO, Only then it will work or else you will have audio sync issues
            group_tag (str, optional): Custom group tag for metadata. Defaults to "Conan76".
        """
        self.zoro_url = url
        self.season = season
        self.requested_episode = episode
        self.resolution = resolution.replace("p", "")
        self.dl_type = dl_type
        self.zoro_id = extract_zoro_id(self.zoro_url)
        self.end_code = str(uuid.uuid4())
        self.custom_group_tag = group_tag
        self.separator = "-" * 70

        self.api = AnimeAPI()
        self.episodes = self.api.get_episodes(self.zoro_id)
        self.setup_episode_start_end()

    def setup_episode_start_end(self):
        """
        Set up the starting and ending episode numbers based on the requested episode range.

        If the requested episode is None, the method sets the episode range to cover all available episodes.
        If the requested episode is specified as a range (e.g., "1-5"), the method extracts the starting and ending
        episode numbers from the range.
        If the requested episode is a single number, it's set as the starting episode, and the ending episode is set to 0.

        This method populates the 'episode_start' and 'episode_end' attributes accordingly.
        """

        if self.requested_episode is None:
            self.episode_start = 1
            self.episode_end = int(len(self.episodes))
        elif "-" in self.requested_episode:
            self.episode_start, self.episode_end = map(
                int, self.requested_episode.split("-")
            )
        else:
            self.episode_start = int(self.requested_episode)
            self.episode_end = 0

    def get_stream_data(self, episode_number):
        """
        Retrieve streaming and subtitle data for a specific episode.

        This method extracts the streams and subtitles for the specified episode.
        It also constructs the complete data dictionary containing various episode details.

        Args:
            episode_number (int): The episode number for which to retrieve data.

        Returns:
            None
        """

        print(colored_text("EXTRACTING STREAMS", "green"))

        episode_index = int(episode_number) - 1
        episode = self.episodes[episode_index]
        episode_id = episode["url"].split("?ep=")[-1]
        find_is_sub_dub = is_sub_dub(episode_id)
        title_season = (
            "0{}".format(self.season)
            if int(self.season) < 10
            else "{}".format(self.season)
        )
        title_episode = (
            "0{}".format(episode_number)
            if int(episode_number) < 10
            else "{}".format(episode_number)
        )

        watch_id = episode["id"].split("$episode")[0]
        watch_id_list = []

        if self.dl_type == "both" and find_is_sub_dub == "both":
            watch_id_list.extend(
                [
                    f"{watch_id}$episode${episode_id}$sub",
                    f"{watch_id}$episode${episode_id}$dub",
                ]
            )

        elif self.dl_type == "dub":
            watch_id_list.extend([f"{watch_id}$episode${episode_id}$dub"])

        elif self.dl_type == "sub":
            watch_id_list.extend([f"{watch_id}$episode${episode_id}$sub"])

        sources = []
        subtitles = []
        complete_data = {
            "sources": sources,
            "subtitles": subtitles,
            "malID": self.api.get_info(self.zoro_id, "malID"),
            "title": self.api.get_info(self.zoro_id, "title"),
            "episodeTitle": episode["title"],
            "season": int(self.season),
            "episode": episode_number,
            "name": f"{self.api.get_info(self.zoro_id, 'title')} S{title_season}E{title_episode} {episode['title']}",
        }

        # Using ThreadPoolExecutor for fetching watch and subtitle information concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(self.fetch_video_sources, watch_id_list, sources)

            if self.dl_type == "both" or self.dl_type == "sub":

                executor.submit(
                    self.fetch_subtitles_sources, watch_id_list[0], subtitles
                )

        self.complete_data = complete_data
        self.video_sources = complete_data["sources"]
        self.subtitle_sources = complete_data["subtitles"]

        self.lang_file_name_data = (
            "JPN-ENG"
            if len(self.video_sources) > 1
            else ("JPN" if self.video_sources[0]["subOrdub"] == "sub" else "ENG")
        )

        self.subs_file_name_data = (
            "MULTI-SUBS" if len(self.subtitle_sources) > 1 else "ENG-SUBS"
        )

    def fetch_video_sources(self, watch_id_list, sources):
        """
        Fetch video sources for the specified watch IDs and store them in the 'sources' list.

        This method queries the AnimeAPI for watch information using the provided watch IDs.
        It extracts the URL of the first video source from Consumet API and determines whether it is a subtitle or dub source.
        The retrieved video source details are then appended to the 'sources' list.

        Args:
            watch_id_list (list): List of watch IDs to fetch video sources for.
            sources (list): List to store the fetched video source dictionaries.

        Returns:
            None
        """
        for wID in watch_id_list:
            watch_info = self.api.get_watch_info(wID)
            stream_dict = {
                "url": watch_info["sources"][0]["url"],
                "subOrdub": wID.split("$")[-1],
            }
            sources.append(stream_dict)

    def fetch_subtitles_sources(self, watch_id, subtitles):
        """
        Fetch subtitle sources for the specified watch ID and store them in the 'subtitles' list.

        This method queries the AnimeAPI for subtitle information using the provided watch ID.It extracts subtitle details such as language, language code,
        and URL for each available subtitle track. The retrieved subtitle details are then appended to the 'subtitles' list.

        Args:
            watch_id (str): Watch ID to fetch subtitle sources for.
            subtitles (list): List to store the fetched subtitle dictionaries.

        Returns:
            None
        """
        subtitle_info = self.api.get_watch_info(watch_id.replace("dub", "sub"))
        subtitles_dict = [
            {
                "lang": sub_data["lang"],
                "lang_639_2": get_language_code(sub_data["lang"].split(" - ")[0]),
                "url": sub_data["url"],
            }
            for sub_data in subtitle_info["subtitles"]
            if sub_data["lang"] != "Thumbnails"
        ]
        subtitles.extend(subtitles_dict)

    def download_video(self):
        """
        Download video sources for each stream in the 'video_sources' list.

        This method iterates through each video source in the 'video_sources' list.
        It constructs a command to invoke the 'n_m3u8_dl' tool with appropriate parameters
        to download the video stream. The downloaded file is saved with a name based on
        the MAL ID, sub/dub information, and a unique code.

        Returns:
            None
        """
        for data in self.video_sources:

            print(
                colored_text("[+] DOWNLOADING", "green"),
                colored_text("JPN" if data["subOrdub"] == "sub" else "ENG", "blue"),
                colored_text("VIDEO SOURCE", "green"),
            )

            cmd = [
                n_m3u8_dl_path,
                data["url"],
                "-sv",
                "res={}".format(self.resolution),
                "--save-name",
                "{}_{}_{}".format(
                    self.complete_data["malID"], data["subOrdub"], self.end_code
                ),
                # '--save-dir',
                # '{} - S{}'.format(self.complete_data['malID'] , self.complete_data['season'])
            ]
            self.out_folder_structure = "{} - S{}".format(
                self.complete_data["title"], self.complete_data["season"]
            )
            subprocess.check_call(cmd)

    def download_subs(self):
        """
        Download subtitle files for each subtitle source in the 'subtitle_sources' list.

        This method iterates through each subtitle source in the 'subtitle_sources' list.
        It invokes the 'download_file' function to download the subtitle file from the provided URL.
        The downloaded subtitle file is saved with a name based on the language code and a unique code.

        Returns:
            None
        """

        print(
            colored_text(
                "[+] DOWNLOADING SUBTITLES (TOTAL - {} FOUND)".format(
                    len(self.subtitle_sources)
                ),
                "green",
            )
        )

        for subs in self.subtitle_sources:
            download_file(
                subs["url"],
                "subtitle_{}_{}.vtt".format(subs["lang_639_2"], self.end_code),
            )

    def mux_files(self):
        """
        Mux video and subtitle files into a single MKV file using FFmpeg.

        This method constructs FFmpeg commands to mux video and subtitle files into a single MKV file.
        It maps video, audio, and subtitle streams accordingly. Metadata such as language and titles
        are added to the resulting MKV file. The final MKV file is named based on various parameters,
        including the custom group tag, video and subtitle language, and resolution.

        Returns:
            str: The filename of the resulting muxed MKV file.
        """
        print(colored_text("[+] MUXING FILES", "green"))

        ffmpeg_opts = [
            "ffmpeg",
            "-y",
        ]

        # Adding Video Files

        for source in self.complete_data["sources"]:
            video_filename = f"{self.complete_data['malID']}_{source['subOrdub']}_{self.end_code}.mp4"
            ffmpeg_opts.extend(["-i", video_filename])

        # Adding Subtitles Files

        if len(self.subtitle_sources) > 1:
            for source in self.subtitle_sources:
                ffmpeg_opts.extend(
                    [
                        "-i",
                        "subtitle_{}_{}.vtt".format(
                            source["lang_639_2"], self.end_code
                        ),
                    ]
                )

        # Mapping 1st Video can be JPN if dl_type == sub or ENG if dl_type == dub
        ffmpeg_opts.extend(["-map", "0:v:0"])

        # Mapping Audio from the 1st Video Source. It can be JPN or ENG acc to the dl_type
        ffmpeg_opts.extend(["-map", "0:a:0"])

        # Mapping Audio from the 2nd Video Source Only If dl_type == both only since then it will have the second Video Source

        if self.dl_type == "both":

            ffmpeg_opts.extend(["-map", "1:a:0"])

        # Mapping Subtitle Source only if dl_type == both

        if len(self.subtitle_sources) > 1:
            for i in range(len(self.subtitle_sources)):
                ffmpeg_opts.extend(["-map", f"{len(self.video_sources)+i}:s:0"])

        # Adding Language Metadata of Subtitles only if dl_type == both

        if len(self.subtitle_sources) > 1:
            for i in range(len(self.subtitle_sources)):
                ffmpeg_opts.extend(
                    [
                        "-metadata:s:s:{0}".format(i),
                        f"language={self.subtitle_sources[i]['lang_639_2']}",
                    ]
                )

        # Adding Audio Metadata

        language_value = {"sub": "jpn", "dub": "eng", "both": "jpn"}.get(
            self.dl_type, ""
        )

        ffmpeg_opts.extend(["-metadata:s:a:0", f"language={language_value}"])

        if self.dl_type == "both":
            ffmpeg_opts.extend(["-metadata:s:a:1", "language=eng"])

        # Adding Encoded by, Audio Title and Video Title Metadata

        ffmpeg_opts.extend(["-metadata", f"encoded_by={self.custom_group_tag}"])
        ffmpeg_opts.extend(["-metadata:s:a", f"title={self.custom_group_tag}"])
        ffmpeg_opts.extend(
            ["-metadata:s:v", f"title={self.custom_group_tag} - Sourced from ZORO"]
        )

        # Adding Subtitle Title metadata

        if len(self.subtitle_sources) > 1:
            for i in range(len(self.subtitle_sources)):
                ffmpeg_opts.extend(
                    [
                        "-metadata:s:s:{0}".format(i),
                        f"title={self.subtitle_sources[i]['lang']}",
                    ]
                )

        out_name = "{}.mkv".format(self.end_code)

        ffmpeg_opts.extend(["-c", "copy", out_name])

        subprocess.check_call(ffmpeg_opts)

        _, height = get_video_resolution(out_name)

        out_file_name = (
            "[{gr}] {name} [{resolution}p] [WEB] [{audio}] [{subs}].mkv".format(
                gr=self.custom_group_tag,
                name=self.complete_data["name"],
                resolution=height,
                audio=self.lang_file_name_data,
                subs=self.subs_file_name_data,
            )
        )

        os.rename(out_name, out_file_name)

        return out_file_name

    def clean_up(self):
        """
        Clean up temporary video and subtitle files generated during the download process.

        This method removes the temporary video and subtitle files that were downloaded during
        the process. It iterates through the 'video_sources' list and 'subtitle_sources' list,
        and deletes the corresponding video and subtitle files.

        Returns:
            None
        """

        print(colored_text("[+] Cleaning Temp Video Files", "green"))

        for data in self.video_sources:
            video_filename = "{}_{}_{}.mp4".format(
                self.complete_data["malID"], data["subOrdub"], self.end_code
            )
            self.remove_file(video_filename)

        print(colored_text("[+] Cleaning Temp Subtitle Files", "green"))

        for data in self.subtitle_sources:
            subtitle_filename = "subtitle_{}_{}.vtt".format(
                data["lang_639_2"], self.end_code
            )
            self.remove_file(subtitle_filename)

    def remove_file(self, file_name):
        """
        Remove a file from the filesystem if it exists.

        Args:
            file_name (str): The name of the file to be removed.

        Returns:
            None
        """
        try:
            Path(file_name).unlink()
        except FileNotFoundError:
            pass

    def processor(self, episode_number):
        """
        Process a single episode for downloading, including streams extraction, downloading video, subtitles, muxing files, and cleanup.

        This method manages the entire download process for a specified episode.
        It first retrieves stream data using the 'get_stream_data' method and processes any exceptions.
        Then, it attempts to download the video using the 'download_video' method and handles any exceptions.
        If multiple subtitles are available, it tries to download subtitles using the 'download_subs' method.
        After downloading, it attempts to mux the downloaded video and subtitles using the 'mux_files' method.
        Finally, it prints completion information and cleans up temporary files using the 'clean_up' method.

        Args:
            episode_number (int): The episode number to be processed.

        Returns:
            None
        """

        process_start = time.time()
        try:
            self.get_stream_data(episode_number)
        except Exception as e:
            print(colored_text("[+] ERROR - Getting Streams", "red"))

        print(
            colored_text("[+] DOWNLOADING", "green"),
            colored_text("- {}".format(self.complete_data["name"]), "blue"),
            colored_text("- {}p".format(self.resolution), "yellow"),
        )

        try:
            self.download_video()
        except Exception as e:
            print(e)
            print(colored_text("[+] ERROR - Downloading Video", "red"))

        if len(self.subtitle_sources) > 1:
            try:
                self.download_subs()
            except Exception as e:
                print(e)
                print(colored_text("[+] ERROR - Downloading Subs", "red"))

        try:
            final_muxed_path = self.mux_files()
            print(
                colored_text(
                    f"[+] TASK COMPLETED IN {get_readable_time(time.time() - process_start)}",
                    "yellow",
                )
            )
            print(colored_text(f"[+] FILE {final_muxed_path}", "blue"))
        except Exception as e:
            print(colored_text("[+] ERROR - Muxing Files", "red"))

        self.clean_up()

    def start_dl(self):
        """
        Start the download process for episodes based on the specified download type and episode range.

        This method initiates the download process according to the specified 'dl_type' and episode range.
        It checks if the 'dl_type' is valid and provides usage instructions for invalid types.
        If only a single episode is requested, the 'processor' method is called for that episode.
        If a range of episodes is requested, the 'processor' method is called for each episode within the range.

        Returns:
            None
        """

        if self.dl_type not in ["sub", "dub", "both"]:

            print(colored_text("[+] ERROR - Invalid dl_type", "red"))
            print(
                colored_text(
                    "[+] dl_type = dub - TO DOWNLOAD IN ENG AUDIO WITH NO SUBS", "green"
                )
            )
            print(
                colored_text(
                    "[+] dl_type = sub - TO DOWNLOAD IN JPN AUDIO WITH ALL AVAILABLE SUBS",
                    "green",
                )
            )
            print(
                colored_text(
                    "[+] dl_type = both - TO DOWNLOAD IN JPN-ENG AUDIO WITH ALL AVAILABLE SUBS",
                    "green",
                )
            )
            return

        # If Single Episode Requested
        if self.episode_end == 0:
            print(self.separator)
            self.processor(self.episode_start)

        # If In Range Episodes Requested
        for ep_index in range(self.episode_start, (self.episode_end + 1)):
            print(self.separator)
            self.processor(ep_index)
