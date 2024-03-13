# -*- coding: utf-8 -*-
"""
Created on Mon Mar  4 15:53:40 2024

@author: Sergey
"""

import subprocess

import PySimpleGUI as sg
from openai import OpenAI
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
BATCH_SIZE = 5

with open('instructions.txt','r') as instr:
    INSTRUCTIONS = instr.read()

INSTRUCTIONS = 'Observe the following guidelines:\n' + INSTRUCTIONS

with open('prompt.txt','r') as p:
    PROMPT = p.read()

def update_dependencies():
    subprocess.call(['pip', 'install', '-r', 'requirements.txt'])

def update():
    import difflib
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
            # If they are different, update the current script
            answer = sg.PopupYesNo('There is an update available\nDo you want to update?')
            if answer == "Yes":
                with open(__file__, 'w', encoding = 'utf-8') as file:
                    file.write(remote_script)
                with open('requirements.txt','w') as req_file:
                    req_file.write(remote_req)
                update_dependencies()
                print("Script updated. Please restart the application.")
        else:
            print('No updates found')

def write_exif(image, data):
    title = data.get('xp_title')
    description = data.get('xp_subject')
    keys = '; '.join(data.get('xp_keywords'))
    
    exif_dict = piexif.load(image)
    
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
    
    return exif_bytes

def create_samples():
    samples = []
    resized_file = resize_image(r'C:\temp\pics\New folder (3)\Key\myphoto01.jpg')
    bytes_file = convert_image_to_bytes(resized_file)
    encoded_file = encode_image(bytes_file)
    samples.extend([{
        "IMAGE":f"{encoded_file}",
        "TITLE":"Two vases with flowers",
        "DESCRIPTION":"Two vases with flowers on mint green background with copy space",
        "KEYS":"modern, vase, flower, background, minimalist, decor, interior, spring, floral, elegant, design, copy space, simple, contemporary, mint, decoration, green, botanical, orange, white, home, bloom, fashion, clean, bright, fresh, stylish, ceramics, trendy, beauty, creative, color, nature, studio, soft, pastel, minimalistic, simplicity, decorative"}])
    
    resized_file = resize_image(r'C:\temp\pics\New folder (3)\Key\myphoto02.jpg')
    bytes_file = convert_image_to_bytes(resized_file)
    encoded_file = encode_image(bytes_file)
    samples.extend([{
        "IMAGE":f"{encoded_file}",
        "TITLE":"Paper cards background",
        "DESCRIPTION":"Handmade paper with torn edges. Chaotic paper cards background",
        "KEYS":"paper, background, torn, edge, texture, natural, handmade, organic, abstract, collage, art, craft, design, material, creative, variety, pattern, decoration, scrapbooking, artistic, rustic, detail, diy, mixed, pastel, colorful, aged, piece, scrap, recycle, chaotic, textured, layered, vintage, color, rough, decorative, wall, surface, unique, card, muted, faded, pale, grunge, tag, raw, patchwork, tone"}])

    resized_file = resize_image(r'C:\temp\pics\New folder (3)\Key\myphoto03.jpg')
    bytes_file = convert_image_to_bytes(resized_file)
    encoded_file = encode_image(bytes_file)
    samples.extend([{
        "IMAGE":f"{encoded_file}",
        "TITLE":"Easter flowers on white background",
        "DESCRIPTION":"Stylized Easter flowers in colorful and artistic springtime on white background. Easter Card. Clipart bundle, hand drawn set",
        "KEYS":"Easter, flower, floral, pattern, nature, colorful, decoration, artistic, stylized, illustration, springtime, vibrant, celebration, holiday, cheerful, festive, bright, design, creative, blooming, tradition, garden, display, ornamental, decorative, beautiful, egg, set, element, isolated, tinycore, folk, white, background, plant, art, clipart, bundle, card, drawing, hand, drawn, greeting, paint, collection, painting, doodle, abstract, decor"}])

    resized_file = resize_image(r'C:\temp\pics\New folder (3)\Key\myphoto04.jpg')
    bytes_file = convert_image_to_bytes(resized_file)
    encoded_file = encode_image(bytes_file)
    samples.extend([{
        "IMAGE":f"{encoded_file}",
        "TITLE":"Smiling man with bouquet of wrenches and screwdrivers",
        "DESCRIPTION":"Smiling happy bearded man with bouquet of wrenches, spanners and screwdrivers with copy space",
        "KEYS":"man, wrench, tool, bouquet, smiling, gift, copy space, screwdriver, happy, smile, surprise, spanner, mechanic, construction, work, metal, equipment, screw, industrial, fix, detail, steel, industry, set, repair, instrument, kit, mechanical, professional, handyman, worker, repairman, bearded, male, hand, creative, car, auto, shop, workshop, holding, engineer, service, maintenance, diy, handmade, father, day, card"}])

    resized_file = resize_image(r'C:\temp\pics\New folder (3)\Key\myphoto05.jpg')
    bytes_file = convert_image_to_bytes(resized_file)
    encoded_file = encode_image(bytes_file)
    samples.extend([{
        "IMAGE":f"{encoded_file}",
        "TITLE":"Natural linen fabric texture. Flaxen circular spiral textile background",
        "DESCRIPTION":"Natural linen fabric texture. Flaxen circular spiral textile background, top view. Rough twisted burlap",
        "KEYS":"linen, fabric, texture, spiral, background, textile, burlap, natural, swirl, flaxen, flax, rough, material, canvas, backdrop, surface, textured, twist, closeup, fiber, crumpled, vintage, wallpaper, weave, grunge, soft, gray, beige, sack, woven, wave, rustic, sackcloth, crease, rumpled, weaving, wrinkled, top view, cotton, tablecloth, old, abstract, design, structure, twisted, fold, fashion, twirl, circular"}])

    with open('samples.json','w') as f:
        f.write(json.dumps(samples))
    return None

