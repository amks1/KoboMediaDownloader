import PySimpleGUI as sg
import sys, os, threading, requests
from queue import Queue
import time



def dload_submission_media(q_in, return_list, q_out):
    """
    :param q_in: Input queue. Contains tuples in the format (index, filename)
    :param username: Owner of the project
    :param dest_folder: Destination folder
    :param return_list: An initialized list to be passed containing download_success_bool for each index
    :param q_out: Normal list containing the filenames which have already been attempted for download
    """
    headers = {'Authorization': f'Token {token}'}
    url_part = f"{kc_url}/attachment/original?media_file={username}/attachments"
    while not q_in.empty():
        qtuple = q_in.get()
        index = qtuple[0]
        filename = qtuple[1]
        if not overwrite and os.path.exists(f'{dest_folder}\\{filename}'):
            return_list[index] = "File exists"
        else:
            url = f"{url_part}/{filename}"
            r = requests.get(url, allow_redirects=True, headers=headers)
            if "Attachment not found" in str(r.content):
                return_list[index] = "Failed"
            else:
                open(f'{dest_folder}\\{filename}', 'wb').write(r.content)
                return_list[index] = "Success"
        q_out.append(filename)
        q_in.task_done()


def save_config():
    with open("config", "w") as config_file:
        config_file.write(username + ",")
        config_file.write(dest_folder + ",")
        config_file.write(token + ",")
        config_file.write(str(values["kobotoolbox"]) + ",")
        config_file.write(str(values["ocha"]) + ",")
        config_file.write(str(overwrite))


try:
    with open("config", "r") as config_file:
        previous_config = config_file.read()
    previous_config = previous_config.split(",")
    print(previous_config)
    username = previous_config[0]
    dest_folder = previous_config[1]
    token = previous_config[2]
    server_kobo = (previous_config[3] == "True")
    server_ocha = (previous_config[4] == "True")
    overwrite = (previous_config[5] == "True")
except FileNotFoundError:
    username = ""
    dest_folder = ""
    token = ""
    server_kobo = False
    server_ocha = False
    overwrite = False


col1 = [
    [sg.Text("Paste filenames, one on each line:")],
    [sg.Multiline(size=(45,15), key="file_list")],
]

col2 = [
    [sg.Text("Settings:  ")],
    [
        sg.Text("Destination Folder"),
        sg.In(dest_folder, size=(25, 1), enable_events=True, key="dest_folder"),
        sg.FolderBrowse()
    ],
    [
        sg.Text("Project Owner"),
        sg.In(username, size=(25, 1), enable_events=True, key="username")
    ],
    [
        sg.Text("Access Token"),
        sg.In(token, size=(25, 1), enable_events=True, key="token")
    ],
    [sg.Radio("KoBoToolbox", group_id="server", key="kobotoolbox", default=server_kobo), sg.Radio("OCHA", group_id="server", key="ocha", default=server_ocha)],
    [sg.Checkbox("Overwrite files", key="overwrite", default=overwrite)],
    [
        sg.Button("Clear"),
        sg.Button("Open Folder"),
        sg.Button("Start Download", key="Download", button_color="green"),
        sg.Button("Exit", button_color="orange", size=(8,1))
    ],
    [sg.Text("Progress: 0/0", key="progress_text", size=(20, 1))],
    [sg.ProgressBar(max_value=100, orientation="horizontal", size=(25,12), key="pbar")],
    # [sg.Button("Test")]
]

layout = [
    [
    sg.Column(col1),
    sg.Column(col2, vertical_alignment="top")
    ],
]

if getattr(sys, 'frozen', False):           # If app is running frozen
    application_path = sys._MEIPASS         # Set the .exe tempfolder as the path (need to pack the icon when building exe)
elif __file__:
    application_path = os.path.dirname(__file__)

iconfile = "kobo.ico"
iconpath = os.path.join(application_path, iconfile)                 # Absolute path of the icon

title = "Kobo Media Downloader"
window = sg.Window(title, layout)
window.set_icon(iconpath)
dest_folder = ""


def pbar_update():
    while True:
        # print(fr"Progress: {len(q_out)}/{len(file_list)}")
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
                    window["file_list"].print(f"{file_list[i]} - {result_list[i]}", text_color="blue")
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
        token = values["token"]
        if values["kobotoolbox"]:
            kc_url = "https://kc.kobotoolbox.org"
        elif values["ocha"]:
            kc_url = "https://kc.humanitarianresponse.info"
        save_config()
        window["pbar"].update(0, max=len(file_list))
        window["progress_text"].update(fr"Progress: 0/{len(file_list)}")
        q_in = Queue(maxsize=0)
        q_out = []
        result_list = [None for i in file_list]    # List with same size as file_list
        max_threads = 25

        if dest_folder == "" or len(file_list) == 0 or username == "":
            print("Please specify destination folder, username, and file list!")
            continue

        for i in range(len(file_list)):
            q_in.put((i, file_list[i]))

        threads = []
        for i in range(max_threads):
            # print(f"Starting thread {i}")
            # thread = threading.Thread(target=dload_submission_media, args=[q_in, username, token, kc_url, dest_folder, result_list, q_out, overwrite], daemon=True)
            thread = threading.Thread(target=dload_submission_media,
                                      args=[q_in, result_list, q_out],
                                      daemon=True)
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
        save_config()
        break

window.close()

