"""
Example generator classes for the CSV Template Processor.
These demonstrate simple string returns and complex JSON returns.
"""
from datetime import datetime
import sqlite3
import random

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

        try:
            # Take accent and sex to add tts.engine and tts.voice
            result['tts'] = {}
            # if accent or sex is None, randomly choose one from the available options
            if not result.get('accent'):
                result['accent'] = random.choices(self.accent, weights=self.accent_weight, k=1)[0]
            if not result.get('sex'):
                result['sex'] = random.choices(self.sex, weights=self.sex_weight, k=1)[0]
            print(f"result accent: {result['accent']}, sex: {result['sex']}")
            result['tts']['engine'], result['tts']['voice'] = getTtsSettings(result['accent'], result['sex'])
        except Exception as e:
            print(f"Error getting TTS settings from {result}: {e}")
            return None

        # update the question as used
        try:
            update_query = 'UPDATE questions SET used=1 WHERE id=?'
            cursor = self.conn.cursor()
            cursor.execute(update_query, (result['id'],))
            self.conn.commit()
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


def getTtsSettings(accent, sex):
    """
    Look up TTS settings by accent and sex.
    If multiple matches found, randomly choose one.
    If not found, raise an exception.
    
    Returns: (engine, voice) tuple
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
    
    # Sanity check
    if not accent or not sex:
        raise ValueError(f"Invalid accent or sex: accent={accent}, sex={sex}")
    
    # Normalize inputs
    accent = str(accent).lower().strip()
    sex = str(sex).lower().strip()
    
    # Look up in mapping
    key = (accent, sex)
    if key not in tts_mapping:
        raise KeyError(f"No TTS settings found for accent='{accent}', sex='{sex}'")
    
    # Get matching options
    options = tts_mapping[key]
    
    # Randomly choose if multiple matches
    engine, voice = random.choice(options)
    
    return engine, voice
