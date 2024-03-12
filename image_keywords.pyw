# -*- coding: utf-8 -*-
"""
Created on Mon Mar  4 15:53:40 2024

@author: Sergey
"""

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

load_dotenv()
API_KEY = os.getenv('API_KEY')
BATCH_SIZE = 5

with open('instructions.txt','r') as instr:
    INSTRUCTIONS = instr.read()

INSTRUCTIONS = 'Observe the following guidelines:\n' + INSTRUCTIONS
PROMPT = '''Describe the images below. Make sure to strictly follow the pattern in previous examples, avoid adding anything except titles, descriptions and keywords.
For titles, make sure to capitalize only the first letter of the sentence.
Remove all articles from the output content ("a", "an", "the" must be removed).
Pay specific attention to keywords - there must be between 45 and 49 of them, all single-word, do not use plurals.
The order of keywords matters - the first 10 keywords must be the most important and relevant ones, all keywords sorted in descending order by relevance'''

def update():
    repo_url = "https://raw.githubusercontent.com/misunders2d/image_keywords/master/image_keywords.pyw"
    response = requests.get(repo_url)
    if response.status_code == 200:
        remote_script = response.text

        # Read the current script file
        with open(__file__, 'r') as file:
            current_script = file.read()

        if current_script != remote_script:
            # If they are different, update the current script
            answer = sg.PopupYesNo('There is an update available\nDo you want to update?')
            if answer == "Yes":
                with open(__file__, 'w') as file:
                    file.write(remote_script)
                print("Script updated. Please restart the application.")
                os.exit()
    print(response.status_code)


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
    resized_file = resize_image('C:\\temp\\pics\\New folder (3)\\Key\\фото\\myphoto01.jpg')
    bytes_file = convert_image_to_bytes(resized_file)
    encoded_file = encode_image(bytes_file)
    samples.extend([{
        "IMAGE":f"{encoded_file}",
        "TITLE":"Two vases with flowers",
        "DESCRIPTION":"Two vases with flowers on mint green background with copy space",
        "KEYS":"modern, vase, flower, background, minimalist, decor, interior, spring, floral, elegant, design, copy space, simple, contemporary, mint, decoration, green, botanical, orange, white, home, bloom, fashion, clean, bright, fresh, stylish, ceramics, trendy, beauty, creative, color, nature, studio, soft, pastel, minimalistic, simplicity, decorative"}])
    
    resized_file = resize_image('C:\\temp\\pics\\New folder (3)\\Key\\фото\\myphoto02.jpg')
    bytes_file = convert_image_to_bytes(resized_file)
    encoded_file = encode_image(bytes_file)
    samples.extend([{
        "IMAGE":f"{encoded_file}",
        "TITLE":"Paper cards background",
        "DESCRIPTION":"Handmade paper with torn edges. Chaotic paper cards background",
        "KEYS":"paper, background, torn, edge, texture, natural, handmade, organic, abstract, collage, art, craft, design, material, creative, variety, pattern, decoration, scrapbooking, artistic, rustic, detail, diy, mixed, pastel, colorful, aged, piece, scrap, recycle, chaotic, textured, layered, vintage, color, rough, decorative, wall, surface, unique, card, muted, faded, pale, grunge, tag, raw, patchwork, tone"}])

    resized_file = resize_image('C:\\temp\\pics\\New folder (3)\\Key\\фото\\myphoto03.jpg')
    bytes_file = convert_image_to_bytes(resized_file)
    encoded_file = encode_image(bytes_file)
    samples.extend([{
        "IMAGE":f"{encoded_file}",
        "TITLE":"Easter flowers on white background",
        "DESCRIPTION":"Stylized Easter flowers in colorful and artistic springtime on white background. Easter Card. Clipart bundle, hand drawn set",
        "KEYS":"Easter, flower, floral, pattern, nature, colorful, decoration, artistic, stylized, illustration, springtime, vibrant, celebration, holiday, cheerful, festive, bright, design, creative, blooming, tradition, garden, display, ornamental, decorative, beautiful, egg, set, element, isolated, tinycore, folk, white, background, plant, art, clipart, bundle, card, drawing, hand, drawn, greeting, paint, collection, painting, doodle, abstract, decor"}])

    resized_file = resize_image('C:\\temp\\pics\\New folder (3)\\Key\\фото\\myphoto04.jpg')
    bytes_file = convert_image_to_bytes(resized_file)
    encoded_file = encode_image(bytes_file)
    samples.extend([{
        "IMAGE":f"{encoded_file}",
        "TITLE":"Smiling man with bouquet of wrenches and screwdrivers",
        "DESCRIPTION":"Smiling happy bearded man with bouquet of wrenches, spanners and screwdrivers with copy space",
        "KEYS":"man, wrench, tool, bouquet, smiling, gift, copy space, screwdriver, happy, smile, surprise, spanner, mechanic, construction, work, metal, equipment, screw, industrial, fix, detail, steel, industry, set, repair, instrument, kit, mechanical, professional, handyman, worker, repairman, bearded, male, hand, creative, car, auto, shop, workshop, holding, engineer, service, maintenance, diy, handmade, father, day, card"}])

    resized_file = resize_image('C:\\temp\\pics\\New folder (3)\\Key\\фото\\myphoto05.jpg')
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

