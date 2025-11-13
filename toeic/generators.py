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
    def __init__(self, xid, qno, part, level, dbPath, img, **args):
        # Connect to database (creates it if it doesn't exist)
        self.part = int(part)
        self.level = int(level)
        self.conn = sqlite3.connect(dbPath)
        self.conn.row_factory = sqlite3.Row
        self.xid = xid
        self.qno = qno
        self.img = True if img == '1' else False

        # parse sex and accent dicts
        sex, accent = args.get('sex', '{}'), args.get('accent', '{}')
        dict_sex, dict_accent = eval(sex), eval(accent)
        self.sex, self.sex_weight = list(dict_sex.keys()), list(dict_sex.values())
        self.accent, self.accent_weight = list(dict_accent.keys()), list(dict_accent.values())

    def run(self):
        cursor = self.conn.cursor()

        # First, check if a question already exists for this xid and qno
        check_query = 'SELECT * FROM questions WHERE used_xid = ? AND used_qno = ?'
        check_params = (self.xid, self.qno)

        try:
            cursor.execute(check_query, check_params)
            existing_result = cursor.fetchone()

            if existing_result:
                # Question already exists for this xid/qno, return it
                print(f"Found existing question for xid={self.xid}, qno={self.qno}")
                result = dict(existing_result)
            else:
                # No existing question, fetch a new unused one randomly
                if self.img:
                    query_template = 'SELECT * FROM questions WHERE part = ? AND level = ? AND valid = 1 AND used_xid IS NULL AND img IS NOT NULL ORDER BY RANDOM() LIMIT 1'
                else:
                    query_template = 'SELECT * FROM questions WHERE part = ? AND level = ? AND valid = 1 AND used_xid IS NULL AND img IS NULL ORDER BY RANDOM() LIMIT 1'
                params = (self.part, self.level)
                cursor.execute(query_template, params)
                fetched_result = cursor.fetchone()

                if not fetched_result:
                    final_query = query_template.replace('?', '{}').format(*params)
                    print(f"No matching found: {final_query}")
                    return None

                result = dict(fetched_result)

                # Mark the new question as used
                update_query = 'UPDATE questions SET used_xid = ?, used_qno = ? WHERE id=?'
                cursor.execute(update_query, (self.xid, self.qno, result['id']))
                self.conn.commit()

        except Exception as e:
            print(f"Error in query execution: {e}")
            return None
        finally:
            cursor.close()

        # Take accent and sex to add tts.engine and tts.voice
        result['tts'] = {}
        # if accent or sex is None, randomly choose one from the available options
        if not result.get('accent'):
            if self.part == 2:
                # special case for part 2: two people with different accents
                first_accent = random.choices(self.accent, weights=self.accent_weight, k=1)[0]
                remaining_accents = [a for a in self.accent if a != first_accent]
                second_accent = random.choices(remaining_accents, weights=[self.accent_weight[self.accent.index(a)] for a in remaining_accents], k=1)[0]
                result['accent'] = json.dumps([first_accent, second_accent])
            else:
                result['accent'] = random.choices(self.accent, weights=self.accent_weight, k=1)[0]
        if not result.get('sex'):
            if self.part == 2:
                # special case for part 2: two people with opposite sexes
                first_speaker = random.choices(self.sex, weights=self.sex_weight, k=1)[0]
                second_speaker = 'woman' if first_speaker == 'man' else 'man'
                result['sex'] = json.dumps([first_speaker, second_speaker])
            else:
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
    """
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
    """
    tts_mapping = {
        ('am', 'man'): [
            ('eleven', 'EozfaQ3ZX0esAp1cW5nG'),
            ('eleven', 'gfRt6Z3Z8aTbpLfexQ7N'),
            ('eleven', 'MP7UPhn7eVWqCGJGIh6Q'),
            ('eleven', 'DMyrgzQFny3JI1Y1paM5'),
            ('eleven', '6OzrBCQf8cjERkYgzSg8'),
            ('gcloud', 'en-US-Chirp3-HD-Achird'),
            ('gcloud', 'en-US-Chirp3-HD-Algenib'),
            ('gcloud', 'en-US-Chirp3-HD-Algieba'),
            ('gcloud', 'en-US-Chirp3-HD-Alnilam'),
            ('gcloud', 'en-US-Chirp3-HD-Charon'),
            ('gcloud', 'en-US-Chirp3-HD-Enceladus'),
            ('gcloud', 'en-US-Chirp3-HD-Fenrir'),
            ('gcloud', 'en-US-Chirp3-HD-Iapetus'),
            ('gcloud', 'en-US-Chirp3-HD-Orus'),
            ('gcloud', 'en-US-Chirp3-HD-Puck'),
            ('gcloud', 'en-US-Chirp3-HD-Rasalgethi'),
            ('gcloud', 'en-US-Chirp3-HD-Sadachbia'),
            ('gcloud', 'en-US-Chirp3-HD-Sadaltager'),
            ('gcloud', 'en-US-Chirp3-HD-Schedar'),
            ('gcloud', 'en-US-Chirp3-HD-Umbriel'),
            ('gcloud', 'en-US-Chirp3-HD-Zubenelgenubi')
        ],
        ('am', 'woman'): [
            ('eleven', 'zGjIP4SZlMnY9m93k97r'),
            ('eleven', 'kPzsL2i3teMYv0FxEYQ6'),
            ('eleven', 'kdmDKE6EkgrWrrykO9Qt'),
            ('eleven', 'dMyQqiVXTU80dDl2eNK8'),
            ('eleven', 'WtA85syCrJwasGeHGH2p'),
            ('gcloud', 'en-US-Chirp3-HD-Achernar'),
            ('gcloud', 'en-US-Chirp3-HD-Aoede'),
            ('gcloud', 'en-US-Chirp3-HD-Autonoe'),
            ('gcloud', 'en-US-Chirp3-HD-Callirrhoe'),
            ('gcloud', 'en-US-Chirp3-HD-Despina'),
            ('gcloud', 'en-US-Chirp3-HD-Erinome'),
            ('gcloud', 'en-US-Chirp3-HD-Gacrux'),
            ('gcloud', 'en-US-Chirp3-HD-Kore'),
            ('gcloud', 'en-US-Chirp3-HD-Laomedeia'),
            ('gcloud', 'en-US-Chirp3-HD-Leda'),
            ('gcloud', 'en-US-Chirp3-HD-Pulcherrima'),
            ('gcloud', 'en-US-Chirp3-HD-Sulafat'),
            ('gcloud', 'en-US-Chirp3-HD-Vindemiatrix'),
            ('gcloud', 'en-US-Chirp3-HD-Zephyr')
        ],
        ('cn', 'man'): [
            ('eleven', 'w4Z9gYJrajAuQmheNbVn'),
            ('eleven', '9XfYMbJVZqPHaQtYnTAO'),
        ],
        ('cn', 'woman'): [
            ('eleven', '1EZBFEhLjqjzuG8HBNbj'),
            ('eleven', 'TgnhEILA8UwUqIMi20rp'),
        ],
        ('br', 'man'): [
            ('eleven', 'L0Dsvb3SLTyegXwtm47J'),
            ('eleven', '2UMI2FME0FFUFMlUoRER'),
            ('eleven', 'mZ8K1MPRiT5wDQaasg3i'),
            ('eleven', 'lnIpQcZuikKim3oNdYlP'),
            ('gcloud', 'en-GB-Chirp3-HD-Achird'),
            ('gcloud', 'en-GB-Chirp3-HD-Algenib'),
            ('gcloud', 'en-GB-Chirp3-HD-Algieba'),
            ('gcloud', 'en-GB-Chirp3-HD-Alnilam'),
            ('gcloud', 'en-GB-Chirp3-HD-Charon'),
            ('gcloud', 'en-GB-Chirp3-HD-Enceladus'),
            ('gcloud', 'en-GB-Chirp3-HD-Fenrir'),
            ('gcloud', 'en-GB-Chirp3-HD-Iapetus'),
            ('gcloud', 'en-GB-Chirp3-HD-Orus'),
            ('gcloud', 'en-GB-Chirp3-HD-Puck'),
            ('gcloud', 'en-GB-Chirp3-HD-Rasalgethi'),
            ('gcloud', 'en-GB-Chirp3-HD-Sadachbia'),
            ('gcloud', 'en-GB-Chirp3-HD-Sadaltager'),
            ('gcloud', 'en-GB-Chirp3-HD-Schedar'),
            ('gcloud', 'en-GB-Chirp3-HD-Umbriel'),
            ('gcloud', 'en-GB-Chirp3-HD-Zubenelgenubi')
        ],
        ('br', 'woman'): [
            ('eleven', 'NFFZBoF6tNodi008z7VH'),
            ('eleven', 'MzqUf1HbJ8UmQ0wUsx2p'),
            ('eleven', 'lcMyyd2HUfFzxdCaC4Ta'),
            ('eleven', 'sIak7pFapfSLCfctxdOu'),
            ('gcloud', 'en-GB-Chirp3-HD-Achernar'),
            ('gcloud', 'en-GB-Chirp3-HD-Aoede'),
            ('gcloud', 'en-GB-Chirp3-HD-Autonoe'),
            ('gcloud', 'en-GB-Chirp3-HD-Callirrhoe'),
            ('gcloud', 'en-GB-Chirp3-HD-Despina'),
            ('gcloud', 'en-GB-Chirp3-HD-Erinome'),
            ('gcloud', 'en-GB-Chirp3-HD-Gacrux'),
            ('gcloud', 'en-GB-Chirp3-HD-Kore'),
            ('gcloud', 'en-GB-Chirp3-HD-Laomedeia'),
            ('gcloud', 'en-GB-Chirp3-HD-Leda'),
            ('gcloud', 'en-GB-Chirp3-HD-Pulcherrima'),
            ('gcloud', 'en-GB-Chirp3-HD-Sulafat'),
            ('gcloud', 'en-GB-Chirp3-HD-Vindemiatrix'),
            ('gcloud', 'en-GB-Chirp3-HD-Zephyr')
        ],
        ('au', 'man'): [
            ('eleven', 'DYkrAHD8iwork3YSUBbs'),
            ('eleven', '9Ft9sm9dzvprPILZmLJl'),
            ('eleven', 'Ori1rnHIeeysIxrsFZ2X'),
            ('gcloud', 'en-AU-Chirp3-HD-Achird'),
            ('gcloud', 'en-AU-Chirp3-HD-Algenib'),
            ('gcloud', 'en-AU-Chirp3-HD-Algieba'),
            ('gcloud', 'en-AU-Chirp3-HD-Alnilam'),
            ('gcloud', 'en-AU-Chirp3-HD-Charon'),
            ('gcloud', 'en-AU-Chirp3-HD-Enceladus'),
            ('gcloud', 'en-AU-Chirp3-HD-Fenrir'),
            ('gcloud', 'en-AU-Chirp3-HD-Iapetus'),
            ('gcloud', 'en-AU-Chirp3-HD-Orus'),
            ('gcloud', 'en-AU-Chirp3-HD-Puck'),
            ('gcloud', 'en-AU-Chirp3-HD-Rasalgethi'),
            ('gcloud', 'en-AU-Chirp3-HD-Sadachbia'),
            ('gcloud', 'en-AU-Chirp3-HD-Sadaltager'),
            ('gcloud', 'en-AU-Chirp3-HD-Schedar'),
            ('gcloud', 'en-AU-Chirp3-HD-Umbriel'),
            ('gcloud', 'en-AU-Chirp3-HD-Zubenelgenubi')
        ],
        ('au', 'woman'): [
            ('eleven', 'aEO01A4wXwd1O8GPgGlF'),
            ('eleven', 'LtPsVjX1k0Kl4StEMZPK'),
            ('eleven', '56bWURjYFHyYyVf490Dp'),
            ('gcloud', 'en-AU-Chirp3-HD-Achernar'),
            ('gcloud', 'en-AU-Chirp3-HD-Aoede'),
            ('gcloud', 'en-AU-Chirp3-HD-Autonoe'),
            ('gcloud', 'en-AU-Chirp3-HD-Callirrhoe'),
            ('gcloud', 'en-AU-Chirp3-HD-Despina'),
            ('gcloud', 'en-AU-Chirp3-HD-Erinome'),
            ('gcloud', 'en-AU-Chirp3-HD-Gacrux'),
            ('gcloud', 'en-AU-Chirp3-HD-Kore'),
            ('gcloud', 'en-AU-Chirp3-HD-Laomedeia'),
            ('gcloud', 'en-AU-Chirp3-HD-Leda'),
            ('gcloud', 'en-AU-Chirp3-HD-Pulcherrima'),
            ('gcloud', 'en-AU-Chirp3-HD-Sulafat'),
            ('gcloud', 'en-AU-Chirp3-HD-Vindemiatrix'),
            ('gcloud', 'en-AU-Chirp3-HD-Zephyr')
        ],
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

class setCoverImg:
    def __init__(self, xid, **args):
        self.xid = xid

    def run(self):
        return self.xid

class passThrough:
    def __init__(self, value, **args):
        try:
            self.value = json.loads(value)
        except json.JSONDecodeError:
            self.value = str(value)

    def run(self):
        return self.value