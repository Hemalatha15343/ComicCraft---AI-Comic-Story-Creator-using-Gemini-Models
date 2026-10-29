from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv
from fpdf import FPDF

import os
import re
import requests
import uuid
import time


# ==================================================
# LOAD ENVIRONMENT VARIABLES
# ==================================================

load_dotenv()


# ==================================================
# FASTAPI APP
# ==================================================

app = FastAPI()


# ==================================================
# STATIC FILES
# ==================================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# ==================================================
# TEMPLATES
# ==================================================

templates = Jinja2Templates(
    directory="templates"
)


# ==================================================
# GENERATED FILES DIRECTORY
# ==================================================

os.makedirs(
    "static/generated",
    exist_ok=True
)


# ==================================================
# POLLINATIONS IMAGE GENERATION
# ==================================================

def generate_image(prompt):

    api_key = os.getenv("POLLINATIONS_API_KEY")

    if not api_key:
        print("Pollinations API key not found.")
        return None

    url = (
        "https://gen.pollinations.ai/image/"
        + requests.utils.quote(prompt, safe="")
    )

    for attempt in range(3):

        try:

            print(
                f"Pollinations image attempt "
                f"{attempt + 1}/3..."
            )

            response = requests.get(
                url,
                params={
                    "model": "flux",
                    "width": 1024,
                    "height": 768
                },
                headers={
                    "Authorization":
                        f"Bearer {api_key}"
                },
                timeout=180
            )

            if response.status_code == 200:

                filename = (
                    f"comic_{uuid.uuid4().hex}.jpg"
                )

                filepath = os.path.join(
                    "static",
                    "generated",
                    filename
                )

                with open(
                    filepath,
                    "wb"
                ) as file:

                    file.write(
                        response.content
                    )

                print(
                    "Image saved:",
                    filepath
                )

                return (
                    f"/static/generated/{filename}"
                )

            print(
                "Pollinations error:",
                response.status_code
            )

            print(
                response.text[:500]
            )

        except requests.exceptions.RequestException as error:

            print(
                f"Pollinations connection error "
                f"(attempt {attempt + 1}):",
                error
            )

        except Exception as error:

            print(
                f"Image generation error "
                f"(attempt {attempt + 1}):",
                error
            )

        if attempt < 2:
            time.sleep(5)

    print(
        "Pollinations image generation failed."
    )

    return None


# ==================================================
# REQUEST MODEL
# ==================================================

class ComicRequest(BaseModel):

    prompt: str
    character: str
    setting: str
    tone: str
    art_style: str


# ==================================================
# HOME PAGE
# ==================================================

@app.get("/")
def home(request: Request):

    return templates.TemplateResponse(
        request,
        "index.html"
    )


# ==================================================
# GENERATE COMIC
# ==================================================

