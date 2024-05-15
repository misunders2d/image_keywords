# -*- coding: utf-8 -*-
"""
Created on Mon Mar  4 15:53:40 2024

@author: Sergey
"""

import subprocess

import PySimpleGUI as sg
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv
import base64
import os
import piexif
# import pandas as pd
from PIL import Image, ImageOps
from io import BytesIO
import time, json
from random import randint
from concurrent.futures import ThreadPoolExecutor
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
VISION_MODEL = "gpt-4o"#"gpt-4-turbo-2024-04-09" # "gpt-4-vision-preview" "gpt-4-turbo-2024-04-09" - new version
ASSISTANT_ID = 'asst_zwOvUO84dbtWqCHwUD0pY5Ho'
version_number = 'Version 2.0.1'
release_notes = 'Switched to GPT-4o'

def test_openai_api(client):
    msg = [{'role':'user','content':[{'type':'text','text':"Once upon a time,"}]}]
    try:
        # Attempt to generate a simple text completion
        response = client.chat.completions.create(
          model=VISION_MODEL,  # Using the Davinci model; change as needed.
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
    subprocess.call(['pip', 'install', '-r', 'requirements.txt'], shell = True)

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

def main_window():
    global window, all_files, modified_folder, client, samples, sample_pics, sample_file, BATCH_SIZE
    update_available = update(check = True)

    client = OpenAI(api_key=API_KEY)
    client.timeout.pool = 60
    client.timeout.read = 60
    client.timeout.write = 60

    presets = [os.path.splitext(x)[0] for x in os.listdir(os.getcwd()) if os.path.splitext(x)[-1] == '.json']
    sample_pics = read_samples()
    # img_data = [base64.b64decode(x.get('IMAGE')) for x in samples]
    # folder = sg.PopupGetFolder('Select a folder with images')
    left_column = [
        [sg.Text('Select a folder with image files'), sg.Input('', key = 'FOLDER', enable_events=True, visible=False), sg.FolderBrowse('Browse', target='FOLDER')],
        [sg.Output(size = (60,20))],
        [sg.ProgressBar(100, size = (40,8), key = 'BAR')],
        [sg.Text('No tokens used so far', key = 'TOKENS')],
        [sg.Button('Batch'),
         sg.Button('Cancel'),
         sg.Button('Check connection', tooltip = 'Check if OpenAI key and connection are OK'),
         sg.Button('Update', visible=update_available, tooltip=release_notes)]
    ]
    
    right_column = [
        [sg.Text('Enter batch size'),sg.Input('5', key = 'BATCH', enable_events=True, size = (3,1), )],
        [sg.Text('Select samples'), sg.DropDown(presets, default_value = presets[0], key = 'SAMPLE_PICS', enable_events=True)],
        [sg.Button('Create new samples')],
        [sg.vbottom(sg.Text(f'{version_number}', relief = 'sunken'))]
        ]
    layout = [[sg.Column(left_column),sg.VerticalSeparator(),sg.vtop(sg.Column(right_column))]]

    window = sg.Window(title = 'Image keyword generator', layout = layout)
    increment = 0
    
    while True:
        event,values = window.read()
        
        if event in ('Cancel', sg.WINDOW_CLOSED):
            break
        elif event == 'Check connection':
            print(test_openai_api(client))

        elif event == 'Update':
            update()
        # elif event == 'OK':
        #     window.start_thread(lambda: main(window = window), 'FINISHED')
        elif event == 'Create new samples':
            samples_window()
        elif event == 'SAMPLE_PICS':
            sample_file = values['SAMPLE_PICS']
            sample_pics = read_samples(sample_file+'.json')
        elif event == 'BATCH' and values['BATCH'] != '':
            try:
                BATCH_SIZE = int(values['BATCH'])
            except:
                sg.PopupError('Batch size should be an integer')
        elif event == 'FOLDER':
            folder = values['FOLDER']
            files = get_image_paths(folder)
            print(f'There are {len(files)} image files in the selected folder')
        elif event == 'Batch':
            BATCH_SIZE = int(values['BATCH'])
            folder = values['FOLDER']
            if folder != '':
                modified_folder = os.path.join(folder,'modified')
                try:
                    os.makedirs(modified_folder)
                except:
                    pass
                all_files = get_image_paths(folder)
                samples = [True if i % BATCH_SIZE == 0 else False for i,x in enumerate(all_files)]
                if len(all_files) > 0:
                    progress = 100/len(all_files)
                    print(f"Please wait, working on {BATCH_SIZE} files at a time\n")
                    window.start_thread(lambda: launch_main(), 'FINISHED_BATCH')
                else:
                    progress = 100
                    print('There are no image files in the selected folder')
            else:
                print('Please select a folder first')

        elif event == 'PROGRESS':
            increment += progress
            window['BAR'].update(increment)
            window['TOKENS'].update(f'Total tokens used: {tokens_used}. Estimated cost: ${(input_tokens * 10 / 1000000) + (output_tokens * 30 / 1000000):.3f}')
        # elif event == 'RESULTS':
        #     results = values['RESULTS']
        #     if isinstance(results, pd.core.frame.DataFrame):
        #         export_to_excel(results)
        #         print('Results saved')
        elif event == 'FINISHED_BATCH_FUNCTION':
            print('All done')
            print(f'{len(success_files)} tagged successfully\n{len(failed_files)} failed')
            if len(failed_files) > 0:
                print('Failed files:')
                print('\n'.join(failed_files))
    client.close()
    window.close()
    
    return None

if __name__ == '__main__':
    try:
        main_window()
    except Exception as e:
        logger.error('\n\n', e)
        logger.exception('Traceback: \n')
