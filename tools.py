import json

def availability(input: str):
    data=json.loads(input)
    '''print(f"Normal: {input}")
    print(f"JSON: {data}")'''

    print(f"Searching for trains from {data['fromstation']} to {data['tostation']}...")
    return "Train 12617 (Mangala Exp) has 42 seats available in SL class."

print(availability('{"fromstation": "Aluva" ,"tostation": "Ferok" ,"train_name": "Mangala Exp", "seats": 42}'))

def trackstatus(trainnumber: int):
    print(f"Monitoring the Train #{trainnumber}....")
    return f"I have started the background agent to watch Train {trainnumber}. I will notify you the moment a seat opens up."
print(trackstatus(11256))