def get_samples():
    query = "Describe this image. Save the result in json format where 'xp_title' is the title of the image, 'xp_subject' is the image description and 'xp_keywords' are the keywords"
    with open('samples.json','r') as file:
        samples = json.load(file)
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

def export_to_excel(df):
    export_path = sg.PopupGetFolder('Select folder to save excel file with results')
    try:
        with pd.ExcelWriter(os.path.join(export_path, 'results.xlsx'), engine = 'xlsxwriter') as writer:
            df.to_excel(writer, sheet_name = 'Images with description', index = False)
    except PermissionError:
        sg.PopupError('Please close the file first')
        export_to_excel(df)
    return None

def resize_image(image_path):
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

def describe_image(image_bytes):
    messages = get_samples()
    
    client = OpenAI(api_key=API_KEY)

    new_prompt = [
        {"role": "user","content":
          [{"type": "text","text": PROMPT + '\n' + INSTRUCTIONS},
          {"type": "image_url","image_url":{"url": f"data:image/jpeg;base64,{image_bytes}"}}]
          }]
    
    messages.extend(new_prompt)
    
    response = client.chat.completions.create(
      model="gpt-4-vision-preview",
      messages = messages,
      max_tokens=300,
    )
    
    if response.choices[0].finish_reason == 'stop':
        description = response.choices[0].message.content
    else:
        description = 'There was an error, please try again.'
    return description

def main(folder = r'C:\temp\pics', *args, **kwargs):
    window = kwargs['window']
    # all_files = get_image_paths(folder)
    progress = 100/len(all_files)
    results = pd.DataFrame()
    for i,file in enumerate(all_files):
        print(f'reading file #{i+1} out of {len(all_files)}')
        resized_file = resize_image(file)
        bytes_file = convert_image_to_bytes(resized_file)
        encoded_file = encode_image(bytes_file)
        file_description = describe_image(encoded_file)
        try:
            data = json.loads(file_description)
            exif_dict = write_exif(file, data)
            initial_img = Image.open(file)
            new_file_name = os.path.splitext(file)[0] + '_modified' + os.path.splitext(file)[-1]
            initial_img.save(new_file_name, exif = exif_dict)
        except:
            pass
        temp_df = pd.DataFrame([[file, file_description]], columns = ['filename','description'])
        results = pd.concat([results, temp_df])
        time.sleep(1)
        window.write_event_value('PROGRESS', progress)
    window.write_event_value('RESULTS', results)
    return None

def batch_main(file):
    time.sleep(randint(10,50)/10)
    resized_file = resize_image(file)
    bytes_file = convert_image_to_bytes(resized_file)
    encoded_file = encode_image(bytes_file)
    file_description = describe_image(encoded_file)
    # file_description = None
    try:
        data = json.loads(file_description)
        exif_dict = write_exif(file, data)
        initial_img = Image.open(file)
        new_file_name = os.path.join(modified_folder, os.path.basename(file))
        # os.path.splitext(file)[0] + '_modified' + os.path.splitext(file)[-1]
        initial_img.save(new_file_name, exif = exif_dict)
        success_files.append(file)
        print(f'{file}:SUCCESS\n')
    except:
        failed_files.append(file)
        print(f'{file}:FAILED\n')
    window.write_event_value('PROGRESS', None)
    return None

def launch_main():
    with ThreadPoolExecutor(max_workers = BATCH_SIZE) as pool:
        pool.map(batch_main, all_files)
    window.write_event_value('FINISHED_BATCH_FUNCTION',None)
    return None

events = []
success_files = []
failed_files = []

def main_window():
    global window, all_files, modified_folder
    folder = sg.PopupGetFolder('Select a folder with images')
    modified_folder = os.path.join(folder,'modified')
    try:
        os.makedirs(modified_folder)
    except:
        pass
    all_files = get_image_paths(folder)
    layout = [
        [sg.Output(size = (40,10))],
        [sg.ProgressBar(100, size = (26,4), key = 'BAR')],
        [sg.Button('Batch'), sg.Button('Cancel'), sg.Button('Update')],
        ]
    
    window = sg.Window(title = 'Image keyword generator', layout = layout)
    increment = 0
    if len(all_files) > 0:
        progress = 100/len(all_files)
    else:
        progress = 100
    
    while True:
        event,values = window.read()
        events.append([event,values])
        
        if event in ('Cancel', sg.WINDOW_CLOSED):
            break
        elif event == 'Update':
            update()
        elif event == 'OK':
            window.start_thread(lambda: main(window = window), 'FINISHED')
        elif event == 'Batch':
            print("Please wait\n")
            window.start_thread(lambda: launch_main(), 'FINISHED_BATCH')           
        elif event == 'PROGRESS':
            increment += progress
            window['BAR'].update(increment)
        elif event == 'RESULTS':
            results = values['RESULTS']
            if isinstance(results, pd.core.frame.DataFrame):
                export_to_excel(results)
                print('Results saved')
        elif event == 'FINISHED_BATCH_FUNCTION':
            print('All done')
            print(f'{len(success_files)} tagged successfully\n{len(failed_files)} failed')
    
    window.close()
    
    return None

if __name__ == '__main__':
    main_window()