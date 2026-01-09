# generateAudio.py

This script scans one or more CSV files in the same folder as `generateAudio.py`, extracts the text inside `<h1>` tags from each card side, generates MP3 audio using Google Translate text to speech, stores the MP3 files in a `Media` folder, and updates your CSV so Anki will play the audio on import.

It is designed to work on macOS, Linux, and Windows.

***

## What this script does

When you run `generateAudio.py` it will:

1. Create a `Media` subfolder if it does not already exist.
2. Find every `.csv` file in the same folder as the script.
3. For each row in each CSV:
   1. Read the first two columns as the two sides of an Anki note, front and back.
   2. Look for the first `<h1>...</h1>` on the front side and the first `<h1>...</h1>` on the back side.
   3. For each found `<h1>` text, generate an MP3 using Google text to speech.
   4. Save the MP3 into `Media`.
   5. Append a `[sound:filename.mp3]` tag to the end of each side so Anki will play that audio.
4. Create a backup of each CSV as `yourfile.csv.bak` before modifying it.

***

## Requirements

### Python
Python 3.8 or newer

Check your version:
```bash
python --version
```

### Internet access
The script uses Google text to speech through the `gTTS` library, so your machine must be online when you run it.

### Python libraries
The script requires these pip packages:

1. gTTS
2. beautifulsoup4
3. pykakasi

Install them:
```bash
python -m pip install gTTS beautifulsoup4 pykakasi
```

If anything is missing, the script will stop and print an exact command to install the missing library.

***

## Folder setup

Put everything in one folder like this:

```
YourFolder/
  generateAudio.py
  deck.csv
  another_deck.csv
```

You do not need to create `Media` yourself. The script will create it.

After running, you will have:

```
YourFolder/
  generateAudio.py
  deck.csv
  deck.csv.bak
  another_deck.csv
  another_deck.csv.bak
  Media/
    LLJ_Some_Title_ab12.mp3
    LLJ_Konnichiwa_cd34.mp3
```

***

## How to run

Open a terminal in the folder containing `generateAudio.py` and your CSV files.

### macOS and Linux
```bash
python3 generateAudio.py
```

### Windows
```bash
python generateAudio.py
```

You should see output that lists each CSV processed, how many rows were read, and how many MP3 files were created.

***

## CSV formatting requirements

### Core rules

Your CSV must follow these rules:

1. Each row represents one Anki note.
2. The first column is the front HTML.
3. The second column is the back HTML.
4. Each of those HTML fields must be a single CSV field, meaning it should be wrapped in quotes if it contains commas.
5. The script only looks for the first `<h1>...</h1>` on each side.
6. If a side does not contain an `<h1>`, no audio is generated for that side and nothing is appended for that side.

### What a row should look like

The simplest valid row looks like this:

```csv
"<h1>Hello</h1><p>Some extra HTML here</p>","<h1>こんにちは</h1><p>More HTML here</p>"
```

Front side `<h1>` text is `Hello`  
Back side `<h1>` text is `こんにちは`

The script will generate two MP3 files and then update the row to:

```csv
"<h1>Hello</h1><p>Some extra HTML here</p><br>[sound:LLJ_Hello_ab12.mp3]","<h1>こんにちは</h1><p>More HTML here</p><br>[sound:LLJ_konnichiwa_cd34.mp3]"
```

The exact filenames will differ because the script adds a random 4 character hex suffix.

### Extra columns are allowed

Your row can contain more than two columns. Only the first two are modified. Everything else is preserved.

Example with tags in column 3:

```csv
"<h1>Water</h1><p>Extra</p>","<h1>水</h1><p>Extra</p>","noun,common"
```

### Quotes and commas inside HTML

If your HTML contains commas, you must keep the field quoted. This is normal CSV behavior.

This is valid:

```csv
"<h1>Hello</h1><p>Comma example, still fine</p>","<h1>こんにちは</h1><p>Text</p>"
```

Do not manually escape commas. Just keep the field inside quotes.

### Existing sound tags

If a side already contains any `[sound:...]` tag anywhere in that field, the script will not append another one to that side.

This prevents duplicate audio tags if you run the script multiple times.

***

## Anki import instructions

1. Run the script so your CSV is updated and your MP3 files are created in the `Media` folder.
2. Open Anki.
3. Import the updated CSV:
   1. File → Import
   2. Choose your modified `.csv`
   3. Map fields: Field 1 to Front, Field 2 to Back
4. Copy the MP3 files into Anki’s media collection folder

Common locations for Anki media:

### macOS
`~/Library/Application Support/Anki2/<YourProfile>/collection.media`

### Windows
`%APPDATA%\Anki2\<YourProfile>\collection.media`

### Linux
`~/.local/share/Anki2/<YourProfile>/collection.media`

After the MP3 files are in `collection.media`, your cards will play audio automatically from the `[sound:...]` tag.

***

## Troubleshooting

### The script says a library is missing
Run the install command it prints, for example:
```bash
python -m pip install pykakasi
```

### MP3 generation fails
Common causes:

1. No internet access
2. A firewall or network policy blocking Google services
3. Temporary Google service issues

Try again on a different network.

### Nothing changes in my CSV
Common causes:

1. Your fields do not contain `<h1>` tags
2. Your `<h1>` tags are not inside the first two columns
3. A `[sound:...]` tag already exists in the field, so the script skips appending

### My CSV got messed up
A backup is created the first time the script runs:

`yourfile.csv.bak`

You can restore it by renaming:

1. Delete or move the modified `yourfile.csv`
2. Rename `yourfile.csv.bak` back to `yourfile.csv`

***

## How it works

1. The script parses each CSV row and treats column 1 and column 2 as HTML.
2. It uses BeautifulSoup to locate the first `<h1>` element and extracts its text.
3. It chooses Japanese or English text to speech based on whether the extracted text contains Japanese characters.
4. It generates MP3 audio using `gTTS` and saves the file in `Media` using a safe filename:
   1. Japanese characters are romanized using `pykakasi`
   2. A random 4 character hex suffix is added to prevent collisions
5. It appends a `<br>[sound:filename.mp3]` tag to the end of each HTML field so Anki will play the audio.

<footer style="text-align: center;">
    <a href="https://maximilianmcclelland.com" 
       style="text-decoration: none; 
              font-weight: bold;
              background: linear-gradient(to right, #ff75c3, #04befe);
              -webkit-background-clip: text;
              -webkit-text-fill-color: transparent;
              display: inline-block;">
        TrueProblematic © <span id="footer-year"></span>
    </a>
</footer>

