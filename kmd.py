import PySimpleGUI as sg
import sys, os, threading, requests
from queue import Queue
import time


def dload_submission_media(q_in, fmdp_username, dest_folder, return_list, q_out, overwrite= True):
    """
    Thread-friendly download function to download from FMDP
    :param q_in: Input queue. Contains tuples in the format (index, filename)
    :param fmdp_username: Owner of the project on FMDP
    :param dest_folder: Destination folder
    :param return_list: An initialized list to be passed containing download_success_bool for each index
    :param q_out: Normal list containing the filenames which have already been attempted for download
    """
    while not q_in.empty():
        qtuple = q_in.get()
        index = qtuple[0]
        filename = qtuple[1]
        if not overwrite and os.path.exists(f'{dest_folder}\\{filename}'):
            return_list[index] = "File exists"
        else:
            return_list[index] = "Downloading..."
            url = f"{kc_url}/attachment/original?media_file={fmdp_username}/attachments/{filename}"    # Create a q with (index, filename)
            r = requests.get(url, allow_redirects=True)
            if "Attachment not found" in str(r.content):
                return_list[index] = "Failed"
            else:
                open(f'{dest_folder}\\{filename}', 'wb').write(r.content)
                return_list[index] = "Success"
        q_out.append(filename)
        q_in.task_done()


col1 = [
    [sg.Text("Paste filenames, one on each line:")],
    [sg.Multiline(size=(45,15), key="file_list")],
]

row_l1 = [
        sg.Button("Clear"),
        sg.Button("Open Folder"),
        sg.Button("Start Download", key="Download", button_color="green"),
        sg.Button("Exit", button_color="orange", size=(8,1))
]

settings_col = [
    [sg.Text("Settings:  ")],
    [
        sg.Text("Destination Folder"),
        sg.In(size=(25, 1), enable_events=True, key="dest_folder"),
        sg.FolderBrowse()
    ],
    [
        sg.Text("Project Owner"),
        sg.In("keystone_main", size=(25, 1), enable_events=True, key="username")
    ],
    [sg.Checkbox("Overwrite files", key="overwrite")],
    row_l1,
    [sg.Text("Progress: 0/0", key="progress_text", size=(20, 1))],
    [sg.ProgressBar(max_value=100, orientation="horizontal", size=(25,12), key="pbar")],
]

layout = [
    [
    sg.Column(col1),
    sg.Column(settings_col, vertical_alignment="top")
        ],
]

if getattr(sys, 'frozen', False):           # If app is running frozen
    application_path = sys._MEIPASS         # Set the .exe tempfolder as the path (need to pack the icon when building exe)
elif __file__:
    application_path = os.path.dirname(__file__)
    application_path = os.path.join(application_path, "Assets")     # Set the ./Assets folder as the path

iconfile = "fm_wizard_ico.ico"
iconpath = os.path.join(application_path, iconfile)                 # Absolute path of the icon

title = "Image Downloader for Fieldmaster Datapoint v1.0"
window = sg.Window(title, layout)
window.set_icon(iconpath)
dest_folder = ""


def pbar_update():
    while True:
        print(fr"Progress: {len(q_out)}/{len(file_list)}")
        window["pbar"].update(len(q_out))
        progress_string = fr"Progress: {len(q_out)}/{len(file_list)}"
        window["progress_text"].set_size(size=(len(progress_string), 1))
        window["progress_text"].update(progress_string)
        if len(q_out) == len(file_list):
            # Download completed
            window["file_list"].update("")
            for i in range(len(result_list)):
                if result_list[i] == "Failed":
                    window["file_list"].print(f"{file_list[i]} - {result_list[i]}", text_color="red")
            for i in range(len(result_list)):
                if result_list[i] == "File exists":
                    window["file_list"].print(f"{file_list[i]} - {result_list[i]}", text_color="orange")
            for i in range(len(result_list)):
                if result_list[i] == "Success":
                    window["file_list"].print(f"{file_list[i]} - {result_list[i]}", text_color="green")
            break
        time.sleep(1)


while True:
    event, values = window.read()

    if event == "Download":
        file_list = values["file_list"].split("\n")
        file_list = list(dict.fromkeys(file_list))      # Remove duplicates
        file_list = list(filter(None, file_list))       # Remove empties
        username = values["username"]
        dest_folder = values["dest_folder"]
        overwrite = values["overwrite"]
        window["pbar"].update(0, max=len(file_list))
        window["progress_text"].update(fr"Progress: 0/{len(file_list)}")
        q_in = Queue(maxsize=0)
        q_out = []
        result_list = ["Not started" for i in file_list]    # List with same size as file_list with [None, None, ...]
        max_threads = 25

        if dest_folder == "" or len(file_list) == 0 or username == "":
            print("Please specify destination folder, username, and file list!")
            continue

        for i in range(len(file_list)):
            q_in.put((i, file_list[i]))

        threads = []
        for i in range(max_threads):
            print(f"Starting thread {i}")
            thread = threading.Thread(target=dload_submission_media, args=[q_in, username, dest_folder, result_list, q_out, overwrite], daemon=True)
            thread.start()
            threads.append(thread)

        status_thread = threading.Thread(target=pbar_update, args=[], daemon=True)
        status_thread.start()

    if event == "Clear":
        window["file_list"].update("")
        window["pbar"].update(0)
        window["progress_text"].update(fr"Progress: 0/0")

    if event == "Open Folder":
        dest_folder = values["dest_folder"]
        os.startfile(dest_folder)

    if event == "Exit" or event == sg.WINDOW_CLOSED:
        break

window.close()

#   Todo: Add permissions to download