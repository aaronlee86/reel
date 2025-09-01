import utils.ai as ai

def user_choice_from_function(list1, list2):
    if len(list1) != len(list2):
        raise ValueError("The two lists must have the same size")

    if not list1:
        print("No items available to choose from.")
        return None

    # Display both lists with custom column names
    for i, (item1, item2) in enumerate(zip(list1, list2)):
        print(f"{i:<3} {str(item1):<20} {item2}")
    print(f"{len(list1):<3} get more...")

    while True:
        try:
            choice = int(input("Enter your choice: "))
            if 0 <= choice < len(list1):
                return choice  # Only return the first list's item
            else:
                return -1
        except ValueError:
            print("Please enter a valid number")

def condition(row):
    return row[2] and row[3] and any(not item for item in row[4:11])

def add_sentence(row):
    cols_set = [(5,6), (7,8), (9,10)]

    chinese = row[4].strip()
    english = row[3].strip()

    list1=[]
    list2=[]
    print(f"get sentences for {english}")

    for col_en, col_ch in cols_set:
        if row[col_en] and row[col_ch]:
            continue

        ans = -2
        while ans < 0:
            if len(list1) == 0 or ans == -1:
                x,y = ai.get_sentences(english, chinese)
                list1.extend(x)
                list2.extend(y)
            ans = user_choice_from_function(list1, list2)

        row[col_en] = list1.pop(ans)
        row[col_ch] = list2.pop(ans)

    return row

def add_explain(row):
    if row[4]:
        return row

    list1=[]
    list2=[]
    ans = -1

    chinese = row[4].strip()
    english = row[3].strip()

    print(f"get explain for {english}")

    while ans < 0:
        x,y = ai.get_explain(english, chinese)
        list1.extend(x)
        list2.extend(y)
        ans = user_choice_from_function(list1, list2)

    row[4] = list1[ans]
    return row

# List of transformation functions to apply in order
transform_functions = [
    add_explain,
    add_sentence
]