def get_samples(n_from = 2, n_to = 5):
    query = "Describe this image. Save the result in json format where 'xp_title' is the title of the image, 'xp_subject' is the image description and 'xp_keywords' are the keywords"
    with open('samples.json','r') as file:
        samples = json.load(file)
    samples = samples[n_from:n_to]
    messages = []
    for sample in samples:
        image = sample['IMAGE']
        title = sample['TITLE']
        description = sample['DESCRIPTION']
        keys = sample['KEYS']
        payload = json.dumps({"xp_title": title,"xp_subject": description,"xp_keywords":keys})
            
        msg = [
            {'role':'user','content':
             [{'type':'text','text':query},
              {'type':'image_url','image_url':{"url": f"data:image/jpeg;base64,{image}"}}]},
            # {'role':'assistant','content':f'Title: {title}\nDescription: {description}\nKeys: {keys}'}
            {'role':'assistant','content':f'{payload}'}
            ]
        messages.extend(msg)
    return messages

# def export_to_excel(df):
#     export_path = sg.PopupGetFolder('Select folder to save excel file with results')
#     try:
#         with pd.ExcelWriter(os.path.join(export_path, 'results.xlsx'), engine = 'xlsxwriter') as writer:
#             df.to_excel(writer, sheet_name = 'Images with description', index = False)
#     except PermissionError:
#         sg.PopupError('Please close the file first')
#         export_to_excel(df)
#     return None

def resize_image(image_path: str):
    full_image = Image.open(image_path)
    cropped_image = ImageOps.contain(full_image, (512,512))
    return cropped_image

def convert_image_to_bytes(image_obj):
    img_byte_arr = BytesIO()
    image_obj.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    return img_byte_arr

def encode_image(image_path):
    if isinstance(image_path, str):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    elif isinstance(image_path, bytes):
        return base64.b64encode(image_path).decode('utf-8')

def get_image_paths(folder):
    files = os.listdir(folder)
    files = [os.path.join(folder,x) for x in files if os.path.splitext(x)[-1].lower() in ('.png','.jpg')]
    return files

