from openai import OpenAI, RateLimitError, NotFoundError
import os, json, time
from io import BytesIO
import base64
import piexif
import threading
from PIL import Image, ImageOps
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('API_KEY')
VISION_MODEL = "gpt-4o"#"gpt-4-turbo-2024-04-09" # "gpt-4-vision-preview" "gpt-4-turbo-2024-04-09" - new version
ASSISTANT_ID = 'asst_zwOvUO84dbtWqCHwUD0pY5Ho'
version_number = 'Version 2.0.1'
release_notes = 'Switched to GPT-4o'

client = OpenAI(api_key=API_KEY)

folder = r'C:\temp\pics\kw'
modified_folder = os.path.join(folder,'modified')
try:
    os.makedirs(modified_folder)
except FileExistsError:
    pass

try:
    with open('prompt.txt','r', encoding='utf-8') as p:
        PROMPT = p.read()
except UnicodeDecodeError:
    with open('prompt.txt','r', encoding='cp1251') as p:
        PROMPT = p.read()


file_paths = [os.path.join(folder, x) for x in os.listdir(folder) if os.path.isfile(os.path.join(folder,x))]
file_paths = file_paths[-3:]

def resize_image(image_path: str):
    full_image = Image.open(image_path)
    resized_image = ImageOps.contain(full_image, (512,512))
    return resized_image

def convert_image_to_bytes(image_obj):
    img_byte_arr = BytesIO()
    image_obj.save(img_byte_arr, format='jpeg')
    img_byte_arr = img_byte_arr.getvalue()
    return img_byte_arr

def upload_files(file_paths: list) -> list:
    file_ids = []
    for file_path in file_paths:
        print(f'Uploading {os.path.basename(file_path)} to Assistant')
        resized_image = resize_image(file_path)
        img_bytes = convert_image_to_bytes(resized_image)
        uploaded_file = client.files.create(
            file = (os.path.basename(file_path),img_bytes),
            purpose = 'vision')
        file_ids.append((uploaded_file.id, uploaded_file.filename))
    return file_ids

def batch_describe_files(file_ids):
    img_content = [
        {'type':'image_file','image_file':{'file_id':file_id[0]}}
        for file_id in file_ids]
    text_content = [
        {'type':'text','text':f'Do not use plurals in keywords. Return your response in JSON format where "key" is "{file_id[1]}", and "value" is the payload of your response.'}
        for file_id in file_ids]
    
    img_text = list(zip(img_content, text_content))
    
    thread = client.beta.threads.create()
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
        run = client.beta.threads.runs.create(
            thread_id = thread.id,
            assistant_id = ASSISTANT_ID,
            additional_instructions=PROMPT)
        current_status = client.beta.threads.runs.retrieve(run_id = run.id, thread_id = thread.id).status
        while current_status != 'completed':
            current_status = client.beta.threads.runs.retrieve(run_id = run.id, thread_id = thread.id).status
            print(f'Please wait, images processing: {current_status}')
            time.sleep(1)
    except Exception as e:
        print(f'{e}')
    return thread
        
def process_response(thread):   
    try:     
        messages = client.beta.threads.messages.list(thread.id)
        response = messages.data[0].content[0].text.value
    except:
        response = '''{"Image":"None"}'''
    response = response.replace('```','').replace('json\n','')
    response = json.loads(response)
    return response

def calculate_cost(thread):
    try:
        run_list = client.beta.threads.runs.list(thread_id = thread.id).data[0]
        input_tokens = run_list.usage.prompt_tokens
        output_tokens = run_list.usage.completion_tokens
        total_cost = (input_tokens * 5 / 1000000) + (output_tokens * 15 / 1000000)
    except:
        total_cost = -1
    return total_cost

def delete_thread(thread):
    try:
        client.beta.threads.delete(thread_id = thread.id)
    except NotFoundError:
        pass
    return None
    
def delete_files(file_ids):
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
        initial_img.save(new_file_name, exif = exif_bytes, quality = 'keep')
    return None

    


file_ids = upload_files(file_paths)
thread = batch_describe_files(file_ids)
response = process_response(thread)
total_cost = calculate_cost(thread)
print(f'Total cost is {total_cost} or {round(total_cost / len(file_ids),4)} per image')
apply_response(response)
delete_files(file_ids)
delete_thread(thread)
