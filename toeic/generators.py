"""
Example generator classes for the CSV Template Processor.
These demonstrate simple string returns and complex JSON returns.
"""
from datetime import datetime
import sqlite3
import random
import json

def parse_or_string(s):
    try:
        value = json.loads(s)
        # If it's a list, return it directly
        if isinstance(value, list):
            return value
        # Otherwise, convert to string
        return str(value)
    except json.JSONDecodeError:
        # If not valid JSON, return as-is
        return s

class loadToeicSql:
    def __init__(self, part, level, dbPath, **args):
        # Connect to database (creates it if it doesn't exist)
        self.part = int(part)
        self.level = int(level)
        self.conn = sqlite3.connect(dbPath)
        self.conn.row_factory = sqlite3.Row

        # parse sex and accent dicts
        sex, accent = args.get('sex', '{}'), args.get('accent', '{}')
        dict_sex, dict_accent = eval(sex), eval(accent)
        self.sex, self.sex_weight = list(dict_sex.keys()), list(dict_sex.values())
        self.accent, self.accent_weight = list(dict_accent.keys()), list(dict_accent.values())

    def run(self):
        cursor = self.conn.cursor()
        query_template = 'SELECT * FROM questions WHERE part = ? AND level = ? AND used = 0'
        params = (self.part, self.level)
        try:
            # apply values to query
            cursor.execute(query_template, params)
            result = dict(cursor.fetchone())  # Get one row
        except Exception as e:
            final_query = query_template.replace('?', '{}').format(*params)
            print(f"No matching found: {final_query}")
            return None
        finally:
            cursor.close()

        # Take accent and sex to add tts.engine and tts.voice
        result['tts'] = {}
        # if accent or sex is None, randomly choose one from the available options
        if not result.get('accent'):
            result['accent'] = random.choices(self.accent, weights=self.accent_weight, k=1)[0]
        if not result.get('sex'):
            result['sex'] = random.choices(self.sex, weights=self.sex_weight, k=1)[0]

        for key in ['prompt','question','A','B','C','D','answer','accent','sex']:
            if result.get(key):
                result[key] = parse_or_string(result[key])

        try:
            result['tts']['engine'], result['tts']['voice'] = getTtsSettings(result['accent'], result['sex'])
            print(f"voice: {result['tts']['voice']} and type: {type(result['tts']['voice'])}")
        except Exception as e:
            print(f"Error getting TTS settings from sex: {result['sex']} and accent: {result['accent']}: {e}")
            return None


        # DEBUG: print each element and type of result
        # for key, value in result.items():
        #    print(f"{key}: {value} (type: {type(value)})")

        # update the question as used
        try:
            update_query = 'UPDATE questions SET used=1 WHERE id=?'
            cursor = self.conn.cursor()
            #cursor.execute(update_query, (result['id'],))
            #self.conn.commit()
        except Exception as e:
            print(f"Error updating question as used: {e}")
            return None
        finally:
            cursor.close()

        return result

    # descturctor to close db connection
    def __del__(self):
        if self.conn:
            print("Closing database connection.")
            self.conn.close()


def getTtsSettings(accents, sexes):
    """
    Look up TTS settings by lists of accents and sexes or single accent and sex.

    Args:
        accents (list or str): List of accent codes or single accent code
        sexes (list or str): List of sex identifiers or single sex identifier

    Returns:
        - If inputs are lists: Tuple of two lists (engines, voices)
        - If inputs are strings: Tuple of two strings (engine, voice)

    Raises:
        ValueError: If inputs are of mixed types (one list, one string)
    """

    # Mapping table: (accent, sex) -> [(engine, voice), ...]
    tts_mapping = {
        ('am', 'man'): [('google', 'en-US-Neural2-C'), ('aws', 'Matthew')],
        ('am', 'woman'): [('google', 'en-US-Neural2-E'), ('aws', 'Joanna')],
        ('cn', 'man'): [('google', 'zh-CN-Neural2-A'), ('aws', 'Zhiyu')],
        ('cn', 'woman'): [('google', 'zh-CN-Neural2-C'), ('aws', 'Zhiyu')],
        ('br', 'man'): [('google', 'pt-BR-Neural2-B'), ('aws', 'Vitoria')],
        ('br', 'woman'): [('google', 'pt-BR-Neural2-A'), ('aws', 'Vitoria')],
        ('au', 'man'): [('google', 'en-AU-Neural2-B'), ('aws', 'Russell')],
        ('au', 'woman'): [('google', 'en-AU-Neural2-D'), ('aws', 'Nicole')],
    }

    # Check input types
    if isinstance(accents, str) and isinstance(sexes, str):
        # Single string inputs
        accent = accents.lower().strip()
        sex = sexes.lower().strip()

        # Sanity check
        if not accent or not sex:
            raise ValueError(f"Invalid accent or sex: accent={accent}, sex={sex}")

        # Look up in mapping
        key = (accent, sex)
        if key not in tts_mapping:
            raise KeyError(f"No TTS settings found for accent='{accent}', sex='{sex}'")

        # Randomly choose from options
        return random.choice(tts_mapping[key])

    elif isinstance(accents, list) and isinstance(sexes, list):
        # List inputs
        if not accents or not sexes or len(accents) != len(sexes):
            raise ValueError("Accents and sexes must be non-empty lists of equal length")

        # Normalize inputs
        accents = [str(accent).lower().strip() for accent in accents]
        sexes = [str(sex).lower().strip() for sex in sexes]

        # Result storage
        engines = []
        voices = []

        # Process each combination
        for accent, sex in zip(accents, sexes):
            # Sanity check
            if not accent or not sex:
                raise ValueError(f"Invalid accent or sex: accent={accent}, sex={sex}")

            # Look up in mapping
            key = (accent, sex)
            if key not in tts_mapping:
                raise KeyError(f"No TTS settings found for accent='{accent}', sex='{sex}'")

            # Get matching options
            options = tts_mapping[key]

            # Randomly choose if multiple matches
            engine, voice = random.choice(options)

            # Append to result lists
            engines.append(engine)
            voices.append(voice)

        return engines, voices

    else:
        # Mixed input types
        raise ValueError("Inputs must be either both lists or both strings")