def describe_image(image_bytes, sample):
    global input_tokens, output_tokens
    time.sleep(randint(20,50)/10)
    if sample == True:
        messages = get_samples(2,5)
        FULL_PROMPT = PROMPT + '\n' + INSTRUCTIONS
    else:
        # messages = []
        messages = get_samples(3,4)
        FULL_PROMPT = PROMPT
    new_prompt = [
        {"role": "user","content":
          [{"type": "text","text": FULL_PROMPT},
          {"type": "image_url","image_url":{"url": f"data:image/jpeg;base64,{image_bytes}"}}]
          }]
    
    messages.extend(new_prompt)
    
    response = client.chat.completions.create(
      model="gpt-4-vision-preview",
      messages = messages,
      max_tokens=500,
    )
    
    stop = response.choices[0].finish_reason
    if stop == 'stop':
        description = response.choices[0].message.content
    else:
        print(stop)
        description = 'There was an error, please try again.'
    description = description.replace("```","").replace("json\n","")
    input_tokens += response.usage.prompt_tokens
    output_tokens += response.usage.completion_tokens
    
    return description, stop, response.usage.total_tokens, sample

def batch_main(filesample):
    global tokens_used
    file = filesample[0]
    sample = filesample[1]
    resized_file = resize_image(file)
    bytes_file = convert_image_to_bytes(resized_file)
    encoded_file = encode_image(bytes_file)
    file_description, stop, usage, sample = describe_image(encoded_file, sample)
    tokens_used += usage
    # file_description = sample = stop = None
    try:
        data = json.loads(file_description)
        exif_dict = write_exif(file, data)
        initial_img = Image.open(file)
        new_file_name = os.path.join(modified_folder, os.path.basename(file))
        initial_img.save(new_file_name, exif = exif_dict, quality = 'keep')
        success_files.append(file)
        print(f'{file}: SUCCESS (finish reason: {stop}. Samples used: {sample}))\n')
    except Exception as e:
        failed_files.append(file)
        print(f'{file}:FAILED (finish reason: {stop})\nModel response: {file_description}\n\n')
        logger.error('\n\n', e)
        logger.exception('Traceback: ')
    finally:
        window.write_event_value('PROGRESS', None)
    return None

def launch_main():
    with ThreadPoolExecutor() as pool:
        pool.map(batch_main, list(zip(all_files,samples)))
    window.write_event_value('FINISHED_BATCH_FUNCTION',None)
    return None

success_files = []
failed_files = []
tokens_used = 0
input_tokens = 0
output_tokens = 0

def main_window():
    global window, all_files, modified_folder, client, samples, BATCH_SIZE

    client = OpenAI(api_key=API_KEY)
    client.timeout.pool = 60
    client.timeout.read = 60
    client.timeout.write = 60

    # folder = sg.PopupGetFolder('Select a folder with images')
    left_column = [
        [sg.Text('Select a folder with image files'), sg.Input('', key = 'FOLDER', enable_events=True, visible=False), sg.FolderBrowse('Browse', target='FOLDER')],
        [sg.Output(size = (60,20))],
        [sg.ProgressBar(100, size = (40,8), key = 'BAR')],
        [sg.Text('No tokens used so far', key = 'TOKENS')],
        [sg.Button('Batch'), sg.Button('Cancel'), sg.Button('Update'), sg.Text('Version 1.0.9', justification='right', relief = 'sunken')]
    ]
    
    right_column = [[sg.Text('Enter batch size'),sg.Input('5', key = 'BATCH', enable_events=True, size = (3,1), )]]
    layout = [[sg.Column(left_column),sg.VerticalSeparator(),sg.vtop(sg.Column(right_column))]]

    window = sg.Window(title = 'Image keyword generator', layout = layout)
    increment = 0
    
    while True:
        event,values = window.read()
        
        if event in ('Cancel', sg.WINDOW_CLOSED):
            break
        elif event == 'Update':
            update()
        # elif event == 'OK':
        #     window.start_thread(lambda: main(window = window), 'FINISHED')
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
    client.close()
    window.close()
    
    return None

if __name__ == '__main__':
    try:
        main_window()
    except Exception as e:
        logger.error('\n\n', e)
        logger.exception('Traceback: \n')
