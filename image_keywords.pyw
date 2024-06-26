# -*- coding: utf-8 -*-
"""
Created on Mon Mar  4 15:53:40 2024

@author: Sergey
"""

import subprocess

import PySimpleGUI as sg
import threading
from openai import OpenAI, RateLimitError, NotFoundError, APIConnectionError
from dotenv import load_dotenv
# import base64
import os
import piexif
# import pandas as pd
from PIL import Image, ImageOps
from io import BytesIO
import time, json
from random import randint
# from concurrent.futures import ThreadPoolExecutor
import requests
import logging

logging.basicConfig(filename='log.log',
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s\n\n',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.WARNING)


logger = logging.getLogger('Image keywords')

load_dotenv()
API_KEY = os.getenv('API_KEY')
VISION_MODELS = ["gpt-4o","gpt-4-turbo-2024-04-09"]
ASSISTANT_ID = os.getenv('ASSISTANT_KEY')
BATCH_SIZE = '1'
version_number = 'Version 2.0.8'
release_notes = 'Adding an option to select specific model'


client = OpenAI(api_key=API_KEY)
try:
    assistant = client.beta.assistants.retrieve(assistant_id = ASSISTANT_ID)
except NotFoundError:
    sg.PopupError('Assistant not found, please check your API and Assistant keys')
    raise RuntimeError
retry_count = 0

def test_openai_api(client):
    msg = [{'role':'user','content':[{'type':'text','text':"Once upon a time,"}]}]
    try:
        # Attempt to generate a simple text completion
        response = client.chat.completions.create(
          model=VISION_MODELS[0],  # Using the Davinci model; change as needed.
          messages=msg,
          max_tokens=5
        )
        
        result = "API Key is valid. Response from OpenAI:"
        result += response.choices[0].message.content.strip()
    except Exception as e:
        result = "There was an issue with the API request."
        result += f"Error: {e}"
    return result

try:
    with open('prompt.txt','r', encoding='utf-8') as p:
        PROMPT = p.read()
except UnicodeDecodeError:
    with open('prompt.txt','r', encoding='cp1251') as p:
        PROMPT = p.read()

def update_dependencies():
    subprocess.call(['pip', 'install', '-r', 'requirements.txt', '--upgrade'], shell = True)

def update(check = False):
    repo_url = "https://raw.githubusercontent.com/misunders2d/image_keywords/master/image_keywords.pyw"
    requirements_file = 'https://raw.githubusercontent.com/misunders2d/image_keywords/master/requirements.txt'
    response = requests.get(repo_url)
    requirements_response = requests.get(requirements_file)
    if response.status_code == 200 and requirements_response.status_code == 200:
        remote_script = response.text
        remote_req = requirements_response.text

        # Read the current script file
        with open(__file__, 'r') as file:
            current_script = file.read()
        if current_script != remote_script:
            if check == True:
                return True
            # If they are different, update the current script
            answer = sg.PopupYesNo('There is an update available\nDo you want to update?\nChanges:\n' + release_notes)
            if answer == "Yes":
                with open(__file__, 'w', encoding = 'utf-8') as file:
                    file.write(remote_script)
                with open('requirements.txt','w') as req_file:
                    req_file.write(remote_req)
                update_dependencies()
                print("Script updated. Please restart the application.")
        else:
            print('No updates found')
    return False

def get_image_paths(folder):
    files = os.listdir(folder)
    files = [os.path.join(folder,x) for x in files if os.path.splitext(x)[-1].lower() in ('.png','.jpg','.jpeg')]
    return files

def resize_image(image_path: str):
    full_image = Image.open(image_path)
    resized_image = ImageOps.contain(full_image, (512,512))
    return resized_image

def convert_image_to_bytes(image_obj):
    img_byte_arr = BytesIO()
    image_obj.save(img_byte_arr, format='jpeg')
    img_byte_arr = img_byte_arr.getvalue()
    return img_byte_arr

def push_to_assistant(file_path, img_bytes, client, uploaded_files_list):
    window['STATUS1'].update('Uploading', background_color = 'yellow', text_color = 'black')
    global retry_count
    try:
        print(f'Uploading {os.path.basename(file_path)} to Assistant\n')
        uploaded_file = client.files.create(
            file = (os.path.basename(file_path),img_bytes),
            purpose = 'vision')
        retry_count = 0
    except APIConnectionError:
        retry_count += 1
        if retry_count < 5:
            print('Assistant unavailable, retrying in 2 seconds')
            time.sleep(2)
            push_to_assistant(file_path, img_bytes, client)
        else:
            print("Couldn't connect in 10 attempts, try later")
            raise Exception
    except Exception as e:
        return e
    uploaded_files_list.append(uploaded_file)
    return None
    
def upload_files(file_paths: list, client: OpenAI, uploaded_files_list: list) -> list:
    file_ids = []
    upload_threads = []
    for file_path in file_paths:
        resized_image = resize_image(file_path)
        img_bytes = convert_image_to_bytes(resized_image)
        upload_threads.append(threading.Thread(target = push_to_assistant, args = (file_path, img_bytes, client, uploaded_files_list)))
        
    for upload_thread in upload_threads:
        time.sleep(randint(0,10)/10)
        upload_thread.start()
        
    for upload_thread in upload_threads:
        upload_thread.join()
        # uploaded_file = 
    file_ids.extend([(uploaded_file.id, uploaded_file.filename) for uploaded_file in uploaded_files_list])
    return file_ids

def batch_describe_files(file_ids, client, thread_list, update_slot, MODEL):
    img_content = [
        {'type':'image_file','image_file':{'file_id':file_id[0]}}
        for file_id in file_ids]
    text_content = [
        {'type':'text',
         'text':f'Describe this image. Use only singular form of for each keyword. All keywords must be single word. Number of keywords MUST be between 45 and 49. Return your response in JSON format where "key" is "{file_id[1]}", and "value" is the payload of your response.'
         }
        for file_id in file_ids]
    
    img_text = list(zip(img_content, text_content))
    
    thread = client.beta.threads.create()
    with open('threads.txt','a') as thread_file:
        thread_file.write(thread.id+'\n')
    try:
        for i in img_text:
            messages = client.beta.threads.messages.create(
                thread_id = thread.id,
                content = [
                    i[0],
                    i[1]
                    ],
                role = 'user',
                )
        # run = client.beta.threads.runs.create_and_poll(thread_id = thread.id, assistant_id = ASSISTANT_ID)
        try:
            run = client.beta.threads.runs.create(
                thread_id = thread.id,
                assistant_id = ASSISTANT_ID,
                model = MODEL,
                additional_instructions=PROMPT)
        except Exception as e:
            logger.error(e)
            raise
        current_run = client.beta.threads.runs.retrieve(run_id = run.id, thread_id = thread.id)
        current_status = current_run.status
        while current_status != 'completed':
            time.sleep(3)
            window[update_slot].update('Processing', background_color = 'red', text_color = 'black', visible = True)
            if current_status == 'failed':
                logger.error(current_run)
                print(current_run.last_error)
                window[update_slot].update('Failed!', background_color = 'red', text_color = 'black', visible = True)
                return
            current_run = client.beta.threads.runs.retrieve(run_id = run.id, thread_id = thread.id)
            current_status = current_run.status
            print(f'Please wait, images processing: {current_status}')
        logger.log(logging.WARNING, current_run)
        window[update_slot].update('Processed', background_color = 'green', text_color = 'black', visible = True)
    except Exception as e:
        print(f'{e}')
    thread_list.append(thread)
    return None
        
def process_response(thread, client):   
    try:     
        messages = client.beta.threads.messages.list(thread.id)
        response = messages.data[0].content[0].text.value
    except Exception as e:
        print(e)
        response = '''{"Image":"None"}'''
    
    if response == '''{"Image":"None"}''':
        response = process_response(thread, client)
    
    response = response.replace('```','').replace('json\n','')
    response = json.loads(response)
    return response

def calculate_cost(thread, client, MODEL):
    input_cost, output_cost = (5,15) if MODEL == 'gpt-4o' else (10,30)
    try:
        run_list = client.beta.threads.runs.list(thread_id = thread.id).data[0]
        input_tokens = run_list.usage.prompt_tokens
        output_tokens = run_list.usage.completion_tokens
        total_cost = (input_tokens * input_cost / 1000000) + (output_tokens * output_cost / 1000000)
    except:
        total_cost = -1
    return total_cost

def delete_thread(thread, client):
    print(f'Deleting thread {thread.id}')
    try:
        client.beta.threads.delete(thread_id = thread.id)
        with open('threads.txt','r') as thread_file:
            all_threads = thread_file.read()
            modified_threads = all_threads.replace(thread.id, '')
        with open('threads.txt','w') as thread_file:
            thread_file.write(modified_threads)
    except NotFoundError:
        pass
    return None
    
def delete_files(file_ids, client):
    print('removing files from Assistant')
    for f in file_ids:
        try:
            client.files.delete(f[0])
        except NotFoundError:
            pass
    return None

def apply_response(response: dict) -> None:
    for key, value in response.items():
        filename = key
        title = value.get('xp_title')
        description = value.get('xp_subject')
        keys = value.get('xp_keywords')
        exif_dict = piexif.load(os.path.join(folder, filename))
        del exif_dict["1st"]
        del exif_dict["thumbnail"]    
        
        # Define EXIF tags for the data (using constants for clarity)
        exif_ifd = exif_dict["0th"]
        exif_tags = piexif.ImageIFD
        
        exif_ifd[piexif.ImageIFD.XPTitle] = title.encode("utf-16le")  # Title
        exif_ifd[270] = description.encode("utf-8")    # Subject
        
        # Handle keywords as a list of encoded strings
        exif_ifd[exif_tags.XPKeywords] = keys.encode("utf-16le") # Keywords
        
        # Convert the modified EXIF data to bytes
        exif_bytes = piexif.dump(exif_dict)
        initial_img = Image.open(os.path.join(folder, filename))
        new_file_name = os.path.join(modified_folder, os.path.basename(filename))
        try:
            initial_img.save(new_file_name, exif = exif_bytes, quality = 'keep')
        except Exception as e:
            logger.error(e,'\n',new_file_name)
            print(e,'\n', new_file_name)
    return None

    
def launch_main(file_paths, MODEL):
    total_cost = 0
    uploaded_files_list = []
    uploaded_file_ids = upload_files(file_paths, client, uploaded_files_list)
    file_id_batches = [uploaded_file_ids[i:i + BATCH_SIZE] for i in range(0, len(uploaded_file_ids), BATCH_SIZE)]
    thread_list = []
    jobs = []
    for i, file_ids in enumerate(file_id_batches):
        jobs.append(threading.Thread(target = batch_describe_files, args = (file_ids, client, thread_list, update_slots[i], MODEL)))
        
    for job in jobs:
        job.start()
    for job in jobs:
        job.join()
    for thread in thread_list:
        try:
            response = process_response(thread, client)
        except Exception as e:
            logger.error('\n\n', e, "thread: ", thread.id)
            print(f"Can't process response:\n{e}")
        thread_cost = calculate_cost(thread, client, MODEL)
        total_cost += thread_cost
        # window.write_event_value('RESPONSE', response)
        try:
            apply_response(response)
        except Exception as e:
            logger.error('\n\n', e)
            print(f"Can't apply exif:\n{e}")
        delete_thread(thread, client)
    window['TOKENS'].update(f'Total cost is {total_cost} or {round(total_cost / len(uploaded_file_ids),4)} per image')
    delete_files(uploaded_file_ids, client)
    # os.startfile(modified_folder)
    print('All done')
    return None

def main_window():
    global modified_folder, folder, window, update_slots, BATCH_SIZE
    update_available = update(check = True)
    update_slots = ['STATUS'+str(i) for i in range(1,31)]
    

    left_column = [
        [sg.Text('Select a folder with image files'), sg.Input('', key = 'FOLDER', enable_events=True, visible=False), sg.FolderBrowse('Browse', target='FOLDER')],
        [sg.Text('Select a model to use:'), sg.DropDown(VISION_MODELS, default_value=VISION_MODELS[0], key = '-MODEL-')],
        [sg.Output(size = (60,20))],
        [sg.ProgressBar(100, size = (40,8), key = 'BAR')],
        [sg.Text('No tokens used so far', key = 'TOKENS')],
        [sg.Button('Describe!'),
         sg.Button('Cancel'),
         sg.Button('Check connection', tooltip = 'Check if OpenAI key and connection are OK'),
         sg.Button('Update', visible=update_available, tooltip=release_notes)]
    ]
    
    right_column = [
        [sg.Text('Set batch size'), sg.Input(BATCH_SIZE, key = 'BATCH', size = (3,1))],
        [sg.Text('Job status')],
        [sg.Text('Not started', key = 'STATUS1', background_color=None)],
        [sg.Text('Not started', key = 'STATUS2', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS3', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS4', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS5', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS6', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS7', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS8', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS9', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS10', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS11', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS12', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS13', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS14', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS15', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS16', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS17', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS18', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS19', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS20', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS21', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS22', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS23', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS24', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS25', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS26', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS27', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS28', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS29', background_color=None, visible = False)],
        [sg.Text('Not started', key = 'STATUS30', background_color=None, visible = False)],
        [sg.vbottom(sg.Text(f'{version_number}', relief = 'sunken'))]
        ]
    layout = [[sg.Column(left_column),sg.VerticalSeparator(),sg.vtop(sg.Column(right_column))]]

    window = sg.Window(title = 'Image keyword generator', layout = layout)
    
    while True:
        event,values = window.read()
        
        if event in ('Cancel', sg.WINDOW_CLOSED):
            with open('threads.txt','r') as thread_file:
                all_threads = thread_file.read().split('\n')
                all_threads = [x for x in all_threads if x != '']
            for thread in all_threads:
                print(f'please wait, deleting thread {thread}')
                try:
                    client.beta.threads.delete(thread)
                    all_threads.remove(thread)
                except NotFoundError:
                    all_threads.remove(thread)
                except Exception:
                    pass
                finally:
                    client.close()
            with open('threads.txt','w') as thread_file:
                thread_file.write('\n'.join(all_threads))
            break
        elif event == 'Check connection':
            print(test_openai_api(client))

        elif event == 'Update':
            update()
        elif event == 'RESPONSE':
            response = values['RESPONSE']
            print(response)
        elif event == 'FOLDER':
            folder = values['FOLDER']
            files = get_image_paths(folder)
            print(f'There are {len(files)} image files in the selected folder')
        elif event == 'Describe!':
            BATCH_SIZE = int(values['BATCH'])
            MODEL = values['-MODEL-']
            folder = values['FOLDER']
            if folder != '':
                modified_folder = os.path.join(folder,'modified')
                try:
                    os.makedirs(modified_folder)
                except:
                    pass
                all_files = get_image_paths(folder)
                if len(all_files) > 0:
                    progress = 100/len(all_files)
                    print(f"Please wait, working on {len(all_files)} at once\n")
                    window.start_thread(lambda: launch_main(all_files, MODEL), 'FINISHED_BATCH')
                else:
                    progress = 100
                    print('There are no image files in the selected folder')
            else:
                print('Please select a folder first')

    window.close()
    
    return None

if __name__ == '__main__':
    try:
        main_window()
    except Exception as e:
        logger.error('\n\n', e)
        logger.exception('Traceback: \n')
