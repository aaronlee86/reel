import re

def time_to_words(time_str):
    """
    Convert time string to TTS-friendly words.
    Supports formats: "HH:MM", "H:MM", "HH:MM AM/PM", "H:MM AM/PM"
    """

    # Number word mappings
    ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
            'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
            'seventeen', 'eighteen', 'nineteen']
    tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty']

    def minutes_to_words(minutes):
        """Convert minutes (0-59) to words."""
        if minutes == 0:
            return "o'clock"
        elif 1 <= minutes <= 9:
            return f"oh {ones[minutes]}"
        elif 10 <= minutes <= 19:
            return ones[minutes]
        else:
            ten = minutes // 10
            one = minutes % 10
            if one == 0:
                return tens[ten]
            else:
                return f"{tens[ten]}-{ones[one]}"

    def hour_to_words(hour):
        """Convert hour (1-12) to words."""
        return ones[hour]

    # Parse the time string
    time_str = time_str.strip()

    # Check for AM/PM suffix
    am_pm = None
    if time_str.upper().endswith('AM'):
        am_pm = 'AM'
        time_str = time_str[:-2].strip()
    elif time_str.upper().endswith('PM'):
        am_pm = 'PM'
        time_str = time_str[:-2].strip()

    # Split into hours and minutes
    match = re.match(r'(\d{1,2}):(\d{2})', time_str)
    if not match:
        return time_str  # Return original if can't parse

    hour = int(match.group(1))
    minutes = int(match.group(2))

    # Handle 24-hour format (no AM/PM specified)
    if am_pm is None:
        if hour == 0:
            hour = 12
            am_pm = 'AM'
        elif hour < 12:
            # No AM/PM suffix for times without it (like your 1:00 examples)
            am_pm = ''
        elif hour == 12:
            am_pm = 'PM'
        else:
            hour = hour - 12
            am_pm = 'PM'
    else:
        # 12-hour format with AM/PM
        if hour == 0:
            hour = 12
        elif hour > 12:
            hour = hour - 12

    # Build the result
    hour_word = hour_to_words(hour)
    minutes_word = minutes_to_words(minutes)

    if minutes == 0:
        if am_pm:
            return f"{hour_word} {am_pm}"
        else:
            return f"{hour_word} {minutes_word}"
    else:
        if am_pm:
            return f"{hour_word} {minutes_word} {am_pm}"
        else:
            return f"{hour_word} {minutes_word}"


def convert_times_in_text(text):
    """
    Find and replace all time patterns in a text string.
    """
    # Pattern for times with AM/PM
    pattern_with_ampm = r'\b(\d{1,2}:\d{2})\s*(AM|PM|am|pm)\b'
    # Pattern for times without AM/PM (24-hour or ambiguous)
    pattern_without_ampm = r'\b(\d{1,2}:\d{2})\b'

    # First replace times with AM/PM
    def replace_with_ampm(match):
        return time_to_words(match.group(0))

    text = re.sub(pattern_with_ampm, replace_with_ampm, text)

    # Then replace remaining times (without AM/PM)
    def replace_without_ampm(match):
        return time_to_words(match.group(0))

    text = re.sub(pattern_without_ampm, replace_without_ampm, text)

    return text


# Test examples
if __name__ == "__main__":
    test_times = [
        "1:00", "1:01", "1:09", "1:10", "1:15", "1:21", "1:30", "1:45", "1:59",
        "5:00 AM", "5:05 AM", "5:15 AM", "5:30 AM", "5:45 AM",
        "13:00", "13:01", "13:15", "13:30", "14:23",
        "9:32", "12:00", "0:00"
    ]

    print("Time conversions:")
    for t in test_times:
        print(f"  {t:12} -> {time_to_words(t)}")

    print("\nText conversion example:")
    sample = "The meeting is at 13:00 and ends at 14:30. Breakfast at 7:00 AM."
    print(f"  Original: {sample}")
    print(f"  Converted: {convert_times_in_text(sample)}")