@app.post("/generate")
def generate_comic(
    data: ComicRequest
):

    # ==================================================
    # STORY PROMPT
    # ==================================================

    prompt = f"""
Create an original 6-panel comic story.

Comic Idea:
{data.prompt}

Main Character:
{data.character}

Setting:
{data.setting}

Story Tone:
{data.tone}

Art Style:
{data.art_style}

The story MUST have a clear beginning,
middle and ending.

IMPORTANT:
Every panel must describe a DIFFERENT moment
of the story.

Do not repeat the same scene.

Return EXACTLY this format:

TITLE:
[comic title]

INTRO:
[2-3 sentence introduction]

CHARACTER:
[main character description]

PANEL 1:
SCENE: [detailed visual description of the first event]
STORY: [1-2 sentences describing what happens]
DIALOGUE: [short dialogue]

PANEL 2:
SCENE: [different visual scene and action]
STORY: [1-2 sentences describing what happens]
DIALOGUE: [short dialogue]

PANEL 3:
SCENE: [different visual scene and action]
STORY: [1-2 sentences describing what happens]
DIALOGUE: [short dialogue]

PANEL 4:
SCENE: [different visual scene and action]
STORY: [1-2 sentences describing what happens]
DIALOGUE: [short dialogue]

PANEL 5:
SCENE: [different visual scene and action]
STORY: [1-2 sentences describing what happens]
DIALOGUE: [short dialogue]

PANEL 6:
SCENE: [different final visual scene and action]
STORY: [1-2 sentences describing what happens]
DIALOGUE: [short dialogue]

ENDING:
[short ending]

Make the story creative, family-friendly
and suitable for a visual comic creator.

Make every panel visually different.
"""


    # ==================================================
    # OPENROUTER STORY GENERATION
    # ==================================================

    story = None

    try:

        print(
            "OpenRouter story generation started..."
        )

        openrouter_key = os.getenv(
            "OPENROUTER_API_KEY"
        )

        if not openrouter_key:

            return {
                "success": False,
                "message":
                    "OpenRouter API key not found."
            }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization":
                    f"Bearer {openrouter_key}",
                "Content-Type":
                    "application/json"
            },
            json={
                "model":
                    "openrouter/free",

                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },

            timeout=120
        )

        print(
            "OpenRouter status:",
            response.status_code
        )

        if response.status_code == 200:

            result = response.json()

            story = (
                result["choices"][0]
                ["message"]["content"]
            )

            print(
                "OpenRouter story generated successfully."
            )

        else:

            print(
                "OpenRouter error:",
                response.text[:1000]
            )

    except Exception as error:

        print(
            "OpenRouter generation error:",
            error
        )


    if not story:

        return {
            "success": False,
            "message":
                "OpenRouter could not generate "
                "the story. Please try again."
        }


    # ==================================================
    # EXTRACT PANELS
    # ==================================================

    panels = []


    for i in range(1, 7):

        pattern = (
            rf"PANEL {i}:"
            r"\s*SCENE:\s*(.*?)"
            r"\s*STORY:\s*(.*?)"
            r"\s*DIALOGUE:\s*(.*?)"
            rf"(?=\s*PANEL {i + 1}:"
            r"|\s*ENDING:|$)"
        )

        match = re.search(
            pattern,
            story,
            re.DOTALL | re.IGNORECASE
        )


        if match:

            panels.append({

                "number": i,

                "scene":
                    match.group(1).strip(),

                "story":
                    match.group(2).strip(),

                "dialogue":
                    match.group(3).strip(),

                "image_url":
                    None

            })

        else:

            panels.append({

                "number": i,

                "scene":
                    f"Scene {i} of the comic story.",

                "story":
                    "The adventure continues.",

                "dialogue":
                    "...",

                "image_url":
                    None

            })


    # ==================================================
    # GENERATE DIFFERENT IMAGE FOR EACH PANEL
    # ==================================================

    camera_styles = [

        "wide establishing shot",

        "medium character shot",

        "dynamic action shot",

        "dramatic close-up",

        "over-the-shoulder cinematic shot",

        "wide heroic final shot"

    ]


    for panel in panels:

        number = panel["number"]

        camera = camera_styles[number - 1]


        image_prompt = f"""
Create ONE single illustration for comic panel {number}.

This is panel {number} of a 6-panel story.
It must show a DIFFERENT moment from the previous
and next panels.

PANEL ACTION:

{panel["scene"]}

STORY MOMENT:

{panel["story"]}

MAIN CHARACTER:

{data.character}

SETTING:

{data.setting}

VISUAL STYLE:

{data.art_style}

STORY TONE:

{data.tone}

CAMERA:

{camera}

IMPORTANT:

- Create one single comic illustration.
- Do NOT create a comic page.
- Do NOT create multiple panels.
- Do NOT repeat a previous scene.
- Show the specific action described above.
- Change the character's pose according to the action.
- Change the background according to the scene.
- Use different composition for this panel.
- Keep the main character visually consistent.
- Make the character clearly visible.
- Use colorful detailed comic artwork.
- Family-friendly.
- No speech bubbles.
- No dialogue text.
- No captions.
- No written words.
- The website will add the story text separately.
"""


        print(
            f"Generating unique image "
            f"for Panel {number}..."
        )


        panel["image_url"] = generate_image(
            image_prompt
        )


        print(
            f"Panel {number} completed."
        )


    # ==================================================
    # IMAGE RESULT
    # ==================================================

    successful_images = sum(
        1
        for panel in panels
        if panel["image_url"]
    )


    print(
        f"Images generated: "
        f"{successful_images}/6"
    )


    # ==================================================
    # RETURN RESULT
    # ==================================================

    return {

        "success": True,

        "story": story,

        "panels": panels,

        "image_warning":
            successful_images < 6

    }


