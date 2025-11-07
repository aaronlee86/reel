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
        query_template = 'SELECT * FROM questions WHERE part = ? AND level = ? AND used_xid = 0'
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
        ValueError: If inputs are of mixed types
    """

    # Mapping table: (accent, sex) -> [(engine, voice), ...]
    tts_mapping = {
        ('am', 'man'): [('google', 'am-man1'), ('aws', 'am-man2')],
        ('am', 'woman'): [('google', 'am-woman1'), ('aws', 'am-woman2')],
        ('cn', 'man'): [('google', 'cn-man1'), ('aws', 'cn-man2')],
        ('cn', 'woman'): [('google', 'cn-woman1'), ('aws', 'cn-woman2')],
        ('br', 'man'): [('google', 'br-man1'), ('aws', 'br-man2')],
        ('br', 'woman'): [('google', 'br-woman1'), ('aws', 'br-woman2')],
        ('au', 'man'): [('google', 'au-man1'), ('aws', 'au-man2')],
        ('au', 'woman'): [('google', 'au-woman1'), ('aws', 'au-woman2')],
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

        # Track unique combinations to ensure consistent engine/voice
        unique_combinations = {}

        # Process each combination
        for accent, sex in zip(accents, sexes):
            # Sanity check
            if not accent or not sex:
                raise ValueError(f"Invalid accent or sex: accent={accent}, sex={sex}")

            # Look up in mapping
            key = (accent, sex)
            if key not in tts_mapping:
                raise KeyError(f"No TTS settings found for accent='{accent}', sex='{sex}'")

            # Check if this combination has been seen before
            if key in unique_combinations:
                # Use previously selected engine and voice
                engines.append(unique_combinations[key][0])
                voices.append(unique_combinations[key][1])
            else:
                # Get matching options and randomly choose
                options = tts_mapping[key]
                engine, voice = random.choice(options)

                # Store for future consistent selection
                unique_combinations[key] = (engine, voice)

                engines.append(engine)
                voices.append(voice)

        return engines, voices

    else:
        # Mixed input types
        raise ValueError("Inputs must be either both lists or both strings")