# ==================================================
# DOWNLOAD PDF
# ==================================================

@app.post("/download-pdf")
def download_pdf(data: dict):

    panels = data.get(
        "panels",
        []
    )


    if not panels:

        return {

            "success": False,

            "message":
                "No comic panels available."

        }


    pdf = FPDF()

    pdf.set_auto_page_break(
        auto=True,
        margin=15
    )


    # ==================================================
    # FONT
    # ==================================================

    font_regular = (
        "C:/Windows/Fonts/arial.ttf"
    )

    font_bold = (
        "C:/Windows/Fonts/arialbd.ttf"
    )


    if (
        os.path.exists(font_regular)
        and
        os.path.exists(font_bold)
    ):

        pdf.add_font(
            "ArialCustom",
            "",
            font_regular
        )

        pdf.add_font(
            "ArialCustom",
            "B",
            font_bold
        )

        font_name = "ArialCustom"

    else:

        font_name = "Helvetica"


    # ==================================================
    # TITLE PAGE
    # ==================================================

    pdf.add_page()


    pdf.set_font(
        font_name,
        "B",
        24
    )


    pdf.cell(
        0,
        15,
        "ComicCraft - AI Comic Story",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C"
    )


    pdf.ln(8)


    pdf.set_font(
        font_name,
        "",
        12
    )


    pdf.multi_cell(
        0,
        8,
        "AI-generated comic story and illustrations."
    )


    # ==================================================
    # PANELS
    # ==================================================

    for panel in panels:

        pdf.add_page()


        number = panel.get(
            "number",
            ""
        )

        scene = panel.get(
            "scene",
            ""
        )

        story_text = panel.get(
            "story",
            ""
        )

        dialogue = panel.get(
            "dialogue",
            ""
        )

        image_url = panel.get(
            "image_url"
        )


        # Panel heading

        pdf.set_font(
            font_name,
            "B",
            18
        )


        pdf.cell(
            0,
            10,
            f"Panel {number}",
            new_x="LMARGIN",
            new_y="NEXT"
        )


        pdf.ln(3)


        # Image

        if image_url:

            image_path = image_url.replace(
                "/static/",
                "static/",
                1
            )


            if os.path.exists(image_path):

                try:

                    pdf.image(
                        image_path,
                        x=15,
                        w=180
                    )

                    pdf.ln(8)

                except Exception as error:

                    print(
                        "PDF image error:",
                        error
                    )


        # Story

        pdf.set_font(
            font_name,
            "B",
            12
        )


        pdf.cell(
            0,
            8,
            "Story:",
            new_x="LMARGIN",
            new_y="NEXT"
        )


        pdf.set_font(
            font_name,
            "",
            11
        )


        pdf.multi_cell(
            0,
            7,
            story_text
        )


        pdf.ln(4)


        # Dialogue

        pdf.set_font(
            font_name,
            "B",
            12
        )


        pdf.cell(
            0,
            8,
            "Dialogue:",
            new_x="LMARGIN",
            new_y="NEXT"
        )


        pdf.set_font(
            font_name,
            "",
            11
        )


        pdf.multi_cell(
            0,
            7,
            dialogue
        )


    # ==================================================
    # SAVE PDF
    # ==================================================

    filename = (
        f"ComicCraft_{uuid.uuid4().hex}.pdf"
    )


    filepath = os.path.join(
        "static",
        "generated",
        filename
    )


    pdf.output(
        filepath
    )


    print(
        "PDF created:",
        filepath
    )


    return {

        "success": True,

        "pdf_url":
            f"/static/generated/{filename}"

    }